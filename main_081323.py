from flask import Flask, request, session, render_template, jsonify, redirect,make_response

from flask_session import Session
from flask_cors import CORS
import asyncio
import os
import json
import uuid
import requests
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
    return 'hello MaxOM'

#--- Initializing Phone number to Restaurant mapper
def fetch_restaurant_ids_for_phone_numbers():
    phone_numbers_to_restaurant_ids_config = Properties()
    with open('resources/phone_number_restaurant_mapping.properties', 'rb') as config_file:
        phone_numbers_to_restaurant_ids_config.load(config_file)
        config_file.close()
    return phone_numbers_to_restaurant_ids_config

@application.route("/initialize/<phone_number>/menu", methods=['POST'])
def initialize_application_menu(phone_number):
    phone_numbers_to_restaurant_ids_config = fetch_restaurant_ids_for_phone_numbers()
    if phone_numbers_to_restaurant_ids_config.get(phone_number).data:
        restaurant_id = phone_numbers_to_restaurant_ids_config.get(phone_number).data
        fetched_menu = fetch_remote_menu(restaurant_id)
        persist_menu(restaurant_id, fetched_menu.text)
        return ('Initialization for Menu Completed')
    else:
        print(phone_number, 'not found in the mapping file')
        return ('Initialization for Menu Failed')

#pre-requisite currently is to run the initialize_application_menu before calling initialize_application_prompt
@application.route("/initialize/<phone_number>/prompt", methods=['POST'])
def initialize_application_prompt(phone_number):
    phone_numbers_to_restaurant_ids_config = fetch_restaurant_ids_for_phone_numbers()
    if phone_numbers_to_restaurant_ids_config.get(phone_number).data:
        restaurant_id = phone_numbers_to_restaurant_ids_config.get(phone_number).data
        return create_prompt_data(restaurant_id)
    else:
        print(phone_number, 'not found in the mapping file')
        return ('Initialization for Prompt Failed')

@application.route("/answer/<restaurant_phone_number>/<calling_phone_number>", methods=['POST'])
def answer(restaurant_phone_number, calling_phone_number):
    reply = ''
    if 'session_id' not in session:
        print("'session_id' not in session")
        create_session()
        initialize_application_menu(restaurant_phone_number)
        prompt_data = initialize_application_prompt(restaurant_phone_number)
        history = [{"role": "assistant", "content": prompt_data}]

        #TODO: figure out what's the difference between user_mes and history from below
        set_session_attribute('first_message', 'True')
        set_session_attribute('to_number', str(restaurant_phone_number))
        set_session_attribute('from_number', str(calling_phone_number))
        set_session_attribute('user_mes', history)
        set_session_attribute('history', history)
        set_session_attribute('order', 'Not-Confirm')


    if get_session_attribute('first_message') == 'True' :
        print("'first_message' is True $$$$")
        #First Hard code Query
        first_user_query = "Hi"
        #--- Getting reply from CHATGPT
        welcome_message = conversation(first_user_query)
        reply = welcome_message
        set_session_attribute('first_message', 'False')

    elif get_session_attribute('first_message') == 'False':
        print("'first_message' is False $$$$")
        reply = conversation("Yes that is correct")
        # Get the speech recognition result
        #TODO: Plugin deepgram or AssemblyAI etc here...so, input from these STT can be set in speech_result
        #speech_result = request.form['SpeechResult']

        #if speech_result:
        #    user_query = speech_result
        #    reply = conversation(user_query)
        #    if '<GOAWAY>' in reply:
        #        history = get_session_attribute('user_mes')
        #        set_session_attribute('history', history)
        #        reply = reply.replace('<GOAWAY>', '')
    print("Reply is : $$$$$$$$", reply)
    return reply

@application.route("/answer/<restaurant_phone_number>/<calling_phone_number>", methods=['DELETE'])
def endConversation(restaurant_phone_number, calling_phone_number):
    reply = ''
    delete_session_attribute('session_id')
    delete_session_attribute('first_message')
    delete_session_attribute('to_number')
    delete_session_attribute('from_number')
    delete_session_attribute('user_mes')
    delete_session_attribute('history')
    delete_session_attribute('order')
    return reply

@application.route("/voice", methods=['GET', 'POST'])
def voice():
    # Start our TwiML response
    resp = VoiceResponse()

    # Read a message aloud to the caller
    resp.say("Hello I am Amy from Paradise restaurant!")
    print('returning ', resp)
    return str(resp)

if __name__ == '__main__':
    application.run()
