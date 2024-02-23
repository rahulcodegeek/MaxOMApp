import uuid
from flask import session


# --- Creating Session
def create_session():
    session['session_id'] = str(uuid.uuid4())


# --- Setting a session attribute using its name and value
def set_session_attribute(attribute_name, value):
    session[attribute_name] = value


# --- Getting an session attribute using its name
def get_session_attribute(attribute_name):
    return session[attribute_name]


# --- Deleting a session attribute using the name of attribute
def delete_session_attribute(attribute_name):
    if session.get(attribute_name):
        if session[attribute_name]:
            del session[attribute_name]
    return None
