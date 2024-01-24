from database import db, restaurant
from db_persisters.restaurants_audit_trail import add_restaurant_audit_trail
import json


# --- Function to get the restaurant using number
def get_restaurants(number):
    restaurant_entry = restaurant.query.filter_by(phone_number=number).first()
    return restaurant_entry


# --- Function to get the restaurant using restaurant id
def get_restaurants_by_id(res_id):
    restaurant_entry =  restaurant.query.filter_by(id=res_id).first()
    return restaurant_entry


# --- Function to add the restaurant in the database
def add_restaurant(name, phone_number, redirection_phone_number,
                   information_json):
    existing_res = get_restaurants(phone_number)
    if not existing_res:
        information_string = json.dumps(information_json)
        # ---> Initializing a new order
        new_restaurant = restaurant(
            name, phone_number,
            redirection_phone_number,
            information_string,
        )
        # ---> Adding in the database
        db.session.add(new_restaurant)
        db.session.commit()
    return phone_number


# --- Function to update the restaurant in the database
def update_restaurant(restaurant_id, name, phone_number,
                      redirection_phone_number, information_json):
    res = get_restaurants_by_id(restaurant_id)
    add_restaurant_audit_trail(
        res.id, res.name, res.phone_number,
        res.redirection_phone_number,
        res.information_json
    )
    res.name = name
    res.phone_number = phone_number
    res.redirection_phone_number = redirection_phone_number
    res.information_json = information_json
    db.session.commit()
