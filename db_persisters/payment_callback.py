from database import db, payment_callback


# --- Function to get a payment callback by order id
def get_payment_callback_by_order_id(order_id):
    payment_callback_obj = payment_callback.query.filter_by(
        order_id=order_id
    ).first()
    return payment_callback_obj


# --- Function to get a payment callback by payment id
def get_payment_callback_by_payment_id(payment_id):
    payment_callback_obj = payment_callback.query.filter_by(
        payment_id=payment_id
    ).first()
    return payment_callback_obj


# --- Function to add a payment callback to the database
def add_payment_callback(order_id, payment_id, logs):
    new_payment_callback = payment_callback(
        order_id=order_id,
        payment_id=payment_id,
        logs=logs
    )
    db.session.add(new_payment_callback)
    db.session.commit()
    return new_payment_callback.id
