from database import db, restaurant_system_configuration
from db_persisters.restaurant_system_configuration_audit_trail import \
    add_restaurant_system_configuration_audit_trail
import base64
import rsa
from database import privateKey, key


# --- Function to get the restaurant configuration using restaurant id
def get_restaurants_configuration(restaurant_id):
    restaurant = restaurant_system_configuration.query.filter_by(
        restaurant_id=restaurant_id
    ).first()
    return restaurant


# --- Function to add the restaurant configuration in the database
def add_restaurant_configuration(restaurant_id, pos_type, pos_url,
                                 pos_authorization_header, voice_api_type,
                                 voice_api_account_sid,
                                 voice_api_account_auth_token,
                                 payment_api_key, payment_secret):
    existing_res = get_restaurants_configuration(restaurant_id)
    if not existing_res:
        # ---> Initializing a new restaurant system configuration
        new_restaurant_configuration = restaurant_system_configuration(
            restaurant_id, pos_type,
            pos_url, pos_authorization_header,
            voice_api_type, voice_api_account_sid,
            voice_api_account_auth_token, payment_api_key,
            payment_secret,
        )
        # ---> Adding in the database
        db.session.add(new_restaurant_configuration)
        db.session.commit()


# --- Function to update the restaurant configuration in the database
def update_restaurant_config(restaurant_id, pos_type, pos_url,
                             pos_authorization_header, voice_api_type,
                             voice_api_account_sid,
                             voice_api_account_auth_token,
                             payment_api_key, payment_secret):
    res_config = get_restaurants_configuration(restaurant_id)
    en_pos_url = rsa.decrypt(
        base64.b64decode(res_config.pos_url), privateKey
    ).decode()
    en_pos_authorization_header = rsa.decrypt(
        base64.b64decode(res_config.pos_authorization_header), privateKey
    ).decode()
    en_voice_api_account_sid = rsa.decrypt(
        base64.b64decode(res_config.voice_api_account_sid), privateKey
    ).decode()
    en_voice_api_account_auth_token = rsa.decrypt(
        base64.b64decode(res_config.voice_api_account_auth_token),
        privateKey
    ).decode()
    en_payment_api_key = rsa.decrypt(
        base64.b64decode(res_config.payment_api_key), privateKey
    ).decode()
    en_payment_secret = rsa.decrypt(
        base64.b64decode(res_config.payment_secret), privateKey
    ).decode()
    add_restaurant_system_configuration_audit_trail(
        res_config.id, res_config.pos_type, en_pos_url,
        en_pos_authorization_header, res_config.voice_api_type,
        en_voice_api_account_sid, en_voice_api_account_auth_token,
        en_payment_api_key, en_payment_secret
    )
    res_config.pos_type = pos_type
    res_config.pos_url = base64.b64encode(
        rsa.encrypt(
            pos_url.encode(),
            key
        )
    ).decode('utf-8')
    res_config.pos_authorization_header = base64.b64encode(
        rsa.encrypt(
            pos_authorization_header.encode(),
            key
        )
    ).decode('utf-8')
    res_config.voice_api_type = voice_api_type
    res_config.voice_api_account_sid = base64.b64encode(
        rsa.encrypt(
            voice_api_account_sid.encode(),
            key
        )
    ).decode('utf-8')
    res_config.voice_api_account_auth_token = base64.b64encode(
        rsa.encrypt(
            voice_api_account_auth_token.encode(),
            key
        )
    ).decode('utf-8')
    res_config.payment_api_key = base64.b64encode(
        rsa.encrypt(
            payment_api_key.encode(),
            key
        )
    ).decode('utf-8')
    res_config.payment_secret = base64.b64encode(
        rsa.encrypt(
            payment_secret.encode(),
            key
        )
    ).decode('utf-8')

    db.session.commit()
