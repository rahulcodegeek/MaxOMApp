from datetime import datetime, time
import pytz
from database import db
from flask import Flask, request, session, render_template
from flask_session import Session
from flask_cors import CORS
from twilio.twiml.voice_response import VoiceResponse
import threading
from db_persisters.restaurants import add_restaurant, get_restaurants
from db_persisters.restaurant_system_configuration import add_restaurant_configuration
from db_persisters.payment_callback import add_payment_callback
from session_manager import create_session, set_session_attribute, \
    get_session_attribute, delete_session_attribute
from prompt_service import create_prompt_data
from menu_service import fetch_remote_menu, persist_menu, load_menu
from chat_gpt_service import conversation
from order_without_payment import persist_and_send_order_to_pos, send_order_to_pos
from fillers_information import get_randomly_filler_sentence, get_randomly_question_filler_sentence
import os
import json

application = Flask(__name__)
# You can choose a different session type if needed
application.config['SESSION_TYPE'] = 'filesystem'
# Session data is not permanent
application.config['SESSION_PERMANENT'] = False
Session(application)
# --- Enable CORS for all routes in the app
CORS(application)

# --- Enable database
#TODO - change or revisit the following two variables database_url and is_test_mode accordingly for every deployment
#database_url = "mysql+pymysql://admin:voicebot@restuarantdatabase.cwr0mrljgsss.eu-west-1.rds.amazonaws.com:3306/restaurantvoicebot"
#PROD
database_url = "mysql+pymysql://admin:maxom123@awseb-e-4m68bme65w-stack-awsebrdsdatabase-uvdqhoxx5vij.cs0btkh5jqy1.us-west-2.rds.amazonaws.com:3306/restaurantvoicebot"

#TEST
#database_url = "mysql+pymysql://admin:maxom123@awseb-e-j7pyp2zkv6-stack-awsebrdsdatabase-dgmfmkp5fakq.cs0btkh5jqy1.us-west-2.rds.amazonaws.com:3306/restaurantvoicebot"

is_test_mode = False

# database_url = 'mysql://root:''@localhost:3308/restaurant'
application.config["SQLALCHEMY_DATABASE_URI"] = database_url
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(application)


# ------------ Routes ------------
# --- Home Route
@application.route('/')
def hello_maxom():
    return 'Hello from MaxOM On 2/18/24 01'


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
        #TODO - change this error as this is now an offline operation and not on the call operation
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




