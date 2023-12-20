from database import db, customer


# --- Function to get the customer using name
def get_customer_by_name(name):
    new_customer = customer.query.filter_by(
        customer_name=name
    )
    return new_customer


# --- Function to get the customer using phone number
def get_customer_by_number(customer_phone_number):
    new_customer = customer.query.filter_by(
        customer_phone_number=customer_phone_number
    ).first()
    return new_customer


# --- Function to get the customer using restaurant id
def get_customers_by_res_id(restaurant_id):
    new_customer = customer.query.filter_by(
        restaurant_id=restaurant_id
    )
    return new_customer


# --- Function to get the customer using customer id
def get_customers_by_id(_id):
    new_customer = customer.query.filter_by(
        id=_id
    ).first()
    return new_customer


# --- Function to add the customer in the database
def add_customer(restaurant_id, customer_name, customer_phone_number):
    existing_customer = get_customer_by_number(customer_phone_number)
    if not existing_customer:
        new_customer = customer(
            restaurant_id=restaurant_id,
            customer_name=customer_name,
            customer_phone_number=customer_phone_number
        )
        db.session.add(new_customer)
        db.session.commit()
        return new_customer.id
    return existing_customer.id
