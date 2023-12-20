from database import db, restaurant_system_configuration_audit_trail


# --- Function to get a restaurant system configuration audit trail by
# --- Restaurant ID
def get_restaurant_system_configuration_audit_trail(restaurant_id):
    audit = restaurant_system_configuration_audit_trail.query.filter_by(
        restaurant_id=restaurant_id
    )
    return audit


# --- Function to add the restaurant configuration audit in the database
def add_restaurant_system_configuration_audit_trail(
        restaurant_id, pos_type, pos_url, pos_authorization_header,
        voice_api_type, voice_api_account_sid, voice_api_account_auth_token,
        payment_api_key, payment_secret):
    new_config = restaurant_system_configuration_audit_trail(
        restaurant_id=restaurant_id,
        pos_type=pos_type,
        pos_url=pos_url,
        pos_authorization_header=pos_authorization_header,
        voice_api_type=voice_api_type,
        voice_api_account_sid=voice_api_account_sid,
        voice_api_account_auth_token=voice_api_account_auth_token,
        payment_api_key=payment_api_key,
        payment_secret=payment_secret
    )
    db.session.add(new_config)
    db.session.commit()
    return new_config.id
