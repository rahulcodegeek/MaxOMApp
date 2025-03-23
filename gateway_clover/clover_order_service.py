import base64
import json

import requests
import rsa

from call_status import CallStatus
from database import privateKey
from db_persisters.call_logs import add_call_log
from db_persisters.customer import get_customer_by_id
from db_persisters.orders import get_order_by_order_id
from db_persisters.pos_order import add_pos_order
from db_persisters.restaurant_system_configuration import get_restaurants_configuration
from db_persisters.restaurants import get_restaurant

# --- A function to get the tax raye from the clover
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
def create_order(baseURL, headers, customer_name, customer_entry, is_test_mode, instructions):
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
        "note": note + "\nCustomer Name: " + customer_name + "\nCustomer Phone: " + customer_entry.customer_phone_number + "\nSpecial Instructions by Customer: " + instructions
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
            "id": item['additional_modifier_id']
        }
    }
    print("**Adding modifier", item['additional_modifier_id'], ' to lineId', inlineId, ' of the order ',  order['id'])
    r = requests.post(url, data=json.dumps(data), headers=headers)
    if r.status_code == 200:
        print("**Added modifier", item['additional_modifier_id'], ' to lineId', inlineId, ' of the order ', order['id'])
        return r.json()
    else:
        print("**Error in adding modifier", item['additional_modifier_id'], ' to lineId', inlineId, ' of the order ', order['id'])
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
        instructions = json_order['special_instructions']
        # Example if same phone numer is being used by husband and wife to place the order..
        order = create_order(baseURL, headers, customer_name, customer_entry, is_test_mode, instructions)
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
                if item['additional_modifier_id'] != '':
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
