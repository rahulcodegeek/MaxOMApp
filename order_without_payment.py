import json
import requests

from openai import OpenAI

from db_persisters.restaurant_system_configuration import \
    get_restaurants_configuration
from db_persisters.customer import get_customer_by_id
from db_persisters.orders import add_order, get_order_by_order_id
from db_persisters.customer import add_customer
from db_persisters.restaurants import get_restaurant
from db_persisters.call_logs import add_call_log
from db_persisters.pos_order import add_pos_order
from db_persisters.conversation import add_conversation, make_conversation_template

from call_status import CallStatus

import base64
import rsa
from database import privateKey
from langchain_service_1 import store
import os

open_ai_api_key = os.environ.get('OPEN_AI_API_KEY')
# --- A function that converts the current order into the json format using ChatGpt
def order_query(history):
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
                        "additional_modifier_name": "additional modifier name (name of the specific additional modifier if selected has additional modifier from the context)"
                        "additional_modifier_id": "additional modifier id (id of the specific additional modifier if selected item has additional modifier from the context)"
                        "modifier_type_name": "modifier type name (name of the specific modifier type user selected if selected item has additional modifier from the context)"
                        "modifier_type_id": "modifier type id (id of the specific modifier type user selected if selected item has additional modifier from the context)"
                        }
                    ],
            "customer_name": "customer name",

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
            model="gpt-4-0125-preview",
            messages=history
        )
        reply = chat.choices[0].message.content
        status = 200
    except Exception as e:
        print(e)
        reply = "Sorry for inconvenience eight. I am connecting you to the actual agent wait for some moments."
        status = 502
    # ---> Extracting the order in json type
    order = extract_order_json(reply)
    return order, status


# --- A function that extract the order json object from the string
def extract_order_json(input_string):
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
            order_string = order_query()
    return order_json_1


def get_tax_rate(restaurant_number):
    res = get_restaurant(restaurant_number)
    res_config = get_restaurants_configuration(res.id)
    baseURL = rsa.decrypt(
        base64.b64decode(res_config.pos_url), privateKey
    ).decode()
    auth = rsa.decrypt(
        base64.b64decode(res_config.pos_authorization_header),
        privateKey
    ).decode()
    pos_tax_rate_code = rsa.decrypt(
        base64.b64decode(res_config.pos_tax_rate_code),
        privateKey
    ).decode()
    headers = {
        'Content-type': 'application/json',
        "authorization": f'Bearer {auth}'
    }
    url = baseURL + "tax_rates/" + pos_tax_rate_code
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        res = json.loads(response.text)
        return res['rate']
    else:
        print(response.json())


