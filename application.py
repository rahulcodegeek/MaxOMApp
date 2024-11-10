from datetime import datetime, time
import pytz

from fillers_information import get_randomly_filler_sentence, get_randomly_question_filler_sentence
from call_status import CallStatus
from database import db

from flask import Flask, request, session, render_template, send_file
from flask_session import Session
from flask_cors import CORS
import threading

from db_persisters.customer import add_customer
from db_persisters.conversation import add_conversation, make_conversation_template
from db_persisters.restaurants import add_restaurant, get_restaurant
from db_persisters.restaurant_system_configuration import add_restaurant_configuration

from menu_service import fetch_remote_menu, persist_menu, load_menu
from langchain_service_1 import langchain_conversation, create_embeddings
from order_without_payment import persist_and_send_order_to_pos
from db_persisters.call_logs import add_call_log
from restaurant_order_timings_service import is_restaurant_open

import os
import json
import sys
from file_logger import FileLogger
import zipfile
import redis
import uuid
import traceback


RESTAURANT_NAME_KEY = 'restaurant_name'
RESTAURANT_NUMBER_KEY = 'restaurant_number'
REDIRECTING_NUMBER_KEY = 'redirecting_number'
RESTAURANT_INFORMATION_KEY = 'restaurant_information'

POS_TYPE_KEY = 'pos_type'
POS_URL_KEY = 'pos_url'
POS_AUTHORIZATION_HEADER_KEY = 'pos_authorization_header'
POS_TAX_RATE_CODE_KEY = 'pos_tax_rate_code'

TIMINGS_KEY = 'timings'
REPRESENTATIVE_NAME_KEY = 'representative_name'
TODAY_SPECIAL_KEY = 'today_special'
WELCOME_MESSAGE_KEY = 'welcome_message'
RESTAURANT_TIMEZONE_KEY = 'restaurant_timezone'
PHONE_ORDERS_TIME_GAP_AFTER_START_TIME = 'phone_orders_time_gap_in_minutes_after_start_time'
PHONE_ORDERS_TIME_GAP_BEFORE_END_TIME = 'phone_orders_time_gap_in_minutes_before_end_time'
KEY_MISSING = ' key missing'

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

# socketio = SocketIO(application, cors_allowed_origins="*")

store = redis.Redis.from_url(os.environ.get('REDIS_URL'))
database_url = os.environ.get('DB_URL')

is_test_mode = os.environ.get('IS_TEST_MODE')

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
    print('data being sent back ', str(data))
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

def validate_restaurant_information(restaurant_information):
    validation_failure_reason = []
    if TIMINGS_KEY not in restaurant_information:
        validation_failure_reason.append(TIMINGS_KEY + KEY_MISSING)
    if REPRESENTATIVE_NAME_KEY not in restaurant_information:
        validation_failure_reason.append(REPRESENTATIVE_NAME_KEY + KEY_MISSING)
    if TODAY_SPECIAL_KEY not in restaurant_information:
        validation_failure_reason.append(TODAY_SPECIAL_KEY + KEY_MISSING)
    if WELCOME_MESSAGE_KEY not in restaurant_information:
        validation_failure_reason.append(WELCOME_MESSAGE_KEY + KEY_MISSING)
    if RESTAURANT_TIMEZONE_KEY not in restaurant_information:
        validation_failure_reason.append(RESTAURANT_TIMEZONE_KEY + KEY_MISSING)
    if PHONE_ORDERS_TIME_GAP_AFTER_START_TIME not in restaurant_information:
        validation_failure_reason.append(PHONE_ORDERS_TIME_GAP_AFTER_START_TIME + KEY_MISSING)
    if PHONE_ORDERS_TIME_GAP_BEFORE_END_TIME not in restaurant_information:
        validation_failure_reason.append(PHONE_ORDERS_TIME_GAP_BEFORE_END_TIME + KEY_MISSING)

    # some extra validations
    if RESTAURANT_TIMEZONE_KEY in restaurant_information:
        try:
            pytz.timezone(restaurant_information[RESTAURANT_TIMEZONE_KEY])
        except pytz.exceptions.UnknownTimeZoneError as unknown_time_zone_error:
            validation_failure_reason.append(str(pytz.exceptions.UnknownTimeZoneError(unknown_time_zone_error)))

    phone_orders_time_gap_in_minutes_after_start_time = -1
    phone_orders_time_gap_in_minutes_before_end_time = -1

    if PHONE_ORDERS_TIME_GAP_AFTER_START_TIME in restaurant_information:
        try:
            phone_orders_time_gap_in_minutes_after_start_time = int(restaurant_information[PHONE_ORDERS_TIME_GAP_AFTER_START_TIME])

            if phone_orders_time_gap_in_minutes_after_start_time < 0 or phone_orders_time_gap_in_minutes_after_start_time > 300:
                validation_failure_reason.append(
                    PHONE_ORDERS_TIME_GAP_AFTER_START_TIME + ' value should be between 0 and 300')
        except ValueError as e:
            # If the conversion fails, raise an exception
            validation_failure_reason.append(str(ValueError(PHONE_ORDERS_TIME_GAP_AFTER_START_TIME +' key value should be an integer')))

    if PHONE_ORDERS_TIME_GAP_BEFORE_END_TIME in restaurant_information:
        try:
            phone_orders_time_gap_in_minutes_before_end_time = int(restaurant_information[PHONE_ORDERS_TIME_GAP_BEFORE_END_TIME])
            if phone_orders_time_gap_in_minutes_before_end_time < 0 or phone_orders_time_gap_in_minutes_before_end_time > 300:
                validation_failure_reason.append(
                    PHONE_ORDERS_TIME_GAP_BEFORE_END_TIME+ ' value should be between 0 and 300')
        except ValueError:
            # If the conversion fails, raise an exception
            validation_failure_reason.append(str(ValueError(PHONE_ORDERS_TIME_GAP_BEFORE_END_TIME + ' key value should be an integer')))

    if len(validation_failure_reason) > 0:
        raise KeyError(validation_failure_reason)


