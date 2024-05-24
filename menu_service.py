import requests
import base64
import json
import rsa
from db_persisters.restaurant_system_configuration import \
    get_restaurants_configuration
from database import privateKey


# --- A function to fetch the menu from the clover url
def fetch_remote_menu(restaurant_id, endpoint):
    try:
        print('File from 12/29/23')
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
        response = requests.get(url+endpoint+ '?limit=1000', headers=headers)
        return response, 200
    except Exception as e:
        # ---> If no url found or any error occurs
        print("Error in Url", e)
        return "Sorry for inconvenience. I am connecting you to the \
actual agent wait for some moments", 503


# --- A function to fetch the menu from the clover url
def fetch_remote_menu_modifiers(restaurant_id, endpoint):
    try:
        print('File from 12/29/23')
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
        response = requests.get(url+endpoint, headers=headers)
        return response, 200
    except Exception as e:
        # ---> If no url found or any error occurs
        print("Error in Url", e)
        return "Sorry for inconvenience. I am connecting you to the \
actual agent wait for some moments", 503


# --- A function write a menu file
# def persist_menu(restaurant_id, fetched_menu):
#     # ---> Getting the elements
#     print('persist menu Step 1', restaurant_id)
#     modifier_groups_dictionary = {}
#     modifi_groups_information = {}
#     item_names_to_exclude_from_final_menu = []
#
#     modifier_group, status = fetch_remote_menu(
#         restaurant_id, "modifier_groups"
#     )
#     print('persist menu Step 2 ', modifier_group.status_code)
#     if modifier_group.status_code == 200:
#         modifier_data = modifier_group.json()
#     for md_group in modifier_data['elements']:
#         #TODO - configure this md_group['name'].lower() == 'Spice level'  per the restaurant too..
#         if (md_group['name'].lower() == 'Spice level'.lower()):
#             modifier_group_elements, status = fetch_remote_menu(
#                 restaurant_id,
#                 "modifier_groups/"+md_group['id']+"/items"
#             )
#             if modifier_group_elements.status_code == 200:
#                 modifier_group_elements = modifier_group_elements.json()
#             element = []
#             for md_group_elements in modifier_group_elements['elements']:
#                 element.append(md_group_elements['name'])
#             modifier_groups_dictionary[md_group['name']] = element
#             modifiers_list = md_group['modifierIds'].split(",")
#             # TODO - configure this modifiers_list per the restaurant too..
#             modifi_groups_information[md_group['name']] = {
#                 "Modifier Group Id": md_group['id'],
#                 "Mild": "6YZ0NQMQ6E4D6",
#                 "Medium": "XE06JV8H5Q7E0",
#                 "Medium Hot": "VP34EZYQNJ4XT",
#                 "Hot": "4ET59HN040664",
#                 "Very Hot": "HBZ08PW79QND6"
#             }
#         elif (md_group['name'].lower() == 'NO_PICKUP'.lower()):
#             items_to_exclude, status = fetch_remote_menu(
#                 restaurant_id,
#                 "modifier_groups/" + md_group['id'] + "/items"
#             )
#             items_to_exclude = items_to_exclude.json()
#             for each_item_to_exclude in items_to_exclude['elements']:
#                 item_names_to_exclude_from_final_menu.append(each_item_to_exclude['name'])
#
#     print('persist menu Step 3')
#
#     menu_data = json.loads(fetched_menu)
#     menu_elements = menu_data['elements']
#     # ---> Extract only desired fields from menu items (id, name, price)
#     extracted_menu_items = []
#     for element in menu_elements:
#         #exclusion rule to skip the items if they are not needed in the menu
#         if (any(element["name"] in exclusion_match for exclusion_match in item_names_to_exclude_from_final_menu)):
#             print('found in exclusion list', element["name"])
#             continue
#         #if passed the exclusion filter keep on processing the rest
#
#         extracted_element = {
#             "id": element["id"],
#             "name": element["name"],
#             "price": element["price"]
#         }
#         for key, value in modifier_groups_dictionary.items():
#             if element["name"] in value:
#                 group_id = modifi_groups_information[key]['Modifier Group Id']
#                 details = "[ "
#                 for index, (sub_key, sub_value) in enumerate(
#                     modifi_groups_information[key].items()
#                 ):
#                     if sub_key != "Modifier Group Id":
#                         details += sub_key + " ("+sub_value + ") "
#                         if index != len(modifi_groups_information[key]) - 1:
#                             details += "or "
#                     if index == len(modifi_groups_information[key]) - 1:
#                         details += "]"
#                 extracted_element['modifier_group_name'] = key+" (" + \
#                     group_id + "): " + details
#             else:
#                 extracted_element['modifier_group_name'] = " "
#         extracted_menu_items.append(extracted_element)
#
#     print('persist menu Step 4')
#
#     names = [element['name'] for element in extracted_menu_items]
#     prices = [element['price'] for element in extracted_menu_items]
#     ids = [element['id'] for element in extracted_menu_items]
#     modify_group_element = [element['modifier_group_name'] for element in extracted_menu_items]
#     # ---> Making Menu
#     combined_strings = []
#     for name, price, id, modify_group_element in zip(names, prices, ids, modify_group_element):
#         if modify_group_element != " ":
#             combined_strings.append(f"{name}: ${int(price)/100.0}, id: {id}, {modify_group_element}")
#         else:
#             combined_strings.append(f"{name}: ${int(price)/100.0}, id: {id}")
#
#     print('persist menu Step 5')
#
#     food_menu = "\n".join(combined_strings)
#
#     # ---> Open the file in write mode
#     menu_file_name = "resources/"+str(restaurant_id)+"_menu.txt"
#     file = open(menu_file_name, "w")
#
#     # ---> Write a string to the file
#     menu_to_write = food_menu
#     print('persist menu Step 6')
#     file.write(menu_to_write)
#     # ---> Close the file
#     file.close()

