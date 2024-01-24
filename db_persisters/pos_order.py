from database import db, pos_order


# --- Function to get a payment callback by order id
def get_pos_order_by_order_id(order_id):
    pos_order_obj = pos_order.query.filter_by(
        order_id=order_id
    ).first()
    return pos_order_obj


# --- Function to get a payment callback by payment id
def get_pos_order_by_clover_order_id(clover_order_id):
    pos_order_obj = pos_order.query.filter_by(
        clover_order_id=clover_order_id
    ).first()
    return pos_order_obj


# --- Function to add a payment callback to the database
def add_pos_order(order_id, clover_order_id, print_status):
    new_pos_order = pos_order(
        order_id=order_id,
        clover_order_id=clover_order_id,
        print_status=print_status
    )
    db.session.add(new_pos_order)
    db.session.commit()
    return new_pos_order.id