@application.route('/add_restaurant', methods=['POST'])
def add_restaurant_database():
    data = request.json
    restaurant_name = data[RESTAURANT_NAME_KEY]
    restaurant_number = data[RESTAURANT_NUMBER_KEY]
    redirecting_number = data[REDIRECTING_NUMBER_KEY]
    restaurant_information = data[RESTAURANT_INFORMATION_KEY]
    pos_type = data[POS_TYPE_KEY]
    pos_url = data[POS_URL_KEY]
    pos_authorization_header = data[POS_AUTHORIZATION_HEADER_KEY]
    pos_tax_rate_code = data[POS_TAX_RATE_CODE_KEY]
    voice_api_type = data['voice_api_type']
    voice_api_account_sid = data['voice_api_account_sid']
    voice_api_account_auth_token = data['voice_api_account_auth_token']
    payment_api_key = data['payment_api_key']
    payment_secret = data['payment_secret']
    print('In add restaurant restaurant_information=', restaurant_information)
    try:
        validate_restaurant_information(restaurant_information)
        print('restaurant_information Validation passed')
    except KeyError as key_error:
        print('restaurant_information Validation failed', str(key_error))
        return str(key_error), 400

    print('Adding restaurant to configuration...')
    persisted_restaurant_id = add_restaurant(restaurant_name, restaurant_number,redirecting_number, restaurant_information)
    add_restaurant_configuration(
        persisted_restaurant_id,
        pos_type, pos_url, pos_authorization_header, pos_tax_rate_code,
        voice_api_type, voice_api_account_sid, voice_api_account_auth_token,
        payment_api_key, payment_secret
    )

    initialize_application_menu(restaurant_number)
    print('Menu initialized..')
    create_embeddings(restaurant_number)
    print('Embeddings initialized..')
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
    restaurant = get_restaurant(restaurant_phone_number)
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
        traceback.print_exc()
        # TODO - change this error as this is now an offline operation and not on the call operation
        return "Sorry for inconvenience three. I am connecting you to the actual agent wait for some moments.", 501


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
    if "reason" in data:
        reason = data['reason']
    else:
        reason = "Unknown Reason"
    conversation_dictionary = store.hgetall(conversation_id)
    res = get_restaurant(conversation_dictionary['to_number'])
    disconnect_response = json.dumps(disconnect_response)
    add_call_log(conversation_id, res.id, CallStatus.DISCONNECTED, str(reason))
    # ---> Getting order in json format using order_query of order module
    history = store.lrange(conversation_id + '-user_mes', 0, -1)

    formatted_history = []
    for message_str in history:
        message = json.loads(message_str)
        formatted_history.append(message)
    # the following condition is a quickfix to prevent the race condition in the async operation to place the order that
    # happens after the disconnect. This is because same operations below are also done during placing the order
    # (in case the order is Confirmed). If the order is not confirmed then only we create the customer and log the
    # conversation from te below block of the code.
    if conversation_dictionary['order'] == 'Not-Confirm':
        conversation_text = make_conversation_template(formatted_history)
        customer_id = add_customer(res.id, "Guest", conversation_dictionary['from_number'])
        add_conversation(res.id, customer_id, conversation_id, conversation_text)
    return str(disconnect_response)


