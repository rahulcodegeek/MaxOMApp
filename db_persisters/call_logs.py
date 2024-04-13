from call_status import CallStatus
from database import db, call_logs


# --- Function to get a call logs
def get_call_logs_by_id(id):
    call_log_obj = call_logs.query.filter_by(
        id=id
    )
    return call_log_obj


# --- Function to add conversation to the database
def add_call_log(conversation_id, restaurant_id, status, reason):
    if isinstance(status, CallStatus):
        new_call_log = call_logs(
            restaurant_id=restaurant_id,
            conversation_id=conversation_id,
            status=status.value,
            reason=reason
        )
        db.session.add(new_call_log)
        db.session.commit()
        return new_call_log.id
    else:
        print('Error in receiving call status, it is received as', status, ' which is not a valid valid for CallStatus enum')