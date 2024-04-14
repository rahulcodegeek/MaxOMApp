from database import db, restaurant
from db_persisters.restaurants_audit_trail import add_restaurant_audit_trail
import json


# --- Function to get the restaurant using number
def get_restaurants(number):
    restaurant_entry = restaurant.query.filter_by(phone_number=number).first()
    return restaurant_entry


# --- Function to get the restaurant using restaurant id
def get_restaurants_by_id(restaurant_id):
    restaurant_entry = restaurant.query.filter_by(id=restaurant_id).first()
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
        persisted_restaurant = get_restaurants(phone_number)
        return persisted_restaurant.id
    else:
        update_restaurant(existing_res.id, name, phone_number,
                          redirection_phone_number, information_json)
        return existing_res.id


# --- Function to update the restaurant in the database
def update_restaurant(restaurant_id, name, phone_number,
                      redirection_phone_number, information_json):
    restaurant = get_restaurants_by_id(restaurant_id)
    add_restaurant_audit_trail(
        restaurant.id, restaurant.name, restaurant.phone_number, restaurant.redirection_phone_number,
        restaurant.information_json
    )
    restaurant.name = name
    restaurant.phone_number = phone_number
    restaurant.redirection_phone_number = redirection_phone_number
    restaurant.information_json = json.dumps(information_json)
    db.session.commit()
