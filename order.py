import json
import requests
from database import db, orders, restaurants_bot
import openai
from openai import ChatCompletion, OpenAIError

# Initialize OpenAI
openai.api_key_path = 'resources/chatgpt_api_key'
openai.api_endpoint = 'https://api.openai.com/v1/chat/completions'


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
    # --> Calling ChatGpt Api and return its reply with status 200 if succesfull other wise return with status 502
    try:
        chat = ChatCompletion.create(model="gpt-4-1106-preview", messages=history)
        reply = chat.choices[0].message.content
        status = 200
    except OpenAIError as e:
        print(e)
        reply = "Sorry for inconvenience. I am connecting you to the actual agent wait for some moments."
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
    bot = restaurants_bot.query.filter_by(restaurant_number = restaurant_number).first()
    baseURL = bot.clover_url
    headers = {'Content-type': 'application/json', 'authorization': bot.clover_authorization_header}
    url = baseURL + "tax_rates/Y4JM6PA9ZM58W"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        res = json.loads(response.text)
        return res['rate']
    else:
        print(response)


# --- Function to add the order in the database
def add_order_in_db(restaurant_number, customer_session_id, customer_name,
                    customer_phone_number, customer_order, customer_total_order_price):
        # ---> Convert order json into string
        order_string = json.dumps(customer_order)
        # ---> Initializing a new order
        new_order = orders(restaurant_number, customer_session_id, customer_name,
                           customer_phone_number, order_string, customer_total_order_price)
        
        # ---> Adding in the database
        db.session.add(new_order)
        db.session.commit()
        # ---> Getting order id using customer session id and restaurant bot using restaurant phone number
        order_id = orders.query.filter_by(customer_session_id = customer_session_id).first().id
        bot_id = restaurants_bot.query.filter_by(restaurant_number = restaurant_number).first().id

        return order_id, bot_id


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


# --- A function to get the order using the order id to confirm it is successufull palced
def getOrder(order, baseURL, headers):
    url = baseURL + 'orders/' + order['id'] + '?expand=payments'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        print(r)


# --- A function to retrieve order from the database and add it to clover once payment is successfull 
def Send_Order_to_clover(order_id, bot_id):

    # ---> Getting restaurant bot information from database using restaurant bot id
    restaurant_bot = restaurants_bot.query.filter_by(id = bot_id).first()
    # ---> Getting order information from database using order id
    current_order = orders.query.filter_by(id = order_id).first()
    # ---> Converting string order to json
    print((current_order))
    json_order = json.loads(current_order.customer_order)
    # ---> Getting Clover information from the restaurant bot we extracted
    baseURL = restaurant_bot.clover_url
    headers = {'Content-type': 'application/json', 'authorization': restaurant_bot.clover_authorization_header}

    # ---> Create order and grab order ID
    order = createOrder(baseURL, headers, current_order.customer_name)
    data_items = json_order['order']
    for item in data_items:
        for i in range(int(item['item_quantity'])):
            # ---> First getting the item from the clover which is in current order
            myItem = requests.get(baseURL + 'items/' + item['item_id'], headers=headers).json()
            # ---> Then Add it in the order which is just created
            addLineItem(order, item, myItem, baseURL, headers)
    # ---> Open the order so its visible on other devices
    openOrder(order, baseURL, headers)
    tax_rate = gettaxrate(restaurant_bot.restaurant_number)
    tax_rate_percentage = tax_rate/100000
    order_amount = current_order.customer_total_order_price
    numeric_price = ''.join(c for c in order_amount if c.isdigit() or c == '.')
    sales_tax = (float(tax_rate_percentage) / float(100)) * float(numeric_price)
    total_price_with_tax = float(numeric_price) + float(sales_tax)
    final_payment = round(total_price_with_tax, 2)
    createPayment(order, baseURL, headers, int(final_payment*100))
    # ---> Getting Order
    print(getOrder(order, baseURL, headers))

    return "Success"

