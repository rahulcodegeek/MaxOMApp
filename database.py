import rsa
import base64
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
db = SQLAlchemy()

# Read private key from file
with open('./resources/privateKey.pem', 'rb') as private_key_file:
    private_key_data = private_key_file.read()
    privateKey = rsa.PrivateKey.load_pkcs1(private_key_data)

# Read public key from file
with open('./resources/publicKey.pem', 'rb') as public_key_file:
    public_key_data = public_key_file.read()
    key = rsa.PublicKey.load_pkcs1(public_key_data)


# --- Restaurants table to store restaurants data in the database
class restaurant(db.Model):
    # --> Stores the id of restaurant
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the name of the restaurant
    name = db.Column(db.String(200), nullable=False)
    # --> Stores the unique phone number of the restaurant
    phone_number = db.Column(db.String(200), unique=True, nullable=False)
    # --> Stores the redirecting phone number
    redirection_phone_number = db.Column(db.String(100), nullable=False)
    # --> Stores the restaurant information
    information_json = db.Column(db.String(500), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )
    # --> Defining relationship with restaurant audit
    restaurants_audits = db.relationship(
        'restaurant_audit_trail', backref='owner'
    )
    # --> Defining relationship with restaurant_system_configuration
    restaurant_system_configuration = db.relationship(
        'restaurant_system_configuration', backref='owner'
    )
    # --> Defining relationship with customer
    customers = db.relationship(
        'customer', backref='owner'
    )
    # --> Defining relationship with order_info
    res_order_info = db.relationship(
        'order_info', backref='owner'
    )
    # --> Defining relationship with conversation
    conversations = db.relationship(
        'conversation', backref='owner'
    )
    # --> Defining relationship with payment_message
    payment_messages = db.relationship(
        'payment_message', backref='owner'
    )

    # ---> Function to initialize a restaurant
    def __init__(self, name, phone_number, redirection_phone_number,
                 information_json):
        self.name = name
        self.phone_number = phone_number
        self.redirection_phone_number = redirection_phone_number
        self.information_json = information_json
        self.created_date = datetime.now(timezone.utc)


# --- Restaurants audit trail table to edit original restaurant table
class restaurant_audit_trail(db.Model):
    # --> Stores the id of restaurant audit trail
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id with the trail record
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant.id'), nullable=False
    )
    # --> Stores the name of the restaurant
    name = db.Column(db.String(200), nullable=False)
    # --> Stores the unique phone number of the restaurant
    phone_number = db.Column(db.String(200), nullable=False)
    # --> Stores the redirecting phone number
    redirection_phone_number = db.Column(db.String(100), nullable=False)
    # --> Stores the restaurant information
    information_json = db.Column(db.String(500), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )
    # ---> Function to initialize a restaurant
    def __init__(self, restaurant_id, name, phone_number,
                 redirection_phone_number, information_json):
        self.restaurant_id = restaurant_id
        self.name = name
        self.phone_number = phone_number
        self.redirection_phone_number = redirection_phone_number
        self.information_json = information_json
        self.created_date = datetime.now(timezone.utc)


# --- Restaurants System Configuration table to store the configuration
# --- of Restaurants in the database
class restaurant_system_configuration(db.Model):
    # --> Stores the id of restaurant system configuration
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id associate with configuration
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant.id'), nullable=False
    )
    # --> Stores the point of sale type of the restaurant
    pos_type = db.Column(db.String(200), nullable=False)
    # --> Stores the url of the point of sale
    pos_url = db.Column(db.String(1000), nullable=False)
    # --> Stores the authentication of the point of sale
    pos_authorization_header = db.Column(db.String(1000), nullable=False)
    # --> Stores the tax rate code of the point of sale
    pos_tax_rate_code = db.Column(db.String(32), nullable=False)
    # --> Stores type of the voice api
    voice_api_type = db.Column(db.String(500), nullable=False)
    # --> Stores sid of the voice api
    voice_api_account_sid = db.Column(db.String(1000), nullable=False)
    # --> Stores api auth token of the voice api
    voice_api_account_auth_token = db.Column(db.String(1000), nullable=False)
    # --> Stores payment api key
    payment_api_key = db.Column(db.String(1000), nullable=False)
    # --> Stores payment secret api key
    payment_secret = db.Column(db.String(1000), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )
    # --> Defining relationship with restaurant_system_configuration_audit
    restaurant_system_configurations_audit = db.relationship(
        'restaurant_system_configuration_audit_trail', backref='owner'
    )

    # ---> Function to initialize a restaurant system configuration
    def __init__(self, restaurant_id,
                 pos_type, pos_url, pos_authorization_header, pos_tax_rate_code,
                 voice_api_type, voice_api_account_sid, voice_api_account_auth_token,
                 payment_api_key, payment_secret):
        self.restaurant_id = restaurant_id
        self.pos_type = pos_type
        self.pos_url = base64.b64encode(
            rsa.encrypt(
                pos_url.encode(),
                key
            )
        ).decode('utf-8')
        self.pos_authorization_header = base64.b64encode(
            rsa.encrypt(
                pos_authorization_header.encode(),
                key
            )
        ).decode('utf-8')
        self.pos_tax_rate_code = base64.b64encode(
            rsa.encrypt(
                pos_tax_rate_code.encode(),
                key
            )
        ).decode('utf-8')
        self.voice_api_type = voice_api_type
        self.voice_api_account_sid = base64.b64encode(
            rsa.encrypt(
                voice_api_account_sid.encode(),
                key
            )
        ).decode('utf-8')
        self.voice_api_account_auth_token = base64.b64encode(
            rsa.encrypt(
                voice_api_account_auth_token.encode(),
                key
            )
        ).decode('utf-8')
        self.payment_api_key = base64.b64encode(
            rsa.encrypt(
                payment_api_key.encode(),
                key
            )
        ).decode('utf-8')
        self.payment_secret = base64.b64encode(
            rsa.encrypt(
                payment_secret.encode(),
                key
            )
        ).decode('utf-8')
        self.created_date = datetime.now(timezone.utc)


