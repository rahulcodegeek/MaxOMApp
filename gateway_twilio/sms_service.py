import base64
import json

import rsa
from twilio.rest import Client

from call_status import CallStatus
from database import privateKey
from db_persisters.call_logs import add_call_log
from db_persisters.customer import get_customer_by_id
from db_persisters.orders import get_order_by_order_id
from db_persisters.restaurant_system_configuration import get_restaurants_configuration
from db_persisters.restaurants import get_restaurant_by_id


def send_order_sms_confirmation(order_id, res_id, conversation_id):
    try:
        restaurant = get_restaurant_by_id(res_id)
        # ---> Getting restaurant bot information from database using restaurant bot id
        res_config = get_restaurants_configuration(res_id)
        # ---> Getting order information from database using order id
        current_order = get_order_by_order_id(order_id)
        customer_entry = get_customer_by_id(current_order.customer_id)

        # ---> Converting string order to json
        json_order = json.loads(current_order.order_details)


        # Example if same phone numer is being used by husband and wife to place the order.
        data_items = json_order['order']

        # Initialize an empty list to hold the output strings
        order_message_strings = []

        # Iterate through the order items
        for item in data_items:
            # Extract item name and quantity
            item_name = item['item_name']
            item_quantity = item['item_quantity']

            # Initialize the string with item name and quantity
            item_string = f"{item_name}, Quantity: {item_quantity}"

            # Check if additional_modifier_name is not blank
            if item['additional_modifier_name']:
                additional_modifier = item['additional_modifier_name']
                item_string += f", {additional_modifier}"

            # Add the constructed string to the list
            order_message_strings.append(item_string)

        # Join the list of order message strings to form the final order gateway_twilio message
        final_order_message_body = "\n".join(order_message_strings)

        print('Preliminary message body for SMS ', final_order_message_body)

        account_sid = rsa.decrypt(
            base64.b64decode(res_config.voice_api_account_sid), privateKey
        ).decode()
        auth_token = rsa.decrypt(
            base64.b64decode(res_config.voice_api_account_auth_token),
            privateKey
        ).decode()
        # ---> Create order and grab order ID
        customer_name = json_order['customer_name']  # This customer name could be sometimes different from the one stored in the customer table

        client = Client(account_sid, auth_token)
        # ---> Message for customer
        final_order_message_body = "Order Confirmation from " + restaurant.name + "\nDear " + customer_name + "! Your Order Has Been \
            Placed.\n\n" + final_order_message_body
        # --> Sending Message to customer phone number
        print('Final message body for SMS ', final_order_message_body)
        client.messages.create(
            from_='+12132618687',
            to=customer_entry.customer_phone_number,
            body=final_order_message_body
        )
        add_call_log(conversation_id, res_id, CallStatus.SMS_ATTEMPTED, final_order_message_body)
        print("SMS attempted for the customer ", customer_name)
    except Exception as e:
        print('Error in sending SMS ', str(e))
        add_call_log(conversation_id, res_id, CallStatus.SMS_ERROR, str(e))
    return "Success"
