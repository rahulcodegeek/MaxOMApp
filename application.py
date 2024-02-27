from datetime import datetime, time
import pytz
from database import db
from flask import Flask, request, session, render_template, send_file
from flask_session import Session
from flask_cors import CORS
from twilio.twiml.voice_response import VoiceResponse
import threading
from db_persisters.restaurants import add_restaurant, get_restaurants
from db_persisters.restaurant_system_configuration import add_restaurant_configuration
from db_persisters.payment_callback import add_payment_callback
from prompt_service import create_prompt_data
from menu_service import fetch_remote_menu, persist_menu, load_menu
from chat_gpt_service import conversation
from order_without_payment import persist_and_send_order_to_pos, send_order_to_pos
from fillers_information import get_randomly_filler_sentence, get_randomly_question_filler_sentence
import os
import json
import sys
from file_logger import FileLogger
import zipfile
import redis
import uuid

# Redirect stdout and stderr to the file object
sys.stdout = FileLogger("./logs/output_log.txt")
sys.stderr = FileLogger("./logs/error_log.txt")


application = Flask(__name__)
# You can choose a different session type if needed
# Session data is not permanent
application.secret_key = os.getenv('SECRET_KEY', default='BAD_SECRET_KEY')

# Configure Redis for storing the session data on the server-side
application.config['SESSION_TYPE'] = 'redis'
application.config['SESSION_PERMANENT'] = False
application.config['SESSION_USE_SIGNER'] = True
application.config['SESSION_REDIS'] = redis.Redis.from_url(os.environ.get('REDIS_URL'))

Session(application)
# --- Enable CORS for all routes in the app
CORS(application)

store = redis.Redis.from_url(os.environ.get('REDIS_URL'))
# --- Enable database
# TODO - change or revisit the following two variables database_url and is_test_mode accordingly for every deployment
# database_url = "mysql+pymysql://admin:voicebot@restuarantdatabase.cwr0mrljgsss.eu-west-1.rds.amazonaws.com:3306/restaurantvoicebot"
# PROD
# database_url = "mysql+pymysql://admin:maxom123@awseb-e-4m68bme65w-stack-awsebrdsdatabase-uvdqhoxx5vij.cs0btkh5jqy1.us-west-2.rds.amazonaws.com:3306/restaurantvoicebot"

#TEST
database_url = "mysql+pymysql://admin:maxom123@awseb-e-j7pyp2zkv6-stack-awsebrdsdatabase-dgmfmkp5fakq.cs0btkh5jqy1.us-west-2.rds.amazonaws.com:3306/restaurantvoicebot"
# database_url = "mysql://admin:password@127.0.0.1:3306/restaurantvoicebot"

is_test_mode = True

# database_url = 'mysql://root:''@localhost:3308/restaurant'
application.config["SQLALCHEMY_DATABASE_URI"] = database_url
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(application)


# ------------ Routes ------------
# --- Home Route
@application.route('/')
def get_health():
    data = {
        'type': 'ac-bot-api',
        'success': True
    }
    data = json.dumps(data)
    return str(data)

@application.route("/", methods=['POST'])
def voice():
    status_code = 200
    print('request in / POST method is ', request.get_data())
    data = json.loads(request.get_data())

    conversation_id = data['conversation']

    data = {
        'activitiesURL': 'conversation/' + conversation_id + '/activities',
        'refreshURL': 'conversation/' + conversation_id + '/refresh',
        'disconnectURL': 'conversation/' + conversation_id + '/disconnect',
        'expiresSeconds': 60
    }
    data = json.dumps(data)
    return str(data)


# --- Route to create the database tables which is defined in database file
@application.route('/create_db_tables')
def create_db_tables():
    db.create_all()
    return 'Database Tables Created'

@application.route('/menu/<restaurant_id>')
def get_loaded_menu(restaurant_id):
    menu_content, status_code = load_menu(restaurant_id)
    return menu_content


# --- Route to delete the database all tables
# @application.route('/delete_db_tables')
# def delete_db_tables():
#    db.drop_all()
#    return 'Database Tables Deleted'

@application.route('/add_restaurant', methods=['POST'])
def add_restaurant_database():
    data = request.json
    restaurant_name = data['restaurant_name']
    restaurant_number = data['restaurant_number']
    redirecting_number = data['redirecting_number']
    restaurant_information = data['restaurant_information']
    pos_type = data['pos_type']
    pos_url = data['pos_url']
    pos_authorization_header = data['pos_authorization_header']
    voice_api_type = data['voice_api_type']
    voice_api_account_sid = data['voice_api_account_sid']
    voice_api_account_auth_token = data['voice_api_account_auth_token']
    payment_api_key = data['payment_api_key']
    payment_secret = data['payment_secret']
    print('Adding restaurant to configuration...')
    phone_number = add_restaurant(
        restaurant_name, restaurant_number,
        redirecting_number, restaurant_information
    )
    res = get_restaurants(phone_number)
    add_restaurant_configuration(
        res.id, pos_type, pos_url, pos_authorization_header,
        voice_api_type, voice_api_account_sid, voice_api_account_auth_token,
        payment_api_key, payment_secret
    )
    initialize_application_menu(phone_number)
    print('Restaurant configuration Added')
    return 'Restaurant Added'


