import stripe
from twilio.rest import Client
from order import order_query, gettaxrate
from db_persisters.orders import add_order
from db_persisters.customer import add_customer
from db_persisters.restaurants import get_restaurants
from db_persisters.payment_message import add_payment_message
from db_persisters.conversation import add_conversation, make_conversation_template
from db_persisters.restaurant_system_configuration import \
    get_restaurants_configuration
import base64
import rsa
from database import privateKey


# --- Create Checkout Session is a function to create a Stripe
# --- Checkout session and return that session
# --- using bill id, bill amount, order id and restaurant bot id
def create_checkout_session(bill_id, bill_amount, order_id, res_id):
    # --- Setting Stripe API key for payment purpose
    res_config = get_restaurants_configuration(res_id)
    stripe.open_ai_api_key = rsa.decrypt(
        base64.b64decode(res_config.payment_api_key),
        privateKey
    ).decode()

    #TODO: Change this per deployment or fetch this dynamically
    app_url = "http://maxom.us-west-2.elasticbeanstalk.com/"
    # app_url = "https://8b9c-39-63-31-137.ngrok-free.app/"
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
                    'unit_amount': int(bill_amount * 100),  # --> Total amount
                },
                'quantity': 1,
            }],
            mode='payment',
            # --> Goes to this successful url to send order to
            # --> clover once payment is completed
            success_url=f'{app_url}payment_successful?bill_id={bill_id}\
&bill_amount={bill_amount}&order_id={order_id}&res_id={res_id}',
            # --> Goes to below failed url in case of unsuccessful payment
            cancel_url=f'{app_url}payment_failed?bill_id={bill_id}\
&bill_amount={bill_amount}&order_id={order_id}',
            client_reference_id=bill_id,
        )

        print('stripe_session', dir(stripe_session))
    except Exception as e:
        print(e)
        return "Sorry for inconvenience nine. There is an issue \
with the clover url", 505

    return stripe_session, 200


# --- Get Checkout URL is a function to create a Stripe Checkout session
# --- and return that session
def get_checkout_url(session_id):
    # ---> Retrieving the session using the session id
    stripe_session = stripe.checkout.Session.retrieve(session_id)
    # ---> Getting url from the session and return it
    checkout_url = stripe_session.url
    return checkout_url


# --- A function to extract information from a order json and
# --- return it in a simple message
def get_order_information(order_id, data, price):
    # ---> Extracting order and total price information
    order_items = data['order']
    # ---> Formatting information into a message
    message = f"Order Details:\nOrder Id: {order_id}\n"
    for item in order_items:
        message += f"Item: {item['item_name']}\n"
        message += f"Price: {item['item_price']}\n"
        message += f"Quantity: {item['item_quantity']}\n"
        message += f"Item ID: {item['item_id']}\n"
        if item["additional_modifier_name"] != "":
            message += f"{item['additional_modifier_name']}: \
{item['modifier_type_name']}\n"
        message += "\n"

    message += f"Total Price Including Sales Tax: \
${round(price, 2)}"

    # ---> Returning message and total payment
    return message, round(price, 2)


# --- A function to create a stripe url and send the order
# --- message alone with the stripe url to customer phone number
def send_stripe_payment_message(session_id, from_number, to_number, history):
    try:
        conversation_template = make_conversation_template(history)
        order, status_code = order_query(history)
        tax_rate = gettaxrate(from_number)
        tax_rate_percentage = tax_rate/100000
        # ---> Calculating tax on order
        price = order['total_price']
        nm_price = ''.join(c for c in price if c.isdigit() or c == '.')
        sales_tax = (float(tax_rate_percentage) / float(100)) * float(nm_price)
        total_price_with_tax = float(nm_price) + float(sales_tax)
        total_price_with_tax = round(total_price_with_tax, 2)
        # ---> Getting restaurant id
        res = get_restaurants(from_number)
        # ---> Adding the customer in the database
        customer_id = add_customer(res.id, order['customer_name'], to_number)
        # ---> Adding the customer order in the database using below
        # ---> function of order package. It returns bot id and order id
        order['total_price_with_tax'] = total_price_with_tax
        order_id = add_order(
            res.id, customer_id,
            order, order['total_price'],
            sales_tax,
            total_price_with_tax
        )
        # ---> Adding the customer in the database
        customer_id = add_conversation(
            res.id, customer_id, conversation_template
        )
        # ---> Getting order information along with total price
        order_data, total_price = get_order_information(
            order_id, order, total_price_with_tax
        )

        # ---> Creating stripe session and getting stripe session url
        stripe_session, status_code = create_checkout_session(
            session_id, total_price, order_id, res.id
        )

        print('stripe_session', dir(stripe_session))
        checkout_url = get_checkout_url(stripe_session.id)
        print('checkout_url ', checkout_url)
        # ---> Getting restaurant configurations for twilio
        res_config = get_restaurants_configuration(res.id)
        account_sid = rsa.decrypt(
            base64.b64decode(res_config.voice_api_account_sid), privateKey
        ).decode()
        auth_token = rsa.decrypt(
            base64.b64decode(res_config.voice_api_account_auth_token),
            privateKey
        ).decode()

        client = Client(account_sid, auth_token)
        # ---> Message for customer
        message_body = "Dear "+order['customer_name']+"! Your Order Has Been \
    Placed.\n\n" + order_data + "\n\nKindly Proceed With Payment \
    Process Using The Link Below\n" + f"<{checkout_url}>"
        # --> Sending Message to customer phone number
        client.messages.create(
            from_=from_number,
            to=to_number,
            body=message_body
        )
        add_payment_message(
            res.id, customer_id, message_body, "Successfully Delivered"
        )
    except Exception as e:
        print('Exception', e)
        message_body = 'Error in sending message to Stripe'
        add_payment_message(res.id, customer_id, message_body, str(e))
    return None
