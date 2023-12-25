from chat_gpt_service import conversation
from database import db
from flask import Flask, request, session, render_template
from flask_session import Session
from flask_cors import CORS
from menu_service import fetch_remote_menu, persist_menu
from order import send_order_to_clover
from prompt_service import create_prompt_data
from session_manager import create_session, set_session_attribute, \
    get_session_attribute, delete_session_attribute
from stripe_payment import send_stripe_payment_message
from twilio.twiml.voice_response import VoiceResponse
import threading
from db_persisters.restaurants import add_restaurant, get_restaurants
from db_persisters.restaurant_system_configuration import add_restaurant_configuration
from db_persisters.payment_callback import add_payment_callback

application = Flask(__name__)
# You can choose a different session type if needed
application.config['SESSION_TYPE'] = 'filesystem'
# Session data is not permanent
application.config['SESSION_PERMANENT'] = False
Session(application)
# --- Enable CORS for all routes in the app
CORS(application)

# --- Enable database
#TODO - change this for every deployment
#database_url = "mysql+pymysql://admin:voicebot@restuarantdatabase.cwr0mrljgsss.eu-west-1.rds.amazonaws.com:3306/restaurantvoicebot"
database_url = "mysql+pymysql://admin:maxom123@awseb-e-4m68bme65w-stack-awsebrdsdatabase-uvdqhoxx5vij.cs0btkh5jqy1.us-west-2.rds.amazonaws.com:3306/restaurantvoicebot"

# database_url = 'mysql://root:''@localhost:3308/restaurant'
application.config["SQLALCHEMY_DATABASE_URI"] = database_url
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(application)


# ------------ Routes ------------
# --- Home Route
@application.route('/')
def hello_maxom():
    return 'Hello from MaxOM On 12/21/23'


# --- Route to create the database tables which is defined in database file
@application.route('/create_db_tables')
def create_db_tables():
    db.create_all()
    return 'Database Tables Created'


# --- Route to delete the database all tables
#@application.route('/delete_db_tables')
#def delete_db_tables():
#    db.drop_all()
#    return 'Database Tables Deleted'

#TODO - This will be dynamically configured for each restaurant
# --- Configure the restaurant
@application.route('/add_restaurant')
def add_restaurant_database():
    print('Adding restaurant to configuration...')
    info_json = {
        "timings": "Monday and Tuesday from 4PM to 12AM and Wednesday \
through Friday from 11AM to 1AM",
        "representative_name": "Amy",
        "address": "280 E 12300 S, Suite 110, Draper, UT",
        "today_special": "Goat Sukka"
    }
    phone_number = add_restaurant(
        "Paradise", "+18016181119", "+13109937203", info_json
    )
    res = get_restaurants(phone_number)
    add_restaurant_configuration(
        res.id, "Clover",
        "https://sandbox.dev.clover.com/v3/merchants/YYKSZ49GMSZD1/",
        "b955f83f-b70c-e717-abe7-95171f25b2e9",
        "Twillio", "AC8c81f929b9a4e03c76d853b383d63a1a",
        "3b9ac8c045793aff725ac0a54a5e3864",
        "sk_test_51NsJOgI6hLoGbkjMETqmm36XjI2SK1\
ajKFFEc94nHxosCQBT6VUSCcrXHbV7ApTsneUb1gGfC1Z6a5uzGX6cKEs900J5wwp41o",
        "Stripe_payment_secret_key")
    print('Restaurant configuration Added')
    return 'Restaurant Added'

# --- Route to have a successful stripe payment
@application.route('/payment_successful')
def payment_successful():
    # ---> Getting order id and restaurant id to pass in the Send
    # ---> Order to clover function of order module
    order_id = request.args.get('order_id')
    res_id = request.args.get('res_id')
    payment_id = request.args.get('bill_id')
    try:
        send_order_to_clover(order_id, res_id)
        add_payment_callback(order_id, payment_id, "Payment Successful")
    except Exception as e:
        add_payment_callback(order_id, payment_id, "Payment Successful but "+str(e))
    return render_template('success.html')