# --- Route to have a successful stripe payment
# @application.route('/payment_successful')
# def payment_successful():
#     # ---> Getting order id and restaurant id to pass in the Send
#     # ---> Order to clover function of order module
#     order_id = request.args.get('order_id')
#     res_id = request.args.get('res_id')
#     payment_id = request.args.get('bill_id')
#     try:
#         send_order_to_clover(order_id, res_id)
#         add_payment_callback(order_id, payment_id, "Payment Successful")
#     except Exception as e:
#         add_payment_callback(order_id, payment_id, "Payment Successful but "+str(e))
#     return render_template('success.html')


# --- Route to have a failed stripe payment
# @application.route('/payment_failed')
# def payment_failed():
#     order_id = request.args.get('order_id')
#     payment_id = request.args.get('bill_id')
#     add_payment_callback(
#         order_id, payment_id, "Payment Unsuccessful"
#     )
#     return render_template('fail.html')


# --- Route for initializing phone number to restaurant mapper
@application.route("/initialize/<restaurant_phone_number>/menu", methods=['POST'])
def initialize_application_menu(restaurant_phone_number):
    print("Initialization for Menu Started...")
    restaurant = get_restaurants(restaurant_phone_number)
    print('restaurant fetched in initialize_application_menu ', restaurant)
    try:
        fetched_menu, status_code = fetch_remote_menu(restaurant.id, "items")
        if status_code == 200:
            print('status_code from fetch_remote_menu', status_code)
            persist_menu(restaurant.id, fetched_menu.text)
            print("Initialization for Menu Completed...")
            return ('Initialization for Menu Completed'), status_code
        return fetched_menu, status_code
    except Exception as e:
        print('Error landing...', e)
        print(e)
        # TODO - change this error as this is now an offline operation and not on the call operation
        return "Sorry for inconvenience three. I am connecting you to the \
actual agent wait for some moments.", 501


# --- Function for creating the prompt for the restaurant phone number

# def initialize_application_prompt(restaurant_phone_number):
#     print("Prompt initialization started...")
#     reply, status_code = initialize_application_menu(restaurant_phone_number)
#     if status_code != 200:
#         return reply, status_code
#     try:
#         prompt_data, status_code = create_prompt_data(restaurant_phone_number)
#         print("Prompt initialized...")
#         return prompt_data, status_code
#     except Exception as e:
#         print(str(e))
#         return "Sorry for inconvenience four. I am connecting you to the actual agent wait for some moments", 500


@application.route("/conversation/<conversation_id>/refresh", methods=['POST'])
def refresh(conversation_id):
    data = json.loads(request.get_data())
    print('request in refresh POST method is ', data)

    refresh_response = {
        "expiresSeconds": 60
    }
    refresh_response = json.dumps(refresh_response)
    return str(refresh_response)

@application.route("/conversation/<conversation_id>/disconnect", methods=['POST'])
def disconnect(conversation_id):
    data = json.loads(request.get_data())
    print('request in disconnect POST method is ', data)

    disconnect_response = {
    }
    disconnect_response = json.dumps(disconnect_response)
    return str(disconnect_response)


