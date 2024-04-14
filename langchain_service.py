from langchain.chat_models import ChatOpenAI
from langchain.prompts.prompt import PromptTemplate
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pickle
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from db_persisters.restaurants import get_restaurant
from db_persisters.restaurants import get_restaurant
import json
import os

open_ai_api_key = os.environ.get('OPEN_AI_API_KEY')

llm = ChatOpenAI(
    openai_api_key=open_ai_api_key,
    temperature=0,
    model="gpt-4-0125-preview"
)

embeddings = OpenAIEmbeddings(
   model="text-embedding-ada-002",
   openai_api_key=open_ai_api_key
)


def create_embeddings(restaurant_phone_number):
    res = get_restaurant(restaurant_phone_number)
    local_retriever_path = "./resources/Retrievers/" + str(res.id) + "_Retriever" + ".pkl"
    menu_file = open("./resources/"+str(res.id)+"_menu.txt")
    data = menu_file.read()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=20
    )
    all_splits = text_splitter.split_text(data)
    db_instructEmbedd = FAISS.from_texts(all_splits, embeddings)
    with open(local_retriever_path, 'wb') as file:
        pickle.dump(db_instructEmbedd, file)
    return local_retriever_path, 200


def langchain_conversation(restaurant_number, retriever_path, user_query, history):
    query = ""
    res = get_restaurant(restaurant_number)
    restaurant_information = json.loads(res.information_json)
    prompt_file = open('./resources/langchain_prompt.txt')
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

    for message in history:
        if message['role']=="user":
            query += f'USER: {message["content"]}\n'
        else:
            query += f'ASSISTANT: {message["content"]}\n'
    try:
        with open(retriever_path, 'rb') as file:
            retriever_data = pickle.load(file)
        retriever = retriever_data.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={'score_threshold': 0.60}
        )

        QA_CHAIN_PROMPT = PromptTemplate(
            input_variables=["context", "question"],
            template=data
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
            verbose=True
        )
        llm_response = qa_chain(query)
        response = llm_response['result']
        if "user:" in response.lower():
            output = response.split("USER:")
            response = output[0]
        return response, 200
    except Exception as e:
        print(f"Error: {e}")
        return "Query Response Couldn't Get", 200
