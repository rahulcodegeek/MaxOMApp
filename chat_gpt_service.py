import openai
from openai import ChatCompletion, OpenAIError
from session_manager import get_session_attribute, set_session_attribute

# Initialize OpenAI
openai.api_key_path = 'resources/chatgpt_api_key'
openai.api_endpoint = 'https://api.openai.com/v1/chat/completions'


# --- Conversation with ChatGpt
def conversation(user_query):
    # --> Sending the user query to the chatgpt function
    if user_query is None or user_query.strip() == '':
        print('Error from conversation so, redirecting to actual agent...')
        return 'Sorry for inconvenience five. I am connecting you to the actual agent wait for some moments.', 500

    response, status_code = chat_gpt_query(user_query)
    return response, status_code


# --- Calls ChatGpt Api using gpt-3.5-turbo-16k model
def chat_gpt_query(user_query):
    if get_session_attribute('user_mes') is None:
        print('Error from chat query, so redirecting to actual agent...')
        return 'Sorry for inconvenience six. I am connecting you to the actual agent wait for some moments.', 400

    user_query = user_query + ' (refer to context)'
    print('user_query for chat is ', user_query)
    print('user_query is for session_id', get_session_attribute('session_id'))
    # --> Getting previous conversation
    history = get_session_attribute('user_mes')
    history.append({"role": "user", "content": user_query})
    set_session_attribute('user_mes', history)

    # --> Calling ChatGpt Api and return its reply with status 200 if successful otherwise return with status 502
    try:
        chat = ChatCompletion.create(model="gpt-4-turbo-preview", messages=get_session_attribute('user_mes'))
        #chat = ChatCompletion.create(model="gpt-3.5-turbo-1106", messages=get_session_attribute('user_mes'))
        reply = chat.choices[0].message.content
        print('reply from chat is ', reply)
        print('reply is for session_id', get_session_attribute('session_id'))
        status = 200
    except OpenAIError as e:
        print(e)
        reply = "Sorry for inconvenience seven. I am connecting you to the actual agent wait for some moments."
        status = 502

    # --> Storing updated conversation
    history = get_session_attribute('user_mes')
    history.append({"role": "assistant", "content": reply})
    set_session_attribute('user_mes', history)

    return reply, status