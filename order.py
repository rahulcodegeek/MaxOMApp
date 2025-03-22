import json
import requests
from db_persisters.orders import get_order_by_order_id
from openai import ChatCompletion, OpenAIError
from db_persisters.restaurant_system_configuration import \
    get_restaurants_configuration
from db_persisters.restaurants import get_restaurant
from db_persisters.customer import get_customer_by_id
import base64
import rsa
from database import privateKey



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
                        "additional_modifier_name": "addtional modifier name (name of the specific additional modifier if selected item have from the context)"
                        "additional_modifier_id": "addtional modifier id (id of the specific additional modifier if selected item have from the context)"
                        "modifier_type_name": "modifier type name (name of the specific modifier type user selected if selected item have modifier from the context)"
                        "modifier_type_id": "modifier type id (id of the specific modifier type user selected if selected item have modifier from the context)"
                        }
                    ],
            "customer_name": "customer name",
            
            "total_price" : "total price of order"
    }
    </JSON OBJECT>
    Don't skip this format and any of the tags provide along with the brackets. You have to strickly follow the format. Use the current order information to return the order.
    """
    # ---> Calling conversation function of chat_gpt_service module
    user_query = Order_Query + ' (refer to context)'

    # --> Getting previous conversation
    history.append({"role": "user", "content": user_query})
    # --> Calling ChatGpt Api and return its reply with status 200 if successful other wise return with status 502
    try:
        chat = ChatCompletion.create(model="gpt-4o-mini-2024-07-18", messages=history)
        reply = chat.choices[0].message.content
        status = 200
    except OpenAIError as e:
        print(e)
        reply = "Sorry for inconvenience eight. I am connecting you to the actual agent wait for some moments."
        status = 502
    # ---> Extracting the order in json type 
    order = extract_order_json(reply)
    return order, status


# --- A function that extract the order json object from the string 
def extract_order_json(input_string):
    # ---> Extracing the Json from our order repeat string
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


def gettaxrate(restaurant_number):
    res = get_restaurant(restaurant_number)
    res_config = get_restaurants_configuration(res.id)
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
    #TODO - Y4JM6PA9ZM58W to be replaced from the dynamic configuration
    url = baseURL + "tax_rates/Y4JM6PA9ZM58W"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        res = json.loads(response.text)
        return res['rate']
    else:
        print(response)


# --- A function to create an order on the clover
def createOrder(baseURL, headers, customer_name):
    url = baseURL + 'orders'
    payload = {
        "paymentState": "PAID",
        "customers": [{"firstName": customer_name}]
    }
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(r)
        raise Exception("Base Order failed to be created in POS")



# --- A function to an item in the order that is already created
def addLineItem(order, item, myitem, baseURL, headers):
    url = baseURL+'orders/'+order['id']+'/line_items'
    data = {
            'item': {'id': myitem['id']},
            "modifications": [
                {
                    "modifier": {
                        "available": "true",
                        "price": "0",
                        "modifierGroup": {
                            "id": item['additional_modifier_id']
                        },
                        "id": item['modifier_type_id'],
                        "name": item['modifier_type_name']
                    }
                }
            ]
    }
    r = requests.post(url, data=json.dumps(data), headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(r.json())


# --- A function to set the state to open so it will be viewed on clover dashboard
def openOrder(order, baseURL, headers):
    url = baseURL + 'orders/' + order['id']
    data = {'state': 'open'}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(r)


# --- A function to createPayment or Order
def createPayment(order, baseURL, headers, amount):
    url = baseURL + 'orders/' + order['id'] + "/payments"
    #TODO - Replace XVEZXVCJ38V8E to fetch dynamically
    payload = {
        "order": { "id": order['id'] },
        "tender": { "id": "XVEZXVCJ38V8E" },
        "offline": "false",
        "transactionSettings": {
            "disableCashBack": "false",
            "cloverShouldHandleReceipts": "true",
            "forcePinEntryOnSwipe": "false",
            "disableRestartTransactionOnFailure": "false",
            "allowOfflinePayment": "false",
            "approveOfflinePaymentWithoutPrompt": "false",
            "forceOfflinePayment": "false",
            "disableReceiptSelection": "false",
            "disableDuplicateCheck": "false",
            "autoAcceptPaymentConfirmations": "false",
            "autoAcceptSignature": "false",
            "returnResultOnTransactionComplete": "false",
            "disableCreditSurcharge": "false"
        },
        "transactionInfo": {
            "isTokenBasedTx": "false",
            "emergencyFlag": "false"
        },
        "amount": amount
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(r)


# --- A function to get the order using the order id to confirm it is successfully placed
def getOrder(order, baseURL, headers):
    url = baseURL + 'orders/' + order['id'] + '?expand=payments'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(r)


# --- A function to retrieve order from the database and add it to clover once payment is successful
def send_order_to_clover(order_id, res_id):
     # ---> Getting restaurant bot information from database using restaurant bot id
    res_config = get_restaurants_configuration(res_id)
    # ---> Getting order information from database using order id
    current_order = get_order_by_order_id(order_id)
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
    # ---> Create order and grab order ID
    customer = get_customer_by_id(current_order.customer_id)
    order = createOrder(baseURL, headers, customer.customer_name)
    data_items = json_order['order']
    for item in data_items:
        for i in range(int(item['item_quantity'])):
            # ---> First getting the item from the clover which is in
            # ---> current order
            myItem = requests.get(
                baseURL + 'items/' + item['item_id'],
                headers=headers
            ).json()
            # ---> Then Add it in the order which is just created
            addLineItem(order, item, myItem, baseURL, headers)
    # ---> Open the order so its visible on other devices
    openOrder(order, baseURL, headers)
    createPayment(
        order, baseURL, headers,
        int(float(current_order.total_price)*100)
    )
    # ---> Getting Order
    print(getOrder(order, baseURL, headers))

    return "Success"