# --- Restaurants System Configuration audit table to edit the
# --- Restaurants System Configuration table
class restaurant_system_configuration_audit_trail (db.Model):
    # --> Stores the id of restaurant system configuration
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id associate with configuration
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant_system_configuration.id'),
        nullable=False
    )
    # --> Stores the point of sale type of the restaurant
    pos_type = db.Column(db.String(200), nullable=False)
    # --> Stores the url of the point of sale
    pos_url = db.Column(db.String(1000), nullable=False)
    # --> Stores the authentication of the point of sale
    pos_authorization_header = db.Column(db.String(1000), nullable=False)
    # --> Stores the tax rate code of the point of sale
    pos_tax_rate_code = db.Column(db.String(32), nullable=False)
    # --> Stores type of the voice api
    voice_api_type = db.Column(db.String(500), nullable=False)
    # --> Stores sid of the voice api
    voice_api_account_sid = db.Column(db.String(1000), nullable=False)
    # --> Stores api auth token of the voice api
    voice_api_account_auth_token = db.Column(db.String(1000), nullable=False)
    # --> Stores payment api key
    payment_api_key = db.Column(db.String(1000), nullable=False)
    # --> Stores payment secret api key
    payment_secret = db.Column(db.String(1000), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )

    # ---> Function to initialize a restaurant system configuration
    def __init__(self, restaurant_id,
                 pos_type, pos_url, pos_authorization_header, pos_tax_rate_code,
                 voice_api_type, voice_api_account_sid, voice_api_account_auth_token,
                 payment_api_key, payment_secret):
        self.restaurant_id = restaurant_id
        self.pos_type = pos_type
        self.pos_url = base64.b64encode(
            rsa.encrypt(
                pos_url.encode(),
                key
            )
        ).decode('utf-8')
        self.pos_authorization_header = base64.b64encode(
            rsa.encrypt(
                pos_authorization_header.encode(),
                key
            )
        ).decode('utf-8')
        self.pos_tax_rate_code = base64.b64encode(
            rsa.encrypt(
                pos_tax_rate_code.encode(),
                key
            )
        ).decode('utf-8')
        self.voice_api_type = voice_api_type
        self.voice_api_account_sid = base64.b64encode(
            rsa.encrypt(
                voice_api_account_sid.encode(),
                key
            )
        ).decode('utf-8')
        self.voice_api_account_auth_token = base64.b64encode(
            rsa.encrypt(
                voice_api_account_auth_token.encode(),
                key
            )
        ).decode('utf-8')
        self.payment_api_key = base64.b64encode(
            rsa.encrypt(
                payment_api_key.encode(),
                key
            )
        ).decode('utf-8')
        self.payment_secret = base64.b64encode(
            rsa.encrypt(
                payment_secret.encode(),
                key
            )
        ).decode('utf-8')
        self.created_date = datetime.now(timezone.utc)


# --- Customer table to store the customer information in the database
class customer(db.Model):
    # --> Stores the id of customer
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id associate with customer
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant.id'), nullable=False
    )
    # --> Stores the name of the customer
    customer_name = db.Column(db.String(200), nullable=False)
    # --> Stores the phone number of customer
    customer_phone_number = db.Column(
        db.String(100), unique=True, nullable=False
    )
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )

    def __init__(self, restaurant_id, customer_name,
                 customer_phone_number):
        self.restaurant_id = restaurant_id
        self.customer_name = customer_name
        self.customer_phone_number = customer_phone_number
        self.created_date = datetime.now(timezone.utc)


