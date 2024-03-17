import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import openai
import pickle
from db_persisters.restaurants import get_restaurants
import json
import copy
import os
import redis

store = redis.Redis.from_url(os.environ.get('REDIS_URL'))
open_ai_api_key = os.environ.get('OPEN_AI_API_KEY')

def create_embeddings(restaurant_phone_number):
    res = get_restaurants(restaurant_phone_number)
    pickle_path = "./resources/Retrievers/" + str(res.id) + "_Retriever" + ".pkl"
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

def langchain_conversation(restaurant_number, conversation_id, user_query, history):
    query_with_history = ""
    res = get_restaurants(restaurant_number)
    restaurant_information = json.loads(res.information_json)
    prompt_file = open('./resources/langchain_prompt.txt')
    pickle_path = "./resources/Retrievers/" + str(res.id) + "_Retriever" + ".pkl"
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
    prompt_file.close()

    try:
        lines, embeddings = load_embeddings_and_lines(pickle_path)
        similar_texts = find_similar_texts(user_query, lines, embeddings)
        print('Found similar number of items:', len(similar_texts))
        print('Found similar number of items:', similar_texts)

        # Push each similar text into the Redis list
        for text, score in similar_texts:
            print(f"Score: {score:.4f}, Text: {text}")
            print('Pushing ', text, ' to cache with key ', conversation_id + '-in-context-menu-items')
            # Ensure we're inserting a string representation of the text
            store.lpush(conversation_id + '-in-context-menu-items', text)

        # Retrieve all items from the Redis list
        in_context_menu_items = store.lrange(conversation_id + '-in-context-menu-items', 0, -1)
        print('Pulling items from cache ', conversation_id + '-in-context-menu-items ', in_context_menu_items)

        in_context_menu_items_str = '\n'.join([item for item in in_context_menu_items])

        print('Replacing {context} in prompt with ', in_context_menu_items_str)
        print('Replacing {question} in prompt with ', user_query)

        data = data.replace("{context}", in_context_menu_items_str)
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
