from flask import Flask, request, session, render_template, jsonify, redirect, make_response

from flask_session import Session
from flask_cors import CORS
from jproperties import Properties

from menu_service import fetch_remote_menu, persist_menu
from prompt_service import create_prompt_data
from session_manager import create_session, set_session_attribute, get_session_attribute, delete_session_attribute
from chat_gpt_service import conversation
from twilio.twiml.voice_response import VoiceResponse

application = Flask(__name__)
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"
Session(application)
CORS(application)  # Enable CORS for all routes in the app


@application.route('/')
def hello_maxom():
    return 'Hello from MaxOM'


# --- Initializing Phone number to Restaurant mapper
def fetch_restaurant_ids_for_phone_numbers():
    phone_numbers_to_restaurant_ids_config = Properties()
    with open('resources/phone_number_restaurant_mapping.properties', 'rb') as config_file:
        phone_numbers_to_restaurant_ids_config.load(config_file)
        config_file.close()
    return phone_numbers_to_restaurant_ids_config


@application.route("/initialize/<restaurant_phone_number>/menu", methods=['POST'])
def initialize_application_menu(restaurant_phone_number):
    phone_numbers_to_restaurant_ids_config = fetch_restaurant_ids_for_phone_numbers()
    if phone_numbers_to_restaurant_ids_config.get(restaurant_phone_number).data:
        restaurant_id = phone_numbers_to_restaurant_ids_config.get(restaurant_phone_number).data
        fetched_menu = fetch_remote_menu(restaurant_id)
        persist_menu(restaurant_id, fetched_menu.text)
        return ('Initialization for Menu Completed')
    else:
        print(restaurant_phone_number, 'not found in the mapping file')
        return ('Initialization for Menu Failed')


def initialize_application_prompt(restaurant_phone_number):
    initialize_application_menu(restaurant_phone_number)
    phone_numbers_to_restaurant_ids_config = fetch_restaurant_ids_for_phone_numbers()
    if phone_numbers_to_restaurant_ids_config.get(restaurant_phone_number).data:
        restaurant_id = phone_numbers_to_restaurant_ids_config.get(restaurant_phone_number).data
        return create_prompt_data(restaurant_id)
    else:
        print(restaurant_phone_number, 'not found in the mapping file')
        return ('Initialization for Prompt Failed')


@application.route("/voice", methods=['POST'])
def voice():
    response = VoiceResponse()
    restaurant_phone_number = request.form['To']
    calling_phone_number = request.form.get('From')
    # print('restaurant_phone_number', restaurant_phone_number)
    # print('calling_phone_number', calling_phone_number)
    gather = response.gather(action="/voice", method="POST", enhanced="true", speechModel="phone_call", input="speech",
                             speechTimeout="auto", timeout=7)

    reply = ''

    # Initiate the session if not already initialized
    if 'session_id' not in session:
        # print("'session_id' not in session")
        create_session()
        prompt_data = initialize_application_prompt(restaurant_phone_number)
        history = [{"role": "assistant", "content": prompt_data}]

        # TODO: figure out what's the difference between user_mes and history from below
        set_session_attribute('first_message', 'True')
        set_session_attribute('to_number', str(restaurant_phone_number))
        set_session_attribute('from_number', str(calling_phone_number))
        set_session_attribute('user_mes', history)
        set_session_attribute('history', history)
        set_session_attribute('order', 'Not-Confirm')

    else:
        # If this is the first message, greet the user and set the first_message attribute in the session to False
        if get_session_attribute('first_message') == 'True':
            # print("1 first_message is True")
            # First Hard code Query
            first_user_query = "Hi"
            # --- Getting reply from CHATGPT
            welcome_message = conversation(first_user_query)
            reply = welcome_message
            set_session_attribute('first_message', 'False')
        # If this is not the first message, then carry on the conversation
        elif get_session_attribute('first_message') == 'False':
            # print("2 first_message is False")
            # Get the speech recognition result
            # TODO: Plugin deepgram or AssemblyAI etc here...so, input from these STT can be set in speech_result
            speech_result = request.form['SpeechResult']

            if speech_result:
                # print("3 SpeechResult", speech_result)
                user_query = speech_result
                reply = conversation(user_query)
                # print("4 Reply", reply)
                # If <PLACE_ORDER_AND_END_CALL> is set then, it means the order is to be placed and conversation has to be ended.
                if '<PLACE_ORDER_AND_END_CALL>' in reply:
                    history = get_session_attribute('user_mes')
                    set_session_attribute('history', history)
                    reply = reply.replace('<PLACE_ORDER_AND_END_CALL>', '')

                    response.say("Kindly wait a moment while we place your order.")
                    # print("5 Redirecting to /place_order")
                    response.redirect('/place_order')
                    # TODO - Save the convo
    # print("6 gather.say(reply)", reply)
    gather.say(reply)
    # print("7 After gather.say(reply)")
    response.say("Are you still there?")
    # print("8 response.say(\"Are you still there?\") and gather action")
    gather = response.gather(action="/voice", method="POST", enhanced="true", speechModel="phone_call", input="speech",
                             speechTimeout="auto")
    # print("9 Returning ", str(response))
    return str(response)


@application.route("/place_order", methods=['POST'])
def place_order():
    response = VoiceResponse()
    # TODO - Put the logic here to place the order and save the order.
    # print("5a Redirected to /place_order")
    response.say("Your Order has been placed successfully, thank you for your business.")
    end_session()
    response.hangup()
    return None


def end_session():
    # print("5b end_conversation")
    delete_session_attribute('session_id')
    delete_session_attribute('first_message')
    delete_session_attribute('to_number')
    delete_session_attribute('from_number')
    delete_session_attribute('user_mes')
    delete_session_attribute('history')
    delete_session_attribute('order')
    return None


if __name__ == '__main__':
    application.run()
