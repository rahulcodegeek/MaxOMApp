import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import openai
import pickle
from db_persisters.restaurants import get_restaurant
import json
import copy
import os
import redis

store = redis.Redis.from_url(os.environ.get('REDIS_URL'))
open_ai_api_key = os.environ.get('OPEN_AI_API_KEY')

def create_embeddings(restaurant_phone_number):
    res = get_restaurant(restaurant_phone_number)
    # Specify the path of the folder you want to create
    folder_path = "./resources/Retrievers/" + str(res.id)

    # Check if the folder already exists
    if not os.path.exists(folder_path):
        # If it doesn't exist, create the folder
        os.makedirs(folder_path)
    pickle_path = folder_path + "/Retriever" + ".pkl"
    menu_file = "./resources/"+str(res.id)+"_menu.txt"
    embeddings = []  # List to store embeddings
    lines = []  # List to store the lines corresponding to the embeddings
    client = OpenAI(api_key=open_ai_api_key)
    # Read the file and generate embeddings
    with open(menu_file, 'r', encoding='utf-8') as file:
        for menu_item in file:
            menu_item = menu_item.strip()
            if menu_item:
                print(menu_item)
                lines.append(menu_item)
                embeddings.append(
                    client.embeddings.create(input=[menu_item], model="text-embedding-3-small").data[0].embedding)

    with open(pickle_path, 'wb') as f:
        pickle.dump({'lines': lines, 'embeddings': embeddings}, f)

    print('Pickle file written', pickle_path)
    return pickle_path, 200

def load_embeddings_and_lines(pickle_path):
    # Load embeddings and lines from the pickle file
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)
    return data['lines'], np.array(data['embeddings'])

def find_similar_texts(query_text, lines, embeddings, similarity_threshold=0.4, top_n=5):
    client = openai.Client(api_key=open_ai_api_key)
    #query_text = query_text + "\n" + "Modifier Group information"

    print('find_similar_texts for ', query_text)
    # Generate query embedding
    response = client.embeddings.create(
        input=[query_text],  # Ensure input is a list for multiple texts
        model="text-embedding-3-small"  # Use an actual, valid model identifier
    )
    query_embedding = np.array(response.data[0].embedding).reshape(1, -1)
    print(query_embedding)
    # Calculate cosine similarity
    scores = cosine_similarity(query_embedding, embeddings)[0]

    # Retrieve texts with a similarity score above the threshold
    scored_texts = [(line, score) for line, score in zip(lines, scores) if score >= similarity_threshold]

    # Sort the list of tuples by score in descending order
    sorted_texts = sorted(scored_texts, key=lambda x: x[1], reverse=True)

    # Select the top_n items
    top_similar_texts = sorted_texts[:top_n]

    return top_similar_texts


