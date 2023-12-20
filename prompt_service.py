from menu_service import load_menu
from db_persisters.restaurants import get_restaurants
import json


# --- Creating a prompt for each restaurant using the restaurant information which is extracted using restaurant id
def create_prompt_data(restaurant_phone_number):
    # ---> Reading properties of the restaurant using the restaurant id
    res = get_restaurants(restaurant_phone_number)
    restaurant_information = json.loads(res.information_json)
    prompt_file = open('resources/prompt.txt')
    # ---> Loading the menu using the load_menu function of menu service module
    menu_content, status_code = load_menu(res.id)
    if status_code != 200:
        return menu_content, status_code

    # ---> Replacing all the tags that were in prompt with
    # ---> the current restaurant values.
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
    data = data.replace("{menu}", menu_content)
    prompt_file.close()
    return data, status_code
