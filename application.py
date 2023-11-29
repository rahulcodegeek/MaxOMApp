from chat_gpt_service import conversation
from database import db
from flask import Flask, request, session, render_template
from flask_session import Session
from flask_cors import CORS
from jproperties import Properties
from menu_service import fetch_remote_menu, persist_menu
from order import order_query, Send_Order_to_clover
from prompt_service import create_prompt_data
from session_manager import create_session, set_session_attribute, \
    get_session_attribute, delete_session_attribute
from StripePython import send_stripe_payment_message
from twilio.twiml.voice_response import VoiceResponse
import threading
from restaurant_bots import get_bot


application = Flask(__name__)
# You can choose a different session type if needed
application.config['SESSION_TYPE'] = 'filesystem'
# Session data is not permanent
application.config['SESSION_PERMANENT'] = False
Session(application)
# --- Enable CORS for all routes in the app
CORS(application)

# --- Enable database
database_url = "mysql+pymysql://admin:voicebot@restuarantdatabase.cwr0mrljgsss.eu-west-1.rds.amazonaws.com:3306/restuarantvoicebot"
# database_url = 'mysql://root:''@localhost:3308/restaurant'
application.config["SQLALCHEMY_DATABASE_URI"] = database_url
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(application)


# ------------ Routes ------------
# --- Home Route
@application.route('/')
def hello_maxom():
    return 'Hello from MaxOM'


# --- Route to create the database tables which is defined in database file
@application.route('/create_db_tables')
def create_db_tables():
    db.create_all()
    return 'Database Tables Created'


# --- Route to delete the database all tables
@application.route('/delete_db_tables')
def delete_db_tables():
    db.drop_all()
    return 'Database Tables Deleted'


# --- Route to have a successful stripe payment
@application.route('/payment_successful')
def payment_successful():
    # ---> Getting order id and restaurant id to pass in the Send
    # ---> Order to clover function of order module
    order_id = request.args.get('order_id')
    bot_id = request.args.get('bot_id')
    Send_Order_to_clover(order_id, bot_id)
    return render_template('success.html')


# --- Route to have a failed stripe payment
@application.route('/payment_failed')
def payment_failed():
    return render_template('fail.html')


# --- Function for initializing phone number to restaurant mapper
def fetch_restaurant_ids_for_phone_numbers():
    phone_numbers_to_restaurant_ids_config = Properties()
    with open('resources/phone_number_restaurant_mapping.properties', 'rb') as config_file:
        phone_numbers_to_restaurant_ids_config.load(config_file)
        config_file.close()
    return phone_numbers_to_restaurant_ids_config


# --- Route for initializing phone number to restaurant mapper
@application.route("/initialize/<restaurant_phone_number>/menu", methods=['POST'])
def initialize_application_menu(restaurant_phone_number):
    phone_numbers_to_restaurant_ids_config = fetch_restaurant_ids_for_phone_numbers()
    try:
        restaurant_id = phone_numbers_to_restaurant_ids_config.get(restaurant_phone_number).data
    except Exception as e:
        print(restaurant_phone_number, 'not found in the mapping file')
        return "Sorry for inconvenience. I am connecting you to the actual agent wait for some moments!", 500

    try:
        fetched_menu, status_code = fetch_remote_menu(restaurant_id, "items")
        if status_code == 200:
            persist_menu(restaurant_id, fetched_menu.text)
            return ('Initialization for Menu Completed'), status_code
        return fetched_menu, status_code
    except:
        print('No properties found for restaurant associate with the phone number', restaurant_phone_number)
        return "Sorry for inconvenience. I am connecting you to the actual agent wait for some moments.", 501


# --- Function for creating the prompt for the restaurant phone number
def initialize_application_prompt(restaurant_phone_number):
    reply, status_code = initialize_application_menu(restaurant_phone_number)
    if status_code != 200:
        return reply, status_code
    phone_numbers_to_restaurant_ids_config = fetch_restaurant_ids_for_phone_numbers()
    try:
        restaurant_id = phone_numbers_to_restaurant_ids_config.get(restaurant_phone_number).data
        prompt_data, status_code = create_prompt_data(restaurant_id)
        return prompt_data, status_code
    except Exception as e:
        print(e)
        return "Sorry for inconvenience. I am connecting you to the actual agent wait for some moments", 500


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
        create_session()
        set_session_attribute('first_message', True)
        set_session_attribute('to_number', str(restaurant_phone_number))
        set_session_attribute('from_number', str(calling_phone_number))
        set_session_attribute('order', 'Not-Confirm')
        # ---> Initiating the prompt for the restaurant phone number
        prompt_data, status_code = initialize_application_prompt(restaurant_phone_number)
        # ---> In case there is an error so say that otherwise will overwrite in the next if condition
        reply = prompt_data
        history = [{"role": "assistant", "content": prompt_data}]
        set_session_attribute('user_mes', history)
    if get_session_attribute('order') == "Confirm":
        response.redirect('/place_order')
    else:
        gather = response.gather(action="/voice", method="POST", input="speech dtmf", numDigits="1",
                                 speechTimeout="auto", timeout=7, language='en-IN', enhanced="true",
                                 speechModel="phone_call")
        if get_session_attribute('first_message') == True and status_code == 200:
            # ---> First Hard code Query
            first_user_query = "Hi"
            # ---> Getting reply from CHATGPT
            welcome_message, status_code = conversation(first_user_query)
            reply = welcome_message
            set_session_attribute('first_message', False)
        elif get_session_attribute('first_message') == False:
            # ---> Get the speech recognition result
            if "Digits" in request.values:
                choice = request.values['Digits']
                if choice == '9':
                    gather.say("I am connecting you to the actual agent wait for some moments")
                    agent_number = get_bot(restaurant_phone_number).agent_number
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
            agent_number = get_bot(restaurant_phone_number).agent_number
            response.dial(agent_number)
        else:
            # ---> Normal conversation reply
            gather.say(reply)
        # ---> If there is no error continue call if user doesn't say anything for next 7 seconds
        if status_code == 200 and get_session_attribute('order') != "Confirm":
            response.say("Are you still there?")
            gather = response.gather(action="/voice", method="POST", input="speech dtmf", numDigits="1",
                                     speechTimeout="auto", language='en-IN', enhanced="true", speechModel="phone_call")

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
