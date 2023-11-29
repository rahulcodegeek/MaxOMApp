from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# --- Orders table to store the confirmed order in the database
class orders(db.Model):
    id = db.Column(db.Integer, primary_key = True)    # --> Stores the id of order
    restaurant_number = db.Column(db.String(200))    # --> Stores the restaurant number on which call is made
    customer_session_id = db.Column(db.String(200),unique = True)    # --> Stores the session id of customer which must be unique
    customer_name = db.Column(db.String(200))    # --> Stores the total price of order
    customer_phone_number = db.Column(db.String(100))    # --> Stores the phone number of customer
    customer_order = db.Column(db.String(5000))    # --> Stores the complete order
    customer_total_order_price = db.Column(db.String(200))    # --> Stores the total price of order
    
    # ---> Function to initialize an order
    def __init__(self, restaurant_number, customer_session_id, customer_name,
                 customer_phone_number, customer_order, customer_total_order_price):
        self.restaurant_number = restaurant_number
        self.customer_session_id = customer_session_id
        self.customer_name = customer_name
        self.customer_phone_number = customer_phone_number
        self.customer_order = customer_order
        self.customer_total_order_price = customer_total_order_price
        
    

# --- Restaurants Bot table to store the multiple bots in the database
class restaurants_bot(db.Model):
    id = db.Column(db.Integer, primary_key = True)    # --> Stores the id of restaurant bot
    restaurant_name = db.Column(db.String(200))    # --> Stores the name of the restaurant
    restaurant_number = db.Column(db.String(200), unique = True)    # --> Stores the unique phone number of the restaurant
    restaurant_timing = db.Column(db.String(100))    # --> Stores the restaurant timing details
    representative_name = db.Column(db.String(100))    # --> Stores the representative name of the restaurant
    restaurant_address = db.Column(db.String(500))      # --> Stores the address of the restaurant
    restaurant_today_special= db.Column(db.String(200))    # --> Stores the today's special item of the restaurant
    clover_url= db.Column(db.String(200))    # --> Stores the clover url of the restaurant along with the merchant id
    clover_authorization_header= db.Column(db.String(200))    # --> Stores the clover authentication key of the merchant
    twilio_account_sid= db.Column(db.String(200))    # --> Stores the clover authentication key of the merchant
    twilio_account_auth_token= db.Column(db.String(200))    # --> Stores the clover authentication key of the merchant
    agent_number= db.Column(db.String(200))    # --> Stores the agent number to forward call


    
    # ---> Function to initialized an restaurant bot
    def __init__(self, restaurant_name, restaurant_number, restaurant_timing,
                representative_name, restaurant_address, restaurant_today_special,
                clover_url, clover_authorization_header, twilio_account_sid,
                twilio_account_auth_token, agent_number):
        
        self.restaurant_name = restaurant_name
        self.restaurant_number = restaurant_number
        self.restaurant_timing = restaurant_timing
        self.representative_name = representative_name
        self.restaurant_address = restaurant_address
        self.restaurant_today_special = restaurant_today_special
        self.clover_url = clover_url
        self.clover_authorization_header = clover_authorization_header
        self.twilio_account_sid = twilio_account_sid
        self.twilio_account_auth_token = twilio_account_auth_token
        self.agent_number = agent_number