@application.route("/conversation/<conversation_id>/activities", methods=['POST'])
def activities(conversation_id):
    status_code = 200
    data = json.loads(request.get_data())
    print('request in activities POST method is ***', data)
    print('session contains', session)

    conversation_id = data['conversation']

    reply = ''
    if 'parameters' in data['activities'][0] and 'callee' in data['activities'][0]['parameters']:
        res = get_restaurant(data['activities'][0]['parameters']['callee'])
    else:
        conversation_dictionary = store.hgetall(conversation_id)
        res = get_restaurant(conversation_dictionary['to_number'])
    try:
        if (data['activities'][0]['type'] == 'message' or
                (data['activities'][0]['type'] == 'event' and data['activities'][0]['name'] == 'start')):
            conversation_dictionary = store.hgetall(conversation_id)
            # this if will only execute if the payload is a start event which happens at the beginning of the call
            if len(conversation_dictionary) == 0:
                # TODO -- properly fetch these values from the start event
                restaurant_phone_number = data['activities'][0]['parameters']['callee']
                calling_phone_number = data['activities'][0]['parameters']['caller']
                print('restaurant_phone_number and calling_phone_number fetched from the start event payload as ',
                      restaurant_phone_number, calling_phone_number)
                # set the cache with all the relevant parameters from the start event and also initialize the dictionary
                store.hset(conversation_id, 'first_message', "True")
                store.hset(conversation_id, 'to_number', str(restaurant_phone_number))
                store.hset(conversation_id, 'from_number', str(calling_phone_number))
                store.hset(conversation_id, 'order', 'Not-Confirm')
                redirection_number = get_restaurant(restaurant_phone_number).redirection_phone_number
                store.hset(conversation_id, 'redirection_number', str(redirection_number))
                conversation_dictionary = store.hgetall(conversation_id)
                # persist the STARTED call event
                add_call_log(conversation_id, res.id, CallStatus.STARTED,
                             'Call received from ' + str(calling_phone_number))

            # the voice message has arrived and the order is Confirmed
            if len(conversation_dictionary) != 0 and store.hgetall(conversation_id)['order'] == 'Confirm':
                print('Confirming the order from voice block for from_number, session_id',
                        conversation_dictionary['from_number'], conversation_id)
                hangup_response = form_hangup_response('Order Confirmed')
                print('returning hangup_response from the order Confirm block ', hangup_response)
                return str(hangup_response)
            # this is the normal conversation path
            else:
                conversation_dictionary = store.hgetall(conversation_id)
                if (len(conversation_dictionary) != 0 and conversation_dictionary['first_message'] == "True"
                       and status_code == 200):
                    # check if restaurant is open and this is checked when returning the default welcome_message only
                    if is_restaurant_open(res.id):
                        # ---> First Hard code Query
                        print('first_message is True, so flowing through first_message block')
                        first_user_query = "Hi"
                        # ---> Getting reply from
                        user_query = first_user_query + ' (refer to context)'
                        print('user_query for chat is ', user_query)
                        print('user_query is for session_id', conversation_id)
                        # --> Getting previous conversation
                        history = store.lrange(conversation_id + '-user_mes', 0, -1)

                        # Deserialize the messages
                        formatted_history = []
                        for message_str in history:
                            message = json.loads(message_str)
                            formatted_history.append(message)

                        formatted_history.append({"role": "user", "content": user_query})
                        store.rpush(conversation_id + '-user_mes',
                                    json.dumps({"role": "user", "content": user_query}))
                        reply, status_code = langchain_conversation(conversation_dictionary['to_number'],
                                                                    conversation_id,
                                                                    user_query,
                                                                    formatted_history)
                        print('welcome_message from chat is ', reply)
                        print('welcome_message is for session_id', conversation_id)
                        # --> Storing updated conversation
                        history.append({"role": "assistant", "content": reply})
                        store.rpush(conversation_id + '-user_mes',
                                    json.dumps({"role": "assistant", "content": reply}))
                        store.hset(conversation_id, 'first_message', "False")
                    else:
                        redirect_response = form_redirection_response(conversation_dictionary['redirection_number'],
                                                                      conversation_id,
                                                                      "Restaurant is closed or unable to help place the order during this time")
                        print('returning redirect_response  ', redirect_response)
                        return str(redirect_response)

                # the call flow comes here when the welcome message has been played and user is chatting now
                elif len(conversation_dictionary) != 0 and conversation_dictionary['first_message'] == "False":
                    # ---> Get the speech recognition result
                    history = store.lrange(conversation_id + '-user_mes', 0, -1)
                    print('history is ', history)
                    # Deserialize the messages
                    formatted_history = []
                    for message_str in history:
                        message = json.loads(message_str)
                        formatted_history.append(message)

                    user_query = data['activities'][0]['text']
                    user_query_to_lower_case = user_query.lower()
                    # forward the call to the redirection number in case the user has mentioned any of the following words

                    formatted_history.append({"role": "user", "content": user_query})
                    store.rpush(conversation_id + '-user_mes', json.dumps({"role": "user", "content": user_query}))

                    call_redirection_phrase_match = ['agent',
                                                     'customer service',
                                                     'human',
                                                     'family biryani pack',
                                                     'biryani pack',
                                                     'family',
                                                     'representative',
                                                     'can i speak to someone',
                                                     'can i speak to someone else',
                                                     'uber eats',
                                                     'door dash',
                                                     'doordash',
                                                     'crab calling',
                                                     'real person',
                                                     'can i talk to some one',
                                                     'can i talk to someone',
                                                     'Connect me to the team member',
                                                     'talk to a person',
                                                     'talk to someone',
                                                     'somebody',
                                                     'catering']

                    if (any(ele in user_query_to_lower_case for ele in call_redirection_phrase_match) and
                            store.hgetall(conversation_id)['order'] != 'Confirm'):
                        redirect_response = form_redirection_response(conversation_dictionary['redirection_number'],
                                                                      conversation_id, "On User request")
                        print('returning redirect_response  ', redirect_response)
                        return str(redirect_response)

                    print('user_query is normal conversation is ', user_query)

                    #normal conversation path
                    reply, status_code = langchain_conversation(conversation_dictionary['to_number'],
                                                                conversation_id,
                                                                user_query,
                                                                formatted_history)

                    print('response in first_message False from chat is ', conversation_id, reply)
                    # --> Storing updated conversation

                    history.append({"role": "assistant", "content": reply})
                    store.rpush(conversation_id + '-user_mes', json.dumps({"role": "assistant", "content": reply}))

                    # If <PLACE_ORDER_AND_END_CALL> is set then, it means the order is to be placed and conversation has to be ended.
                    if '<PLACE_ORDER_AND_END_CALL>' in reply:
                        reply = reply.replace('<PLACE_ORDER_AND_END_CALL>', '')
                        store.hset(conversation_id, 'order', 'Confirm')
                        print('Confirming the order from <PLACE_ORDER_AND_END_CALL> in the response for',
                              conversation_id)
                        status_code = place_order(conversation_id)
                        print('From <PLACE_ORDER_AND_END_CALL> block for conversation_id response is',
                              conversation_id,
                              status_code, reply)
                print('Flow at Stage 1, status_code=', status_code)
                print('Flow at Stage 2, is status_code not 200', status_code != 200)
                if status_code != 200:
                    redirect_response = form_redirection_response(conversation_dictionary['redirection_number'],
                                                                  conversation_id, "Error In Chat GPT Service")
                    print('returning redirect_response  ', redirect_response)
                    return str(redirect_response)
                else:
                    # ---> Normal conversation reply
                    print('cache [order] value is ', store.hgetall(conversation_id)['order'])
                    normal_response = form_response(reply, user_query)
                    print('returning normal_response from the respective block ', normal_response)
                    return str(normal_response)

        # As per the current implementation the flow should only come here in case of transferStatus event
        else:
            if data['activities'][0]['type'] == 'event' and data['activities'][0]['name'] == 'transferStatus':
                print('As per the current implementation the flow should only come here in case of transferStatus event')
                transfer_status_value = data['activities'][0]['value']
                if transfer_status_value['status'] == 'answered':
                    reason = transfer_status_value['status']
                    add_call_log(conversation_id, res.id, CallStatus.TRANSFER_SUCCESSFUL, str(reason))
                else:
                    reason = (transfer_status_value['status']
                              + ', reasonCode -', transfer_status_value['reasonCode']
                              + ', reason -', transfer_status_value['reason'])
                    add_call_log(conversation_id, res.id, CallStatus.TRANSFER_FAILED, str(reason))
            normal_response = form_response("{}", '')
            return str(normal_response)


    except Exception as e:
        traceback.print_exc()
        # assuming that by now we will have the conversation_dictionary set..
        redirect_response = form_redirection_response(conversation_dictionary['redirection_number'], conversation_id,
                                                      str(e))
        print("In Exception block..")
        print('returning redirect_response  ', redirect_response)
        return str(redirect_response)


