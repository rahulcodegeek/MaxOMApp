import stripe
from twilio.rest import Client
from order import add_order_in_db, order_query, gettaxrate
from database import restaurants_bot

# --- Setting Stripe API key for payment purpose
stripe.api_key = "sk_test_51NsJOgI6hLoGbkjMETqmm36XjI2SK1ajKFFEc94nHxosCQBT6VUSCcrXHbV7ApTsneUb1gGfC1Z6a5uzGX6cKEs900J5wwp41o"
app_url = "http://voicebotapi.eu-west-1.elasticbeanstalk.com/"
# app_url = "https://fbe5-39-63-29-195.ngrok-free.app/"


# --- Create Checkout Session is a function to create a Stripe
# --- Checkout session and return that session
# --- using bill id, bill amount, order id and restaurant bot id
def create_checkout_session(bill_id, bill_amount, order_id, bot_id):
    try:
        # --> Creating a stripe session to get the url for payment process
        stripe_session = stripe.checkout.Session.create(
            payment_method_types=['card'],    # --> Method type for payment
            line_items=[{
                'price_data': {
                    'currency': 'usd',    # --> Currency type for payment
                    'product_data': {
                        'name': 'Food Order Payment',    # --> Name of payment
                    },
                    'unit_amount': int(bill_amount * 100), # --> Total amount
                },
                'quantity': 1,
            }],
            mode='payment',
            # --> Goes to this successfull url to send order to clover once payment is completed
            success_url=f'{app_url}payment_successful?bill_id={bill_id}&bill_amount={bill_amount}&order_id={order_id}&bot_id={bot_id}',
            # --> Goes to below failed url in case of unsuccessfull payment
            cancel_url=f'{app_url}payment_failed?bill_id={bill_id}&bill_amount={bill_amount}',
            client_reference_id=bill_id,
        )
    except Exception as e:
        print(e)
        return "Sorry for inconvenience. There is an issue with the clover url", 505

    return stripe_session, 200


# --- Get Checkout URL is a function to create a Stripe Checkout session and return that session 
def get_checkout_url(session_id):
    # ---> Retrieving the session using the session id
    stripe_session = stripe.checkout.Session.retrieve(session_id)
    # ---> Getting url from the session and return it
    checkout_url = stripe_session.url
    return checkout_url


# --- A function to extract information from a order json and return it in a simple message 
def Get_order_information(order_id, data, taxrate):
    # ---> Extracting order and total price information
    order_items = data['order']
    total_price = data['total_price']

    # ---> Formatting information into a message
    message = f"Order Details:\nOrder Id: {order_id}\n"
    for item in order_items:
        message += f"Item: {item['item_name']}\n"
        message += f"Price: {item['item_price']}\n"
        message += f"Quantity: {item['item_quantity']}\n"
        message += f"Item ID: {item['item_id']}\n"
        if item["additional_modifier_name"] != "":
            message += f"{item['additional_modifier_name']}: {item['modifier_type_name']}\n"
        message += "\n"

    numeric_price = ''.join(c for c in total_price if c.isdigit() or c == '.')

    sales_tax = (float(taxrate) / float(100)) * float(numeric_price)
    total_price_with_tax = float(numeric_price) + float(sales_tax)
    message += f"Total Price Including Sales Tax: ${round(total_price_with_tax, 2)}"

    # ---> Returning message and total payment
    return message, round(total_price_with_tax, 2)


# --- A function to create a stripe url and send the order message alone with the stripe url to customer phone number
def send_stripe_payment_message(session_id, from_number, to_number, history):
    order, status_code = order_query(history)
    tax_rate = gettaxrate(from_number)
    tax_rate_percentage = tax_rate/100000
    # ---> Adding the customer order in the data base using below function of order package. It return bot id and order id
    order_id, bot_id = add_order_in_db(from_number, session_id, order['customer_name'], to_number, order, order['total_price'])
    # ---> Getting order information along with total price
    order_data, total_price = Get_order_information(order_id, order, tax_rate_percentage)

    # ---> Creating stripe session and getting stripe session url
    stripe_session, status_code = create_checkout_session(session_id, total_price, order_id, bot_id)
    checkouturl = get_checkout_url(stripe_session.id)

    # ---> Adding the restaurant bot to the database using the properties read from the file if already not in the database
    restaurant_number = from_number    # ---> Getting the current phone number 
    existing_bot = restaurants_bot.query.filter(
        restaurants_bot.restaurant_number == restaurant_number
    ).first()
    
    # ---> Setting twilio account SID and Auth token to send message to user phone number
    account_sid = existing_bot.twilio_account_sid
    auth_token = existing_bot.twilio_account_auth_token
    client = Client(account_sid, auth_token)
    # ---> Message for customer
    message_body = "Dear "+order['customer_name']+"! Your Order Has Been Placed.\n\n" + order_data \
                    + "\n\nKindly Proceed With Payment Process Using The Link Below\n" + f"<{checkouturl}>"
    # --> Sending Message to customer phone number
    client.messages.create(from_=from_number,
                    to=to_number,
                    body=message_body
    )

    return None