def get_modifiers_information(query, restaurant_phone_number, conversation_id, menu_str):
    res = get_restaurant(restaurant_phone_number)
    # Path to your JSON file
    file_path = "./resources/"+str(res.id)+"_modifier.json" 
    
    modifier_menu_detail_return = ''
    # Read JSON data from file
    with open(file_path, 'r') as file:
        data = json.load(file)
    # Loop through each category and its modifiers
    if 'family biryani pack' in query.lower() or 'biryani pack' in query.lower() or 'family' in query.lower():
        for category, values in data.items():
            modifier_menu_detial = ''
            if len(values['modifiers']) > 0:
                in_context_modifier_items = store.lrange(conversation_id + f'-in-{category}-modifier', 0, -1)
                in_context_modifier_items_str = '\n'.join([item for item in in_context_modifier_items])
                modifier_item__ = f'Modifer Group - {category} Modifiers: (ID: {values["modifier_type_id"]}):\n'
                if modifier_item__ not in in_context_modifier_items_str:
                    modifier_menu_detail_return += modifier_item__
                    modifier_menu_detial += modifier_item__
                    for modifier in values['modifiers']:
                        modi_data = f"{modifier['name']}: ID: {modifier['id']}: Price: ${modifier['price']}\n"
                        modifier_menu_detail_return += str(modi_data)
                        modifier_menu_detial += str(modi_data)
                    modifier_menu_detail_return += "\n\n\n"
                    store.lpush(conversation_id + f'-in-{category}-modifier', modifier_menu_detial)
                else:
                    modifier_menu_detail_return += in_context_modifier_items_str

    else:
        for category, values in data.items():
            modifier_menu_detial = ''
            if 'spice level' in menu_str.lower() and category.lower() == 'spice level':
                in_context_modifier_items = store.lrange(conversation_id + f'-in-{category}-modifier', 0, -1)
                in_context_modifier_items_str = '\n'.join([item for item in in_context_modifier_items])
                modifier_item__ = f'Modifer Group - {category} Modifiers: (ID: {values["modifier_type_id"]}):\n'
                if modifier_item__ not in in_context_modifier_items_str:
                    modifier_menu_detail_return += modifier_item__
                    modifier_menu_detial += modifier_item__
                    for modifier in values['modifiers']:
                        modi_data = f"{modifier['name']}: ID: {modifier['id']}: Price: ${modifier['price']}\n"
                        modifier_menu_detail_return += str(modi_data)
                        modifier_menu_detial += str(modi_data)
                    modifier_menu_detail_return += "\n\n\n"
                    store.lpush(conversation_id + f'-in-{category}-modifier', modifier_menu_detial)
                else:
                    modifier_menu_detail_return += in_context_modifier_items_str

    return modifier_menu_detail_return


def langchain_conversation(restaurant_number, conversation_id, user_query, history):
    query_with_history = ""
    res = get_restaurant(restaurant_number)
    restaurant_information = json.loads(res.information_json)
    prompt_file = open('./resources/langchain_prompt.txt')
    pickle_path = "./resources/Retrievers/" + str(res.id) + "/Retriever" + ".pkl"
    data = prompt_file.read()
    data = data.replace("{name}", res.name)
    data = data.replace("{timings}", restaurant_information['timings'])
    data = data.replace(
        "{representative_name}", restaurant_information['representative_name']
    )
    data = data.replace("{address}", restaurant_information['address'])
    data = data.replace(
        "{today_special}", restaurant_information['today_special']
    )
    data = data.replace(
        "{welcome_message}", restaurant_information['welcome_message']
    )
    prompt_file.close()

    try:
        lines, embeddings = load_embeddings_and_lines(pickle_path)
        similar_texts = find_similar_texts(user_query, lines, embeddings)
        #print('Found similar number of items:', len(similar_texts))
        #print('Found similar number of items:', similar_texts)

        # Push each similar text into the Redis list
        for text, score in similar_texts:
            #print(f"Score: {score:.4f}, Text: {text}")
            #print('Pushing ', text, ' to cache with key ', conversation_id + '-in-context-menu-items')
            # Ensure we're inserting a string representation of the text
            store.lpush(conversation_id + '-in-context-menu-items', text)

        # Retrieve all items from the Redis list
        in_context_menu_items = store.lrange(conversation_id + '-in-context-menu-items', 0, -1)
        print('Pulling items from cache ', conversation_id + '-in-context-menu-items ', in_context_menu_items)

        in_context_menu_items_str = '\n'.join([item for item in in_context_menu_items])

        print('Replacing {context} in prompt with ', in_context_menu_items_str)
        print('Replacing {question} in prompt with ', user_query)

        modifiers = get_modifiers_information(user_query, restaurant_number, conversation_id, in_context_menu_items_str)
        menu = f'Menu Information:\n{in_context_menu_items_str}\n\n\nModifier Information:\n{modifiers}'
        data = data.replace("{menu}", menu)
        data = data.replace("{question}", user_query)

        query_with_history = copy.deepcopy(history)

        query_with_history.insert(0, {"role": "assistant", "content": data})

        print('sending the query_with_history as ***', query_with_history)

        client = OpenAI(api_key=open_ai_api_key)

        chat = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=query_with_history
        )

        reply = chat.choices[0].message.content
        return reply, 200
    except Exception as e:
        print(f"Error: {e}")
        return "Query Response Couldn't Get", 200
