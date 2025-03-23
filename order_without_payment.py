import json

from openai import OpenAI

from db_persisters.orders import add_order
from db_persisters.customer import add_customer
from db_persisters.restaurants import get_restaurant
from db_persisters.call_logs import add_call_log
from db_persisters.conversation import add_conversation, make_conversation_template

from call_status import CallStatus

from gateway_clover.clover_order_service import get_tax_rate, send_order_to_pos
from langchain_service_1 import store
import os

#open_ai_api_key = 'sk-proj-xH1Y3zh_goAC5fmq6GTeOlGuKGMnStIkHEaeZhUl'+os.environ.get('OPEN_AI_API_KEY') # Test

open_ai_api_key = 'sk-proj-bIhEAlBd5kpLGTysb8fVzrAHwTZFSsn8JAAXeIp5'+os.environ.get('OPEN_AI_API_KEY') # Prod

# --- A function that converts the current order into the json format using ChatGpt
def order_query(history):
    current_history = history
    # ---> Prompt for the ChatGpt to return the current order in json format given below in the prompt
    Order_Query = """"Return the current order in the below format and don't add anything else other than the given format
    <JSON OBJECT>
    {
            "order":[
                        {
                        "item_name" : 'name (this item is from the provided menu)',
                        "item_price" : 'price (price of the item from the provided menu)',
                        "item_id" : 'id (id of the specific item from the context)',
                        "item_quantity" : 'quantity',
                        "modifier_type_name": "modifier type name (name of the specific modifier type user selected if selected item has additional modifier from the context)",
                        "modifier_type_id": "modifier type id (id of the specific modifier type user selected if selected item has additional modifier from the context)",
                        "additional_modifier_name": "additional modifier name (name of the specific additional modifier if selected has additional modifier from the context)",
                        "additional_modifier_id": "additional modifier id (id of the specific additional modifier if selected item has additional modifier from the context)"
                        }
                    ],
            "customer_name": "customer name",
            "special_instructions": "special instructions if mentioned by the user otherwise empty string",
            "total_price" : "total price of order"
    }
    </JSON OBJECT>
    Don't skip this format and any of the tags provide along with the brackets. You have to strictly follow the format. Use the current order information to return the order.
    """
    # ---> Calling conversation function of chat_gpt_service module
    user_query = Order_Query + ' (refer to context)'

    # --> Getting previous conversation
    history.append({"role": "user", "content": user_query})
    # --> Calling ChatGpt Api and return its reply with status 200 if successful otherwise return with status 502
    try:
        client = OpenAI(api_key=open_ai_api_key)

        chat = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=history
        )
        reply = chat.choices[0].message.content
        status = 200
    except Exception as e:
        print(e)
        reply = "Sorry for inconvenience eight. I am connecting you to the actual agent wait for some moments."
        status = 502
    # ---> Extracting the order in json type
    order = extract_order_json(reply, current_history)
    return order, status


# --- A function that extract the order json object from the string
def extract_order_json(input_string, current_history):
    # ---> Extracting the Json from our order repeat string
    order_string = input_string
    # ---> Find the start and end indices of the JSON object within the string
    while True:
        try:
            start_index = order_string.index("{")
            end_index = order_string.rindex("}") + 1
            # ---> Extract the JSON object from the string
            order_json_string = order_string[start_index:end_index]
            # ---> Convert the JSON string to a JSON object
            order_json_1 = json.loads(order_json_string)
            break
        except:
            # ---> If any error occurs get the order again from the ChatGpt
            order_string = order_query(current_history)
    return order_json_1


# --- A function to retrieve order from the database and add it to clover once payment is successful
def persist_and_send_order_to_pos(history, from_number, to_number, is_test_mode, conversation_id):
    order_id = None
    try:
        res = get_restaurant(to_number)
        restaurant_information = json.loads(res.information_json)
        prompt_file = open('./resources/langchain_prompt.txt')
        #pickle_path = "./resources/Retrievers/" + str(res.id) + "_Retriever" + ".pkl"
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

        in_context_menu_items = store.lrange(conversation_id + '-in-context-menu-items', 0, -1)
        print('Pulling items from cache ', conversation_id + '-in-context-menu-items ', in_context_menu_items)

        in_context_menu_items_str = '\n'.join([item.decode('utf-8') for item in in_context_menu_items])
        print('Replacing {context} in prompt with ', in_context_menu_items_str)

        data = data.replace("{context}", in_context_menu_items_str)
        history.insert(0, {"role": "assistant", "content": data})

        print('persist_and_send_order_to_pos.....')
        conversation_template = make_conversation_template(history)
        print('conversation_template ', conversation_template)
        order, status_code = order_query(history)
        print('order ', order)
        tax_rate = get_tax_rate(to_number)
        print('tax_rate ', tax_rate)
        tax_rate_percentage = tax_rate / 100000
        # ---> Calculating tax on order
        price = order['total_price']
        print('price of the order ', price)
        nm_price = ''.join(c for c in price if c.isdigit() or c == '.')
        print('nm_price ', nm_price)

        sales_tax = (float(tax_rate_percentage) / float(100)) * float(nm_price)
        print('sales_tax ', sales_tax)

        total_price_with_tax = float(nm_price) + float(sales_tax)
        print('total_price_with_tax ', total_price_with_tax)

        total_price_with_tax = round(total_price_with_tax, 2)
        print('total_price_with_tax rounded off ', total_price_with_tax)

        # ---> Adding the customer in the database
        customer_id = add_customer(res.id, order['customer_name'], from_number)
        print('added the customer ', customer_id)

        # ---> Adding the customer order in the database using below
        # ---> function of order package. It returns bot id and order id
        order['total_price_with_tax'] = total_price_with_tax
        order_id = add_order(
            res.id, customer_id,
            conversation_id,
            order, order['total_price'],
            sales_tax,
            total_price_with_tax
        )
        print('added the order ', order_id)

        # ---> Adding the conversation in the database
        persisted_conversation_id = add_conversation(res.id, customer_id, conversation_id, conversation_template)
        print('added the conversation_ ', persisted_conversation_id)

        send_order_to_pos(order_id, res.id, is_test_mode, conversation_id)
        print('send_order_to_pos')

        #send_order_sms_confirmation(order_id, res.id, conversation_id)
        #print('send_order_sms_confirmation')

    except Exception as e:
        print('Exception ERROR', e)
        add_call_log(conversation_id, res.id, CallStatus.ENDED_IN_ERROR, str(e))
        message_body = 'Error in sending order to POS'
    return order_id
