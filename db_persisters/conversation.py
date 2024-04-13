from database import db, conversation


# --- Function to get a conversation by restaurant id
def get_conversation_by_res_id(restaurant_id):
    conversation_obj = conversation.query.filter_by(
        restaurant_id=restaurant_id
    )
    return conversation_obj


# --- Function to get a conversation by customer id
def get_conversation_by_customer_id(customer_id):
    conversation_obj = conversation.query.filter_by(
        customer_id=customer_id
    )
    return conversation_obj


# --- Function to add conversation to the database
def add_conversation(restaurant_id, customer_id, conversation_text):
    new_conversation = conversation(
        restaurant_id=restaurant_id,
        customer_id=customer_id,
        conversation=conversation_text
    )
    db.session.add(new_conversation)
    db.session.commit()
    return new_conversation.id


# --- Function to get the conversation in proper format
def make_conversation_template(history):
    conversation = ""
    for item in history[2:]:
        role = item['role']
        content = item['content']
        if role == 'user':
            text = content.replace(" (refer to context)", "")
            conversation += f'USER: {text}\n'
        elif role == 'assistant':
            text = content.replace('<PLACE_ORDER_AND_END_CALL>', '')
            conversation += f'ASSISTANT: {text}\n'
    return conversation