# --- Route to have the conversation with the bot using the twilio
@application.route("/voice", methods=['POST'])
def voice():
    status_code = 200
    restaurant_phone_number = request.form['To']
    calling_phone_number = request.form.get('From')
    reply = ''
    prompt_data = ''
    response = VoiceResponse()
    restaurant_opening_time = time(16, 0)
    restaurant_closing_time = time(23, 30)
    print("Restaurant timings are between ", restaurant_opening_time, restaurant_closing_time)
    if is_restaurant_open(restaurant_opening_time, restaurant_closing_time, 'America/Denver'):
        # ---> Initiate the session if not already initialized
        if 'session_id' not in session:
            print('session_id is not in session, so setting it first time')
            create_session()
            set_session_attribute('first_message', True)
            set_session_attribute('to_number', str(restaurant_phone_number))
            set_session_attribute('from_number', str(calling_phone_number))
            set_session_attribute('order', 'Not-Confirm')
            # ---> Initiating the prompt for the restaurant phone number
            prompt_data, status_code = create_prompt_data(restaurant_phone_number)
            # ---> In case there is an error so say that otherwise will overwrite in the next if condition
            print('status_code returned from create_prompt_data is', status_code)
            print('create_prompt_data completed for session_id', get_session_attribute('session_id'))
            print('create_prompt_data completed for from_number', get_session_attribute('from_number'))

            reply = prompt_data
            history = [{"role": "assistant", "content": prompt_data}]
            set_session_attribute('user_mes', history)
        if get_session_attribute('order') == "Confirm":
            print('Confirming the order from voice block for from_number, session_id', get_session_attribute('from_number'), get_session_attribute('session_id'))
            response.redirect('/place_order')
        else:
            gather = response.gather(
                action="/filler", method="POST",
                input="speech dtmf", numDigits="1",
                speechTimeout="auto", timeout=7,
                language='en-IN', enhanced="true",
                speechModel="phone_call",
                hints = "yes, no, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, one, two, three, four, five, six, seven, eight, nine, ten, mild, medium, hot, mango lassi, cheese naan, butter naan, naan, appetizers, vegetarian, food, Paneer Tikka Masala, Masala Chai Tea, Chicken Tikka Masala, Goat Sukka"
            )
            if get_session_attribute('first_message') and status_code == 200:
                # ---> First Hard code Query
                first_user_query = "Hi"
                # ---> Getting reply from
                user_query = first_user_query + ' (refer to context)'
                print('user_query for chat is ', user_query)
                print('user_query is for session_id', get_session_attribute('session_id'))
                # --> Getting previous conversation
                history = get_session_attribute('user_mes')
                history.append({"role": "user", "content": user_query})
                set_session_attribute('user_mes', history)
                conversation(history, get_session_attribute('session_id'))
                with open("./resources/"+get_session_attribute('session_id')+".json", 'r') as file:
                    data = json.load(file)
                # Extract reply and status code from the data dictionary
                reply = data["reply"]
                status_code = data["status_code"]
                os.remove("./resources/"+get_session_attribute('session_id')+".json")
                print('reply from chat is ', reply)
                print('reply is for session_id', get_session_attribute('session_id'))
                # --> Storing updated conversation
                history = get_session_attribute('user_mes')
                history.append({"role": "assistant", "content": reply})
                set_session_attribute('user_mes', history)
                set_session_attribute('first_message', False)
            elif not get_session_attribute('first_message'):
                # ---> Get the speech recognition result
                if get_session_attribute('speech') != "":
                    user_query = get_session_attribute('speech')
                    # reply, status_code = conversation(user_query)
                    file_path = "./resources/"+get_session_attribute('session_id')+".json"
                    while not os.path.exists(file_path):
                        continue
                    while True:
                        try:
                            with open(file_path, 'r') as file:
                                data = json.load(file)
                            break  # Break out of the loop if loading is successful
                        except json.decoder.JSONDecodeError:
                            continue
                    # Extract reply and status code from the data dictionary
                    reply = data["reply"]
                    status_code = data["status_code"]
                    os.remove(file_path)
                    print('reply from chat is ', reply)
                    print('reply is for session_id', get_session_attribute('session_id'))
                    # --> Storing updated conversation
                    history = get_session_attribute('user_mes')
                    history.append({"role": "assistant", "content": reply})
                    set_session_attribute('user_mes', history)
                    set_session_attribute("speech","")
                    # If <PLACE_ORDER_AND_END_CALL> is set then, it means the order is to be placed and conversation has to be ended.
                    if '<PLACE_ORDER_AND_END_CALL>' in reply:
                        history = get_session_attribute('user_mes')
                        set_session_attribute('history', history)
                        reply = reply.replace('<PLACE_ORDER_AND_END_CALL>', '')
                        set_session_attribute('order', "Confirm")
                        print('Confirming the order from <PLACE_ORDER_AND_END_CALL> in the response for from_number, session_id',
                              get_session_attribute('from_number'), get_session_attribute('session_id'))
                        response.redirect('/place_order')
            if status_code != 200:
                gather.say("I am connecting you to the actual agent.")
                gather.say("Kindly wait while i am connecting you.")
                agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
                response.dial(agent_number)
            else:
                # ---> Normal conversation reply
                gather.say(reply)
            # ---> If there is no error continue call if user doesn't say anything for next 7 seconds
            if status_code == 200 and get_session_attribute('order') != "Confirm":
                response.say("Are you still there?")
                gather = response.gather(
                    action="/filler", method="POST",
                    input="speech dtmf", numDigits="1",
                    speechTimeout="auto",
                    language='en-IN', enhanced="true",
                    speechModel="phone_call",
                    hints = "yes, no, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, one, two, three, four, five, six, seven, eight, nine, ten, mild, medium, hot, mango lassi, cheese naan, butter naan, naan, appetizers, vegetarian, food, Paneer Tikka Masala, Masala Chai Tea, Chicken Tikka Masala, Goat Sukka"
                )
    else:
        agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
        print("Restaurant is closed right now so, redirecting the call to ", agent_number)
        response.dial(agent_number)
    return str(response)


