import os
import uuid
from datetime import datetime
from firebase_admin import firestore
from flask import current_app

# Firestore collection name
def get_inquiries_collection():
    return firestore.client().collection('inquiries')


def _conversation_key_from_doc(data):
    return (data.get('user_id') or data.get('email') or data.get('user_email') or '').strip()

def get_conversations():
    # Returns a list of unique conversations (by user)
    docs = get_inquiries_collection().stream()
    users = {}
    for doc in docs:
        data = doc.to_dict()
        user_id = _conversation_key_from_doc(data)
        user_email = (data.get('email') or data.get('user_email') or '').strip().lower()
        if not user_email and '@' in user_id:
            user_email = user_id.lower()

        if user_id and user_id not in users:
            users[user_id] = {
                'user_id': user_id,
                'email': user_email,
                'user_email': user_email,
                'user_name': data.get('user_name', ''),
                'user_photo': data.get('user_photo', ''),
                'last_message': data.get('message', ''),
                'last_time': data.get('timestamp', datetime.utcnow()),
            }
        elif user_id:
            # Update last message if newer
            if data.get('timestamp', datetime.utcnow()) > users[user_id]['last_time']:
                users[user_id]['last_message'] = data.get('message', '')
                users[user_id]['last_time'] = data.get('timestamp', datetime.utcnow())
    return list(users.values())

def get_messages(user_id):
    # Returns all messages for a conversation keyed by user_id/email.
    if not user_id:
        return []

    key = str(user_id).strip()

    # Preserve existing behavior first.
    docs = list(get_inquiries_collection().where('user_id', '==', key).order_by('timestamp').stream())
    if not docs:
        docs = list(get_inquiries_collection().where('email', '==', key.lower()).order_by('timestamp').stream())
    if not docs:
        docs = list(get_inquiries_collection().where('user_email', '==', key.lower()).order_by('timestamp').stream())

    return [doc.to_dict() for doc in docs]

def add_message(user_id, user_name, message, user_photo=None, file_url=None, file_type=None, user_email=None):
    user_id = str(user_id or '').strip()
    user_email = str(user_email or '').strip().lower()
    if not user_email and '@' in user_id:
        user_email = user_id.lower()

    doc = {
        'user_id': user_id,
        'email': user_email,
        'user_email': user_email,
        'user_name': user_name,
        'message': message,
        'timestamp': datetime.utcnow(),
        'user_photo': user_photo or '',
        'file_url': file_url or '',
        'file_type': file_type or '',
    }
    get_inquiries_collection().add(doc)
    return doc
