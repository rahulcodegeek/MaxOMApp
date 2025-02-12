import pytz
from datetime import datetime, time, timedelta
import requests
import base64
import json
import rsa
from db_persisters.restaurant_system_configuration import \
    get_restaurants_configuration
from db_persisters.restaurants import get_restaurant_by_id
from database import privateKey


def is_restaurant_open(restaurant_id):
    restaurant = get_restaurant_by_id(restaurant_id)
    information_json = restaurant.information_json
    information_json = json.loads(information_json)

    restaurant_timezone = information_json['restaurant_timezone']
    phone_orders_time_gap_in_minutes_after_start_time = information_json['phone_orders_time_gap_in_minutes_after_start_time']
    phone_orders_time_gap_in_minutes_before_end_time = information_json['phone_orders_time_gap_in_minutes_before_end_time']

    fetched_opening_hours, status = fetch_opening_hours_from_pos(restaurant.id)

    if status == 200:
        fetched_opening_hours = fetched_opening_hours.json()

    fetched_opening_hours = fetched_opening_hours.get('elements')[0]
    print(fetched_opening_hours)
    # Check if the business is open
    result = is_open_to_take_phone_orders(fetched_opening_hours, restaurant_timezone,
                                          phone_orders_time_gap_in_minutes_after_start_time,
                                          phone_orders_time_gap_in_minutes_before_end_time)
    print("Is the restaurant open to take phone order?", result)
    return result

#def is_restaurant_open(restaurant_id):
#    return True

def fetch_opening_hours_from_pos(restaurant_id):
    try:
        # ---> First read the properties using the restaurant id
        restaurant_config = get_restaurants_configuration(restaurant_id)
        # ---> Getting clover url and authentication token
        # ---> from properties of the restaurant
        url = rsa.decrypt(
            base64.b64decode(restaurant_config.pos_url), privateKey
        ).decode()
        auth = rsa.decrypt(
            base64.b64decode(restaurant_config.pos_authorization_header),
            privateKey
        ).decode()
        headers = {"authorization": f'Bearer {auth}'}
        # ---> Calling the clover url and returns it
        response = requests.get(url + 'opening_hours', headers=headers)
        return response, 200
    except Exception as e:
        # ---> If no url found or any error occurs
        print("Error in Url", e)
        return "Sorry for inconvenience. I am connecting you to the \
actual agent wait for some moments", 503

def is_open_to_take_phone_orders(fetched_opening_hours,
                                 timezone_str,
                                 phone_orders_time_gap_in_minutes_after_start_time,
                                 phone_orders_time_gap_in_minutes_before_end_time):
    timezone = pytz.timezone(timezone_str)
    current_time = datetime.now(timezone)
    current_day = current_time.strftime("%A").lower()
    current_time = current_time.time()

    for day, schedule in fetched_opening_hours.items():
        if current_day in day:
            elements = schedule.get("elements", [])
            for slot in elements:
                # this is some configration that is allowed in Clover to configure the hour as the value 24, which is invalid according to many softwares, so, adjustment is made to accommodate it
                if slot['start'] == 2400:
                    slot['start'] = 2359
                if slot['end'] == 2400:
                    slot['end'] = 2359
                open_datetime = datetime.combine(datetime.today(), time(hour=slot['start'] // 100, minute=slot['start'] % 100)) + timedelta(minutes=phone_orders_time_gap_in_minutes_after_start_time)
                close_datetime = datetime.combine(datetime.today(), time(hour=slot['end'] // 100, minute=slot['end'] % 100)) - timedelta(minutes=phone_orders_time_gap_in_minutes_before_end_time)
                if open_datetime.time() <= current_time <= close_datetime.time():
                    return True
    return False

# Define the timezone