# --- A function to create an order on the clover
def create_order(baseURL, headers, customer_name, customer_entry, is_test_mode):
    url = baseURL + 'orders'
    note = ''
    testMode = 'false'

    is_test_mode_to_lower_case = is_test_mode.lower()

    if ("true" in is_test_mode_to_lower_case):
        note = 'A Test Order'
        testMode = 'true'
    else:
        note = 'MaxOM Order'
        testMode = 'false'

    # TODO - Change this when deploying, enhancement to do these configurations at one place
    payload = {
        "paymentState": "OPEN",
        "note": note + "\nCustomer Name: " + customer_name + "\nCustomer Phone: " + customer_entry.customer_phone_number
        # ,testMode
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        print('Order sent to Clover successfully', r.json())
        return r.json()
    else:
        raise Exception("Base Order failed to be created in POS")


# --- A function to an item in the order that is already created
def add_line_item(order, item, myitem, baseURL, headers):
    url = baseURL + 'orders/' + order['id'] + '/line_items'
    data = {
        'item': {'id': myitem['id']}
    }
    r = requests.post(url, data=json.dumps(data), headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print("Add line item Error")
        print(r.json())


# --- A function to an item in the order that is already created
def add_modifier_in_line_item(order, item, inlineId, baseURL, headers):
    url = baseURL + 'orders/' + order['id'] + '/line_items/' + inlineId + "/modifications"
    data = {
        "modifier": {
            "id": item['modifier_type_id']
        }
    }
    print("**Adding modifier", item['modifier_type_id'], ' to lineId', inlineId, ' of the order ',  order['id'])
    r = requests.post(url, data=json.dumps(data), headers=headers)
    if r.status_code == 200:
        print("**Added modifier", item['modifier_type_id'], ' to lineId', inlineId, ' of the order ', order['id'])
        return r.json()
    else:
        print("**Error in adding modifier", item['modifier_type_id'], ' to lineId', inlineId, ' of the order ', order['id'])
        print(r.json())


# --- A function to print event
def print_event(clover_order_id, baseURL, headers):
    url = baseURL + 'print_event'
    payload = {
        "orderRef": {
            "id": clover_order_id
        }
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        return r.status_code
    else:
        return r.status_code


# --- A function to add discount
def add_discount(clover_order_id, baseURL, headers):
    url = baseURL + 'orders/' + clover_order_id + "/discounts"
    payload = {
        "name": "Order placed through AI bot.",
        "percentage": 10
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print("Add discount error")
        print(r.json())


# --- A function to set the state to open so it will be viewed on clover dashboard
def open_order(order, baseURL, headers):
    url = baseURL + 'orders/' + order['id']
    data = {'state': 'open'}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print("Open Order Error")
        print(r.json())


# --- A function to get the order using the order id to confirm it is successfully placed
def get_order(order, baseURL, headers):
    url = baseURL + 'orders/' + order['id'] + '?expand=lineItems,lineItems.modifications,discounts'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print("Get Order Error")
        print(r.json())


# --- A function to retrieve order from the database and add it to clover once payment is successful
def persist_and_send_order_to_pos(history, from_number, to_number, is_test_mode, conversation_id):
    order_id = None
    try:
        res = get_restaurant(to_number)
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

        in_context_menu_items = store.lrange(conversation_id + '-in-context-menu-items', 0, -1)
        print('Pulling items from cache ', conversation_id + '-in-context-menu-items ', in_context_menu_items)

        in_context_menu_items_str = '\n'.join([item for item in in_context_menu_items])
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
    except Exception as e:
        print('Exception ERROR', e)
        add_call_log(conversation_id, res.id, CallStatus.ENDED_IN_ERROR, str(e))
        message_body = 'Error in sending order to POS'
    return order_id


def send_order_to_pos(order_id, res_id, is_test_mode, conversation_id):
    try:
        # ---> Getting restaurant bot information from database using restaurant bot id
        res_config = get_restaurants_configuration(res_id)
        # ---> Getting order information from database using order id
        current_order = get_order_by_order_id(order_id)
        print('Current order ', current_order)
        customer_entry = get_customer_by_id(current_order.customer_id)

        # ---> Converting string order to json
        json_order = json.loads(current_order.order_details)
        # ---> Getting Clover information from the restaurant bot we extracted
        baseURL = rsa.decrypt(
            base64.b64decode(res_config.pos_url), privateKey
        ).decode()
        auth = rsa.decrypt(
            base64.b64decode(res_config.pos_authorization_header),
            privateKey
        ).decode()
        headers = {
            'Content-type': 'application/json',
            "authorization": f'Bearer {auth}'
        }

        print('json order is ', json_order)

        # ---> Create order and grab order ID
        customer_name = json_order['customer_name']  # This customer name could be sometimes different from the one stored in the customer table
        # Example if same phone numer is being used by husband and wife to place the order..
        order = create_order(baseURL, headers, customer_name, customer_entry, is_test_mode)
        print('base order created in clover ', order)
        data_items = json_order['order']

        for item in data_items:
            for i in range(int(item['item_quantity'])):
                # ---> First getting the item from the clover which is in
                # ---> current order
                myItem = requests.get(
                    baseURL + 'items/' + item['item_id'],
                    headers=headers
                ).json()
                print()
                # ---> Then Add it in the order which is just created
                inlineItem = add_line_item(order, item, myItem, baseURL, headers)
                if item['modifier_type_id'] != '':
                    add_modifier_in_line_item(order, item, inlineItem['id'], baseURL, headers)
        # ---> Open the order so its visible on other devices
        open_order(order, baseURL, headers)
        print('order opened in clover ', order)
        # add_discount(order['id'], baseURL, headers)

        # ---> Getting Order
        clover_order = get_order(order, baseURL, headers)
        print('clover_order fetched ', clover_order)
        clover_order_id = clover_order['id']
        print("Clover Order ID is ", clover_order_id)
        print_status = print_event(clover_order_id, baseURL, headers)
        add_pos_order(order_id, clover_order_id, print_status)
        print("Added POS Order to database")
        message = 'MaxOM Order Id - ' + str(order_id) + 'POS Order Id -' + str(clover_order_id)
        add_call_log(conversation_id, res_id, CallStatus.COMPLETED_WITH_AN_ORDER, message)
    except Exception as e:
        add_call_log(conversation_id, res_id, CallStatus.ENDED_IN_ERROR, str(e))
    return "Success"