# --- Order_info table to store the confirmed order in the database
class order_info(db.Model):
    # --> Stores the id of order_info
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id associate with order_info
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant.id'), nullable=False
    )
    # --> Stores the customer id associate with order_info
    customer_id = db.Column(
        db.Integer, db.ForeignKey('customer.id'),
        nullable=False
    )
    # --> Stores the complete order_info
    order_details = db.Column(db.String(5000), nullable=False)
    # --> Stores the total price of order
    order_price = db.Column(db.String(200), nullable=False)
    # --> Stores the tax price of order
    order_tax = db.Column(db.String(200), nullable=False)
    # --> Stores the total price of order including tax
    total_price = db.Column(db.String(200), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )
    # --> Defining relationship with payment_callback
    payment_callback = db.relationship(
        'payment_callback', backref='owner'
    )

    # ---> Function to initialize an order_info
    def __init__(self, restaurant_id, customer_id, order_details,
                 order_price, order_tax, total_price):
        self.restaurant_id = restaurant_id
        self.customer_id = customer_id
        self.order_details = order_details
        self.order_price = order_price
        self.order_tax = order_tax
        self.total_price = total_price
        self.created_date = datetime.now(timezone.utc)


# --- Conversation table to store the conversations in the database
class conversation(db.Model):
    # --> Stores the id of conversation
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id associate with customer
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant.id'), nullable=False
    )
    # --> Stores the customer id associate with order_info
    customer_id = db.Column(
        db.Integer, db.ForeignKey('customer.id'),
        nullable=False
    )
    # --> Stores the conversation
    conversation = db.Column(db.String(10000), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )

    def __init__(self, restaurant_id, customer_id,
                 conversation):
        self.restaurant_id = restaurant_id
        self.customer_id = customer_id
        self.conversation = conversation
        self.created_date = datetime.now(timezone.utc)


# --- Payment Message table to store the message in the database
class payment_message(db.Model):
    # --> Stores the id of payment_message
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id associate with customer
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant.id'), nullable=False
    )
    # --> Stores the customer id associate with order_info
    customer_id = db.Column(
        db.Integer, db.ForeignKey('customer.id'),
        nullable=False
    )
    # --> Stores the payment message
    message = db.Column(db.String(1000), nullable=False)
    # --> Stores the logs of message
    logs = db.Column(db.String(1000), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )

    def __init__(self, restaurant_id, customer_id,
                 message, logs):
        self.restaurant_id = restaurant_id
        self.customer_id = customer_id
        self.message = message
        self.logs = logs
        self.created_date = datetime.now(timezone.utc)


# --- Payment Successful Callback table to store the message in the database
class payment_callback(db.Model):
    # --> Stores the id of payment_callback
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the order id associate with order
    order_info_id = db.Column(
        db.Integer, db.ForeignKey('order_info.id'),
        nullable=False
    )
    # --> Stores the stripe payment id
    payment_id = db.Column(db.String(1000), nullable=False)
    # --> Stores the logs of payment
    logs = db.Column(db.String(1000), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )

    def __init__(self, order_info_id, payment_id, logs):
        self.order_info__id = order_info_id
        self.payment_id = payment_id
        self.logs = logs
        self.created_date = datetime.now(timezone.utc)


# --- Pos Order table to store the message in the database
class pos_order(db.Model):
    # --> Stores the id of payment_callback
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the order id associate with order
    order_id = db.Column(
        db.Integer, db.ForeignKey('order_info.id'),
        nullable=False
    )
    # --> Stores the clover order id
    clover_order_id = db.Column(db.String(1000), nullable=False)
    # --> Stores the logs of payment
    print_status = db.Column(db.String(1000), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )

    def __init__(self, order_id, clover_order_id, print_status):
        self.order_id = order_id
        self.clover_order_id = clover_order_id
        self.print_status = print_status
        self.created_date = datetime.now(timezone.utc)

# --- Call Logs table to store the call logs in the database
class call_logs(db.Model):
    # --> Stores the id of call logs
    id = db.Column(db.Integer, primary_key=True)
    # --> Stores the restaurant id associate with call logs
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurant.id'), nullable=False
    )
    # --> Stores the conversation id
    conversation_id = db.Column(db.String(64), nullable=False)
    # --> Stores the status of the call
    status = db.Column(db.String(32), nullable=False)
    # --> Stores the reason of the call ends
    reason = db.Column(db.String(1024), nullable=False)
    # --> Stores the creation date
    created_date = db.Column(
        db.DateTime, nullable=False
    )

    def __init__(self, restaurant_id, conversation_id, status, reason):
        self.restaurant_id = restaurant_id
        self.conversation_id = conversation_id
        self.status = status
        self.reason = reason
        self.created_date = datetime.now(timezone.utc)