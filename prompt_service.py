from jproperties import Properties
from menu_service import load_menu
from session_manager import get_session_attribute, set_session_attribute
from database import db, restaurants_bot


# --- Creating an prompt for the each restaurant using the restaurant information which is extracted using restuarant id
def create_prompt_data(restaurant_id):
    # ---> Reading properties of the restuarannt using the restaurant id 
    prompt_file = open('resources/prompt.txt')
    restaurant_config = Properties()
    restaurant_properties_file = "resources/"+restaurant_id+"/restaurant.properties"
    with open(restaurant_properties_file, 'rb') as config_file:
        restaurant_config.load(config_file)
        config_file.close()

    # ---> Loading the menu using the load_menu function of menu service module
    menu_content, status_code = load_menu(restaurant_id)
    if status_code != 200:
        return menu_content, status_code

    # ---> Replacing all the tags that were in prompt with the current restaurant values.
    data = prompt_file.read()
    data = data.replace("{name}", restaurant_config.get("name").data)
    data = data.replace("{timings}", restaurant_config.get("timings").data)
    data = data.replace("{representative_name}", restaurant_config.get("representative_name").data)
    data = data.replace("{address}", restaurant_config.get("address").data)
    data = data.replace("{today_special}", restaurant_config.get("today_special").data)
    data = data.replace("{menu}", menu_content)
    prompt_file.close()
    
    try:
        # ---> Adding the restaurant bot to the database using the properties read from the file if already not in the database
        restaurant_number = get_session_attribute('to_number')    # ---> Getting the current phone number 
        existing_bot = restaurants_bot.query.filter(
            restaurants_bot.restaurant_number == restaurant_number
        ).first()
        
        if existing_bot:
            # ---> Just return data if bot already exists
            return data, status_code
        else:
            # ---> Insert the new record if bot doesn't exist
            new_bot = restaurants_bot(restaurant_config.get("name").data, restaurant_number, 
                                    restaurant_config.get("timings").data, restaurant_config.get("representative_name").data,
                                    restaurant_config.get("address").data, restaurant_config.get("today_special").data,
                                    restaurant_config.get("clover_url").data, restaurant_config.get("clover_authorization_header").data,
                                    restaurant_config.get("twilio_account_sid").data, restaurant_config.get("twilio_account_auth_token").data,
                                    restaurant_config.get("agent_number").data)
            db.session.add(new_bot)
            db.session.commit()
    except Exception as e:
        print(e)
        return "Sorry for inconvenience. I am connecting you to the actual agent wait for some moments.", 506

    return data, status_code