@application.route("/filler", methods=['POST'])
def filler():
    response = VoiceResponse()
    speech_result = request.form['SpeechResult']
    if get_session_attribute('order') == "Confirm":
        print('Confirming the order from filler block for from_number, session_id', get_session_attribute('from_number'), get_session_attribute('session_id'))
        response.redirect('/place_order')
    if speech_result:
        if "agent" in speech_result.lower() or "customer service" in speech_result.lower():
            response.say("I am connecting you to the actual agent.")
            response.say("Kindly wait for a moment...")
            restaurant_phone_number = request.form['To']
            agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
            response.dial(agent_number)
        else:
            user_query = speech_result
            if user_query is None or user_query.strip() == '':
                print('Error from conversation so, redirecting to actual agent...')
                reply = 'Sorry for inconvenience five. I am connecting you to the actual agent wait for some moments.'
                status = 500
                with open("./resources/"+get_session_attribute('session_id')+".txt", 'w') as file:
                    file_data = reply+" status_code "+str(status)
                    file.write(file_data)
            else:
                # ---> Getting reply from
                user_query = user_query + ' (refer to context)'
                print('user_query for chat is ', user_query)
                print('user_query is for session_id', get_session_attribute('session_id'))
                # --> Getting previous conversation
                history = get_session_attribute('user_mes')
                history.append({"role": "user", "content": user_query})
                set_session_attribute('user_mes', history)

                def local_conversation(local_history, local_session_id):
                    with application.test_request_context():
                        conversation(local_history, local_session_id)

                # ---> Sending payment message to customer
                thread = threading.Thread(
                    target=local_conversation,
                    args=(
                        history, get_session_attribute('session_id')
                    )
                )
                thread.start()
            if "?" in user_query:
                response.say(get_randomly_question_filler_sentence())
            else:
                response.say(get_randomly_filler_sentence())
            set_session_attribute("speech", user_query)
            response.redirect('/voice')
    return str(response)


@application.route("/voice_error_handler", methods=['POST'])
def voice_error_handler():
    print("End session called from voice_error_handler for session ", get_session_attribute('session_id'))
    end_session()
    response = VoiceResponse()
    response.say(
        "We apologize an application issue has occurred at our side. I am redirecting your call to a real agent. Thank you for your business.")
    restaurant_phone_number = request.form['To']
    agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
    response.dial(agent_number)
    return str(response)




# --- Route to place the order
@application.route("/place_order", methods=['POST'])
def place_order():
    # ---> Once order is successfully placed bot says below statement
    response = VoiceResponse()
    response.hangup()
    # ---> Getting order in json format using order_query of order module
    history = get_session_attribute('user_mes')
    from_ = get_session_attribute('from_number')
    to_ = get_session_attribute('to_number')

    def local_persist_and_send_order_to_pos(local_history, local_from, local_to, local_is_test_mode):
        with application.test_request_context():
            persist_and_send_order_to_pos(local_history, local_from, local_to, local_is_test_mode)

    # ---> Sending payment message to customer
    thread = threading.Thread(
        target=local_persist_and_send_order_to_pos,
        args=(
            history, from_, to_, is_test_mode
        )
    )
    thread.start()
    print("End session called from place_order for session ", get_session_attribute('session_id'))
    end_session()

    print('Finally session ended')
    return str(response)


# --- Function to delete the session
def end_session():
    print("End session called for ", get_session_attribute('session_id'))
    delete_session_attribute('session_id')
    delete_session_attribute('first_message')
    delete_session_attribute('to_number')
    delete_session_attribute('from_number')
    delete_session_attribute('user_mes')
    delete_session_attribute('history')
    delete_session_attribute('order')
    return None

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


if __name__ == '__main__':
    application.run(debug=True)
