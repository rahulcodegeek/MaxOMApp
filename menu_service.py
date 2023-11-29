from jproperties import Properties
import requests
import json


# --- A function to fetch the menu from the clover url 
def fetch_remote_menu(restaurant_id, endpoint):
    # ---> First read the properties using the restaurant id
    restaurant_config = Properties()
    restaurant_properties_file = "resources/"+restaurant_id+"/restaurant.properties"
    with open(restaurant_properties_file, 'rb') as config_file:
        restaurant_config.load(config_file)
        try:
            # ---> Getting clover url and authentication token from properties of the restaurant
            url = restaurant_config.get('clover_url').data
            auth = restaurant_config.get('clover_authorization_header').data
            headers = {"authorization": auth}
            # ---> Calling the clover url and returns it 
            response = requests.get(url+endpoint, headers=headers)
            config_file.close()
            return response, 200
        except Exception as e:
            # ---> If no url found or any error occurs 
            print("Error", e)
            config_file.close()
            return "Sorry for inconvenience. I am connecting you to the actual agent wait for some moments", 503


# --- A function write a menu file 
def persist_menu(restaurant_id, fetched_menu):
    # ---> Getting the elements
    modifier_groups_dictionary = {}
    modifier_groups_information = {}
    modifier_group, status = fetch_remote_menu(restaurant_id, "modifier_groups")
    if modifier_group.status_code == 200:
        modifier_data = modifier_group.json()
    for md_group in modifier_data['elements']:
        modifier_group_elements, status = fetch_remote_menu(restaurant_id, "modifier_groups/"+md_group['id']+"/items")
        if modifier_group_elements.status_code == 200:
            modifier_group_elements = modifier_group_elements.json()
        element = []
        for md_group_elements in modifier_group_elements['elements']:
            element.append(md_group_elements['name']) 
        modifier_groups_dictionary[md_group['name']] = element
        modifiers_list = md_group['modifierIds'].split(",")
        modifier_groups_information[md_group['name']] = {"Modifier Group Id":md_group['id'],"Hot":modifiers_list[0],"Medium":modifiers_list[1],"Mild":modifiers_list[2]}

    menu_data = json.loads(fetched_menu)
    menu_elements = menu_data['elements']
    # ---> Extract only desired fields from menu items (id, name, price)
    extracted_menu_items = []
    for element in menu_elements:
        extracted_element = {
            "id": element["id"],
            "name": element["name"],
            "price": element["price"]
        }
        for key, value in modifier_groups_dictionary.items():
            if element["name"] in value:
                group_id = modifier_groups_information[key]['Modifier Group Id']
                details = "[ "
                for index, (sub_key, sub_value) in enumerate(modifier_groups_information[key].items()):
                    if sub_key != "Modifier Group Id":
                        details += sub_key + " ("+sub_value +") "
                        if index != len(modifier_groups_information[key]) - 1:
                            details += "or "
                    if index == len(modifier_groups_information[key]) - 1:
                        details += "]"

                extracted_element['modifier_group_name'] = key+" ("+group_id+"): "+details
            else:
                extracted_element['modifier_group_name'] = " "
        extracted_menu_items.append(extracted_element)

    names = [element['name'] for element in extracted_menu_items]
    prices = [element['price'] for element in extracted_menu_items]
    ids = [element['id'] for element in extracted_menu_items]
    modify_group_element = [element['modifier_group_name'] for element in extracted_menu_items]

    # ---> Making Menu
    combined_strings = []
    for name, price, id, modify_group_element in zip(names, prices, ids, modify_group_element):
        if modify_group_element != " ":
            combined_strings.append(f"{name}: ${int(price)/100.0}, id: {id}, {modify_group_element}" )
        else:
            combined_strings.append(f"{name}: ${int(price)/100.0}, id: {id}" )

    food_menu = "\n".join(combined_strings)

    # ---> Open the file in write mode
    menu_file_name = "resources/"+restaurant_id+"/menu.txt"
    file = open(menu_file_name, "w")

    # ---> Write a string to the file
    menu_to_write = food_menu
    file.write(menu_to_write)

    # ---> Close the file
    file.close()


# --- A function to load the menu from the restaurant id path and return it
def load_menu(restaurant_id):
    try:
        menu_file_name = "resources/"+restaurant_id+"/menu.txt"
        menu_file = open(menu_file_name)
        menu_content = menu_file.read()
        menu_file.close()
        return menu_content, 200
    except Exception as e:
        print(e)
        return "Sorry for inconvenience. I am connecting you to the actual agent wait for some moments.", 504
    
