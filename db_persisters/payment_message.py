from database import db, payment_message


# --- Function to get a payment message by restaurant id
def get_payment_message_by_res_id(restaurant_id):
    payment_message_obj = payment_message.query.filter_by(
        restaurant_id=restaurant_id
    )
    return payment_message_obj


# --- Function to get a payment message by customer id
def get_payment_message_by_customer_id(customer_id):
    payment_message_obj = payment_message.query.filter_by(
        customer_id=customer_id
    )
    return payment_message_obj


# --- Function to add a payment message to the database
def add_payment_message(restaurant_id, customer_id, message, logs):
    new_payment_message = payment_message(
        restaurant_id=restaurant_id,
        customer_id=customer_id,
        message=message,
        logs=logs
    )
    db.session.add(new_payment_message)
    db.session.commit()
    return new_payment_message.id
