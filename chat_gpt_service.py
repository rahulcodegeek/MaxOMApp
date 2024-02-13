import openai
from openai import ChatCompletion, OpenAIError
from session_manager import get_session_attribute, set_session_attribute
import json

# Initialize OpenAI
openai.api_key_path = 'resources/chatgpt_api_key'
openai.api_endpoint = 'https://api.openai.com/v1/chat/completions'


# --- Conversation with ChatGpt
def conversation(history, session_id):
    # --> Sending the user query to the chatgpt function
    chat_gpt_query(history, session_id)
    return None


# --- Calls ChatGpt Api using gpt-3.5-turbo-16k model
def chat_gpt_query(history, session_id):
    if history is None:
        print('Error from chat query, so redirecting to actual agent...')
        reply = 'Sorry for inconvenience six. I am connecting you to the actual agent wait for some moments.'
        status = 400
    else:
        # --> Calling ChatGpt Api and return its reply with status 200 if successful otherwise return with status 502
        try:
            chat = ChatCompletion.create(model="gpt-4-turbo-preview", messages=history)
            # chat = ChatCompletion.create(model="gpt-3.5-turbo-1106", messages=get_session_attribute('user_mes'))
            reply = chat.choices[0].message.content
            status = 200
        except OpenAIError as e:
            print(e)
            reply = "Sorry for inconvenience seven. I am connecting you to the actual agent wait for some moments."
            status = 502

    data = {
        "reply": reply,
        "status_code": status
    }
    with open("./resources/"+session_id+".json", 'w') as file:
        json.dump(data, file)

    return None