@application.route("/conversation/<conversation_id>/activities", methods=['POST'])
def activities(conversation_id):
    status_code = 200
    data = json.loads(request.get_data())
    print('request in activities POST method is ', data)
    print('session contains', session)

    conversation_id = data['conversation']

    reply = ''
    prompt_data = ''
    restaurant_opening_time = time(16, 0)
    restaurant_closing_time = time(5, 30)
    print("Restaurant timings are between ", restaurant_opening_time, restaurant_closing_time)
    if is_restaurant_open_temp(restaurant_opening_time, restaurant_closing_time, 'America/Denver'):
        # ---> Initiate the session if not already initialized
        conversation_dictionary = store.hgetall(conversation_id)
        print('Is ', conversation_id, ' present:', conversation_dictionary, len(conversation_dictionary))
        if len(conversation_dictionary) == 0:
            # TODO -- properly fetch these values from the start event
            restaurant_phone_number = data['activities'][0]['parameters']['callee']
            calling_phone_number = data['activities'][0]['parameters']['caller']
            print('restaurant_phone_number and calling_phone_number fetched from the start event payload as ',
                  restaurant_phone_number, calling_phone_number)

            store.hset(conversation_id, 'first_message', "True")
            store.hset(conversation_id, 'to_number', str(restaurant_phone_number))
            store.hset(conversation_id, 'from_number', str(calling_phone_number))
            store.hset(conversation_id, 'order', 'Not-Confirm')

            # ---> Initiating the prompt for the restaurant phone number
            prompt_data, status_code = create_prompt_data(restaurant_phone_number)

            print('Now session contains', session)
            # ---> In case there is an error so say that otherwise will overwrite in the next if condition
            print('status_code returned from create_prompt_data is', status_code)
            print('create_prompt_data completed for session_id', conversation_id)

            reply = prompt_data
            history = [{"role": "assistant", "content": prompt_data}]
            store.rpush(conversation_id+'-user_mes', json.dumps({"role": "assistant", "content": prompt_data}))

        if len(conversation_dictionary) != 0 and store.hgetall(conversation_id)['order'] == 'Confirm':
            print('Confirming the order from voice block for from_number, session_id',
                  conversation_dictionary['from_number'], conversation_id)
            return form_hangup_response()
        else:
            conversation_dictionary = store.hgetall(conversation_id)
            # gather = response.gather(
            #     action="/filler", method="POST",
            #     input="speech dtmf", numDigits="1",
            #     speechTimeout="auto", timeout=7,
            #     language='en-IN', enhanced="true",
            #     speechModel="phone_call",
            #     hints = "yes, no, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, one, two, three, four, five, six, seven, eight, nine, ten, mild, medium, hot, mango lassi, cheese naan, butter naan, naan, appetizers, vegetarian, food, Paneer Tikka Masala, Masala Chai Tea, Chicken Tikka Masala, Goat Sukka"
            # )
            if len(conversation_dictionary) != 0 and conversation_dictionary['first_message'] == "True" and status_code == 200:
                # ---> First Hard code Query
                print('first_message is True, so flowing through first_message block')
                first_user_query = "Hi"
                # ---> Getting reply from
                user_query = first_user_query + ' (refer to context)'
                print('user_query for chat is ', user_query)
                print('user_query is for session_id', conversation_id)
                # --> Getting previous conversation
                history = store.lrange(conversation_id+'-user_mes', 0, -1)

                # Deserialize the messages
                formatted_history = []
                for message_str in history:
                    message = json.loads(message_str)
                    formatted_history.append(message)

                formatted_history.append({"role": "user", "content": user_query})
                store.rpush(conversation_id+'-user_mes', json.dumps({"role": "user", "content": user_query}))
                reply, status_code = conversation(formatted_history, conversation_id)

                # with open("./resources/" + conversation_id + ".json", 'r') as file:
                #     data = json.load(file)
                # # Extract reply and status code from the data dictionary
                # reply = data["reply"]
                # status_code = data["status_code"]
                # os.remove("./resources/" + conversation_id + ".json")
                print('welcome_message from chat is ', reply)
                print('welcome_message is for session_id', conversation_id)
                # --> Storing updated conversation

                history.append({"role": "assistant", "content": reply})
                store.rpush(conversation_id+'-user_mes', json.dumps({"role": "assistant", "content": reply}))
                store.hset(conversation_id, 'first_message', "False")
            elif len(conversation_dictionary) != 0 and conversation_dictionary['first_message'] == "False":
                # ---> Get the speech recognition result
                history = store.lrange(conversation_id + '-user_mes', 0, -1)

                # Deserialize the messages
                formatted_history = []
                for message_str in history:
                    message = json.loads(message_str)
                    formatted_history.append(message)

                user_query = data['activities'][0]['text']
                print('user_query is normal conversation is ', user_query)

                formatted_history.append({"role": "user", "content": user_query})
                store.rpush(conversation_id + '-user_mes', json.dumps({"role": "user", "content": user_query}))

                reply, status_code = conversation(formatted_history, conversation_id)

                # with open("./resources/" + conversation_id + ".json", 'r') as file:
                #     data = json.load(file)
                # # Extract reply and status code from the data dictionary
                # reply = data["reply"]
                # status_code = data["status_code"]
                # os.remove("./resources/" + conversation_id + ".json")
                print('response in first_message False from chat is ', conversation_id, reply)
                # --> Storing updated conversation

                history.append({"role": "assistant", "content": reply})
                store.rpush(conversation_id + '-user_mes', json.dumps({"role": "assistant", "content": reply}))

                # If <PLACE_ORDER_AND_END_CALL> is set then, it means the order is to be placed and conversation has to be ended.
                if '<PLACE_ORDER_AND_END_CALL>' in reply:
                    #TODO
                    # history = store.lrange(conversation_id+'-user_mes', 0, -1)
                    # store.hset(conversation_id, 'history', history)
                    reply = reply.replace('<PLACE_ORDER_AND_END_CALL>', '')
                    store.hset(conversation_id, 'order', 'Confirm')
                    print('Confirming the order from <PLACE_ORDER_AND_END_CALL> in the response for', conversation_id)
                    status_code = place_order(conversation_id)
                    print('From <PLACE_ORDER_AND_END_CALL> block for conversation_id response is', conversation_id,
                          status_code, reply)
            if status_code != 200:
                redirect_response = form_redirection_response()
                return str(redirect_response)
                # agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
                # response.dial(agent_number)
            else:
                # ---> Normal conversation reply
                normal_response = form_response(reply)
                normal_response = json.dumps(normal_response)
                print('returning normal_response from the respective block ', normal_response)
                return str(normal_response)
            # ---> If there is no error continue call if user doesn't say anything for next 7 seconds
            # if status_code == 200 and get_session_attribute('order') != "Confirm":
            #     response.say("Are you still there?")
            #     gather = response.gather(
            #         action="/filler", method="POST",
            #         input="speech dtmf", numDigits="1",
            #         speechTimeout="auto",
            #         language='en-IN', enhanced="true",
            #         speechModel="phone_call",
            #         hints = "yes, no, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, one, two, three, four, five, six, seven, eight, nine, ten, mild, medium, hot, mango lassi, cheese naan, butter naan, naan, appetizers, vegetarian, food, Paneer Tikka Masala, Masala Chai Tea, Chicken Tikka Masala, Goat Sukka"
            #     )
    else:
        # TODO -- properly fetch these values from the start event
        restaurant_phone_number = data['activities'][0]['parameters']['callee']
        agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
        redirect_response = form_redirection_response()
        print("Restaurant is closed right now so, redirecting the call to ", agent_number)
        return str(redirect_response)

