import openai
from openai import ChatCompletion, OpenAIError
import json

# Initialize OpenAI
openai.api_key_path = 'resources/chatgpt_api_key'
openai.api_endpoint = 'https://api.openai.com/v1/chat/completions'


# --- Conversation with ChatGpt
def conversation(history):
    # --> Sending the user query to the chatgpt function
    response, status_code = chat_gpt_query(history)
    return response, status_code


# --- Calls ChatGpt Api using gpt-3.5-turbo-16k model
def chat_gpt_query(history):
    if history is None:
        print('Error from chat query, so redirecting to actual agent...')
        reply = 'Sorry for inconvenience six. I am connecting you to the actual agent wait for some moments.'
        status = 400
    else:
        # --> Calling ChatGpt Api and return its reply with status 200 if successful otherwise return with status 502
        try:
            chat = ChatCompletion.create(model="gpt-4-0125-preview", messages=history)
            reply = chat.choices[0].message.content
            status = 200
        except OpenAIError as e:
            print(e)
            reply = "Sorry for inconvenience seven. I am connecting you to the actual agent wait for some moments."
            status = 502

    # data = {
    #     "reply": reply,
    #     "status_code": status
    # }
    # with open("./resources/" + conversation_id + ".json", 'w') as file:
    #     json.dump(data, file)

    return reply, status
