from database import db, restaurants_audit_trail


# --- Function to get a restaurant audit trail by its ID
def get_restaurant_audit_trail(restaurant_id):
    audit_trail_entry = restaurants_audit_trail.query.filter_by(
        restaurant_id=restaurant_id
    )
    return audit_trail_entry


# --- Function to add a restaurant audit trail to the database
def add_restaurant_audit_trail(restaurant_id, name, phone_number,
                               redirection_phone_number, information_json):
    new_audit_trail = restaurants_audit_trail(
        restaurant_id=restaurant_id,
        name=name,
        phone_number=phone_number,
        redirection_phone_number=redirection_phone_number,
        information_json=information_json
    )
    db.session.add(new_audit_trail)
    db.session.commit()
    return new_audit_trail.id