def persist_menu(restaurant_id, fetched_menu):
    # ---> Getting the elements
    print('persist menu Step 1', restaurant_id)
    items_and_modifiers_in_a_modifier_group_dictionary = {}
    modifier_group_modifier_group_id_modifier_id_price_dictionary = {}
    item_names_to_exclude_from_final_menu = []

    modifier_group, status = fetch_remote_menu(restaurant_id, "modifier_groups")
    print('persist menu Step 2 ', modifier_group.status_code)
    if modifier_group.status_code == 200:
        modifier_groups_from_data = modifier_group.json()
    for modifier_group in modifier_groups_from_data['elements']:
        modifier_group_modifiers_and_items, status = fetch_remote_menu_modifiers( restaurant_id,
            "modifier_groups/"+modifier_group['id']+"?expand=modifiers,items&limit=1000"
        )
        if modifier_group_modifiers_and_items.status_code == 200:
            modifier_group_modifiers_and_items = modifier_group_modifiers_and_items.json()
        fetched_menu_items_in_a_modifier_group = []
        fetched_modifiers_in_a_modifier_group = []
        for modifier_group_item_element in modifier_group_modifiers_and_items['items']['elements']:
            fetched_menu_items_in_a_modifier_group.append(modifier_group_item_element['name'])
        for modifier_group_modifier_element in modifier_group_modifiers_and_items['modifiers']['elements']:
            fetched_modifiers_in_a_modifier_group.append(
                {
                    "name": modifier_group_modifier_element['name'],
                    "id": modifier_group_modifier_element['id'],
                    "price": modifier_group_modifier_element['price']
                }
                )
        items_and_modifiers_in_a_modifier_group_dictionary[modifier_group['name']] = {
            'items': fetched_menu_items_in_a_modifier_group, 'modifiers': fetched_modifiers_in_a_modifier_group
        }
        modifier_group_modifier_group_id_modifier_id_price_dictionary[modifier_group['name']] = {
            "Modifier Group Id": modifier_group['id']
        }
        for modifier in fetched_modifiers_in_a_modifier_group:
            modifier_group_modifier_group_id_modifier_id_price_dictionary[modifier_group['name']][modifier['name']] = { "id": modifier['id'], "price": modifier['price']}

        if (modifier_group['name'].lower() == 'NO_PICKUP'.lower()):
            items_to_exclude, status = fetch_remote_menu( restaurant_id, 
                "modifier_groups/" + modifier_group['id'] + "/items"
            )
            items_to_exclude = items_to_exclude.json()
            for each_item_to_exclude in items_to_exclude['elements']:
                item_names_to_exclude_from_final_menu.append(each_item_to_exclude['name'])

    print('persist menu Step 3')

    base_menu_data = json.loads(fetched_menu)
    base_menu_elements = base_menu_data['elements']
    # ---> Extract only desired fields from menu items (id, name, price)
    extracted_menu_items = []
    modifiers_json = {}
    for base_menu_item in base_menu_elements:
        # exclusion rule to skip the items if they are not needed in the menu
        if (any(base_menu_item["name"] in exclusion_match for exclusion_match in
                item_names_to_exclude_from_final_menu)):
            continue
        # if passed the exclusion filter keep on processing the rest

        extracted_element = {
            "id": base_menu_item["id"],
            "name": base_menu_item["name"],
            "price": base_menu_item["price"],
            "modifier_group_name" : ""
        }

        for key, value in items_and_modifiers_in_a_modifier_group_dictionary.items():
            modifier_group_id = modifier_group_modifier_group_id_modifier_id_price_dictionary[key]['Modifier Group Id']
            #details = f'Type - {key} Modifiers (ID: {modifier_group_id})\nOptions\n'
            ######################
            modifiers_json[key] = {'modifier_type_id':  modifier_group_id}
            ######################
            modifiers_json[key]['modifiers'] = []
            for sub_key, sub_value in modifier_group_modifier_group_id_modifier_id_price_dictionary[key].items():
                if sub_key != "Modifier Group Id":
                    modifiers_json_modifiers_list = modifiers_json[key]['modifiers']
                    modifiers_json_modifier = {
                        "id": sub_value["id"],
                        "name": sub_key,
                        "price": int(sub_value["price"] / 100)
                    }
                    modifiers_json_modifiers_list.append(modifiers_json_modifier)

            # Add relevant modifier types
            if base_menu_item["name"] in value['items']:
                # modify the modifier_group_name based on which modifier group is attached to this menu item in context
                extracted_element['modifier_group_name'] += (key if extracted_element['modifier_group_name'] == "" else ", " + key)
        # build the final menu item list with its modifier groups information
        extracted_menu_items.append(extracted_element)

    # Path to your JSON file
    modifier_file_name = f"resources/{restaurant_id}_modifier.json"

    # Writing to the file with explicit newline handling
    with open(modifier_file_name, "w") as file:
        json.dump(modifiers_json, file, indent=4)
    # ---> Close the file
    file.close()
    print('persist menu Step 4')

    names = [element['name'] for element in extracted_menu_items]
    prices = [element['price'] for element in extracted_menu_items]
    ids = [element['id'] for element in extracted_menu_items]
    modify_group_element = [element['modifier_group_name'] for element in extracted_menu_items]
    # ---> Making Menu
    combined_strings = []
    for name, price, id, modify_group_element in zip(names, prices, ids, modify_group_element):
        if modify_group_element != " ":
            combined_strings.append(f"{name}: ${int(price)/100.0}, id: {id}, {modify_group_element}")
        else:
            combined_strings.append(f"{name}: ${int(price)/100.0}, id: {id}")

    print('persist menu Step 5')
    menu_items = "\n".join(combined_strings)
    # ---> Open the file in write mode
    menu_item_file_name = "resources/"+str(restaurant_id)+"_menu.txt"
    file = open(menu_item_file_name, "w")

    # ---> Write a string to the file
    print('persist menu Step 6')
    file.write(menu_items)
    # ---> Close the file
    file.close()


# --- A function to load the menu from the restaurant id path and return it
def load_menu(restaurant_id):
    try:
        menu_file_name = "resources/"+str(restaurant_id)+"_menu.txt"
        menu_file = open(menu_file_name)
        menu_content = menu_file.read()
        menu_file.close()
        return menu_content, 200
    except Exception as e:
        print(e)
        return "Sorry for inconvenience. I am connecting you to the \
actual agent wait for some moments.", 504