def form_hangup_response():
    hangup_response = {
        'activities': [
            {
                'id': str(uuid.uuid4()),
                'type': 'event',
                'name': 'hangup'
            }
        ]
    }
    return hangup_response

def form_response(reply):
    normal_response = {
        'activities': [
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'language': 'en-US',
                'type': 'message',
                'text': reply
            }
        ]
    }
    return normal_response


def form_redirection_response():
    redirect_response = {
        'activities': [
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'language': 'en-US',
                'type': 'message',
                'text': 'I am connecting you to the actual agent. Kindly wait while i am connecting you. Though I have to still implement redirection, please feel free to hangup..'
            }
        ]
    }
    redirect_response = json.dumps(redirect_response)
    print('returning', redirect_response)
    return redirect_response


# filler and voice_error_handler

# --- Route to place the order
@application.route("/place_order", methods=['POST'])
def place_order(conversation_id):
    conversation_dictionary = store.hgetall(conversation_id)
    # ---> Getting order in json format using order_query of order module
    history = store.lrange(conversation_id+'-user_mes', 0, -1)

    formatted_history = []
    for message_str in history:
        message = json.loads(message_str)
        formatted_history.append(message)

    from_ = conversation_dictionary['from_number']
    to_ = conversation_dictionary['to_number']

    def local_persist_and_send_order_to_pos(local_history, local_from, local_to, local_is_test_mode):
        with application.test_request_context():
            persist_and_send_order_to_pos(local_history, local_from, local_to, local_is_test_mode)

    # ---> Sending payment message to customer
    thread = threading.Thread(
        target=local_persist_and_send_order_to_pos,
        args=(
            formatted_history, from_, to_, is_test_mode
        )
    )

    thread.start()
    print("End session called from place_order for session ", conversation_id)

    #store.delete(conversation_id)

    print('returning with the hang_up_event_as_response from place_order as  ', 200)
    return 200


@application.route('/download_logs')
def download_logs():
    try:
        if os.path.exists('logs.zip'):
            os.remove('logs.zip')
        with zipfile.ZipFile('logs.zip', 'w') as zipf:
            zipf.write('logs/output_log.txt', os.path.basename('output_log.txt'))
            zipf.write('logs/error_log.txt', os.path.basename('error_log.txt'))

        # Send the ZIP file as an attachment
        return send_file('logs.zip', as_attachment=True)
    except Exception as e:
        return str(e)


def is_restaurant_open(restaurant_opening_time, restaurant_closing_time, timezone_str):
    # Define the timezone
    timezone = pytz.timezone(timezone_str)

    # Get current time in the specified timezone
    current_time = datetime.now(timezone).time()

    # Check if current time is within the range
    if restaurant_opening_time <= current_time <= restaurant_closing_time:
        return True
    else:
        return False

def is_restaurant_open_temp(restaurant_opening_time, restaurant_closing_time, timezone_str):
    return True


if __name__ == '__main__':
    application.run(debug=True)
