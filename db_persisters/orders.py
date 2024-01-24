from database import db, order_info
import json


# --- Function to get an order by restaurant id
def get_order_by_res_id(restaurant_id):
    order_entry = order_info.query.filter_by(
        restaurant_id=restaurant_id
    )
    return order_entry


# --- Function to get an order by customer id
def get_order_by_customer_id(customer_id):
    order_entry = order_info.query.filter_by(
        customer_id=customer_id
    )
    return order_entry


# --- Function to get an order by order id
def get_order_by_order_id(order_id):
    order_entry = order_info.query.filter_by(
        id=order_id
    ).first()
    return order_entry


# --- Function to add an order to the database
def add_order(restaurant_id, customer_id, order_details, order_price,
              order_tax, total_price):
    order_details_ = json.dumps(order_details)
    new_order_info = order_info(
        restaurant_id=restaurant_id,
        customer_id=customer_id,
        order_details=order_details_,
        order_price=order_price,
        order_tax=order_tax,
        total_price=total_price
    )
    db.session.add(new_order_info)
    db.session.commit()
    return new_order_info.id