def form_hangup_response(reason):
    hangup_response = {
        'activities': [
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'event',
                'name': 'hangup'
            }
        ]
    }
    return json.dumps(hangup_response)


def form_response(reply, user_query):
    filler = ''
    if '?' in user_query:
        filler = get_randomly_question_filler_sentence()
    else:
        filler = get_randomly_filler_sentence()
    normal_response = {
        'activities': [
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'language': 'en-US',
                'type': 'message',
                'text': '<prosody rate="120%">' + reply + '</prosody>',
                'sessionParams': {
                    'botNoInputSpeech': '<prosody rate="120%">' + filler + '</prosody>'
                }
            }
        ]
    }
    return json.dumps(normal_response)


def form_response_with_hangup(reply):
    normal_response = {
        'activities': [
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'language': 'en-US',
                'type': 'message',
                'text': reply
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'event',
                'name': 'hangup'
            }
        ]
    }
    return json.dumps(normal_response)


def form_redirection_response(redirection_number, conversation_id, reason):
    conversation_dictionary = store.hgetall(conversation_id)
    res = get_restaurant(conversation_dictionary['to_number'])
    add_call_log(conversation_id, res.id, CallStatus.TRANSFER_ATTEMPTED, str(reason))

    # ---> Getting order in json format using order_query of order module
    history = store.lrange(conversation_id + '-user_mes', 0, -1)

    formatted_history = []
    for message_str in history:
        message = json.loads(message_str)
        formatted_history.append(message)
    convertion_text = make_conversation_template(formatted_history)
    customer_id = add_customer(res.id, "Guest", conversation_dictionary['from_number'])
    conversation_id = add_conversation(res.id, customer_id, conversation_id, convertion_text)

    redirect_response = {
        'activities': [
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'language': 'en-US',
                'type': 'message',
                'text': 'Transferring your call to the restaurant'
            },
            {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'event',
                'name': 'transfer',
                'activityParams': {
                    'transferTarget': 'tel:' + redirection_number,
                    'transferNotifications': True,
                    'transferNotificationsHangupMS': 2000
                }
            }
        ]
    }
    return json.dumps(redirect_response)


# filler and voice_error_handler

# --- Route to place the order
@application.route("/place_order", methods=['POST'])
def place_order(conversation_id):
    conversation_dictionary = store.hgetall(conversation_id)
    # ---> Getting order in json format using order_query of order module
    history = store.lrange(conversation_id + '-user_mes', 0, -1)

    formatted_history = []
    for message_str in history:
        message = json.loads(message_str)
        formatted_history.append(message)

    from_ = conversation_dictionary['from_number']
    to_ = conversation_dictionary['to_number']

    def local_persist_and_send_order_to_pos(local_history, local_from, local_to, local_is_test_mode,
                                            local_conversation_id):
        with application.test_request_context():
            persist_and_send_order_to_pos(local_history, local_from, local_to, local_is_test_mode,
                                          local_conversation_id)

    # ---> Sending payment message to customer
    thread = threading.Thread(
        target=local_persist_and_send_order_to_pos,
        args=(
            formatted_history, from_, to_, is_test_mode, conversation_id
        )
    )

    thread.start()
    # TODO - delete the cache entries
    print("End session called from place_order for session ", conversation_id)

    # store.delete(conversation_id)

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
        traceback.print_exc()
        return str(e)


if __name__ == '__main__':
    application.run(debug=True)