# --- Route to have a failed stripe payment
@application.route('/payment_failed')
def payment_failed():
    order_id = request.args.get('order_id')
    payment_id = request.args.get('bill_id')
    add_payment_callback(
        order_id, payment_id, "Payment Unsuccessful"
    )
    return render_template('fail.html')


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

        reply = prompt_data
        history = [{"role": "assistant", "content": prompt_data}]
        set_session_attribute('user_mes', history)
        print('session_id is not in session, so have set it for the first time')
    if get_session_attribute('order') == "Confirm":
        print('Confirming the order...')
        response.redirect('/place_order')
    else:
        gather = response.gather(
            action="/voice", method="POST",
            input="speech dtmf", numDigits="1",
            speechTimeout="auto", timeout=7,
            language='en-IN', enhanced="true",
            speechModel="phone_call",
            hints = "yes, no, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, one, two, three, four, five, six, seven, eight, nine, ten, mild, medium, hot, mango lassi, cheese naan, butter naan, naan, appetizers, vegetarian, food, Paneer Tikka Masala, Masala Chai Tea"
        )
        if get_session_attribute('first_message') and status_code == 200:
            # ---> First Hard code Query
            first_user_query = "Hi"
            # ---> Getting reply from CHATGPT
            welcome_message, status_code = conversation(first_user_query)

            reply = welcome_message
            print('reply -- ', reply)
            set_session_attribute('first_message', False)
        elif not get_session_attribute('first_message'):
            # ---> Get the speech recognition result
            if "Digits" in request.values:
                choice = request.values['Digits']
                if choice == '9':
                    print('choice 9 detected')
                    gather.say("I am connecting you to the actual agent.")
                    gather.say("Kindly wait while i am connecting you.")
                    agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
                    response.dial(agent_number)
            else:
                speech_result = request.form['SpeechResult']
                if speech_result:
                    user_query = speech_result
                    reply, status_code = conversation(user_query)
                    # If <PLACE_ORDER_AND_END_CALL> is set then, it means the order is to be placed and conversation has to be ended.
                    if '<PLACE_ORDER_AND_END_CALL>' in reply:
                        history = get_session_attribute('user_mes')
                        set_session_attribute('history', history)
                        reply = reply.replace('<PLACE_ORDER_AND_END_CALL>', '')
                        set_session_attribute('order', "Confirm")
                        response.redirect('/place_order')
        if status_code != 200:
            gather.say(reply)
            agent_number = get_restaurants(restaurant_phone_number).redirection_phone_number
            response.dial(agent_number)
        else:
            # ---> Normal conversation reply
            gather.say(reply)
        # ---> If there is no error continue call if user doesn't say anything for next 7 seconds
        if status_code == 200 and get_session_attribute('order') != "Confirm":
            response.say("Are you still there?")
            gather = response.gather(
                action="/voice", method="POST",
                input="speech dtmf", numDigits="1",
                speechTimeout="auto",
                language='en-IN', enhanced="true",
                speechModel="phone_call",
                hints = "yes, no, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, one, two, three, four, five, six, seven, eight, nine, ten, mild, medium, hot, mango lassi, cheese naan, butter naan, naan, appetizers, vegetarian, food, Paneer Tikka Masala, Masala Chai Tea"
            )

    return str(response)


# --- Route to place the order
@application.route("/place_order", methods=['POST'])
def place_order():
    # ---> Once order is successfully placed bot says below statement
    response = VoiceResponse()
    response.say(
        "Your order has been placed successfully. You will receive a payment link via SMS. Your order will be ready in 15 to 20 minutes after payment should be done. Thank you for your business.")
    response.hangup()

    # ---> Getting order in json format using order_query of order module
    history = get_session_attribute('user_mes')
    id = get_session_attribute('session_id')
    from_ = get_session_attribute('to_number')
    to_ = get_session_attribute('from_number')

    def send_to_stripe(session_id, from_number, to_number, history):
        with application.test_request_context():
            send_stripe_payment_message(session_id, from_number, to_number, history)

    # ---> Sending payment message to customer
    thread = threading.Thread(
        target=send_to_stripe,
        args=(
            id, from_, to_, history
        )
    )
    thread.start()
    end_session()
    return str(response)


# --- Function to delete the session
def end_session():
    delete_session_attribute('session_id')
    delete_session_attribute('first_message')
    delete_session_attribute('to_number')
    delete_session_attribute('from_number')
    delete_session_attribute('user_mes')
    delete_session_attribute('history')
    delete_session_attribute('order')
    return None


if __name__ == '__main__':
    application.run(debug=True)
