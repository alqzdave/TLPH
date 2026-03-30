import os
import uuid
from datetime import datetime
from firebase_admin import firestore
from flask import current_app

# Firestore collection name
def get_inquiries_collection():
    return firestore.client().collection('inquiries')

def get_conversations():
    # Returns a list of unique conversations (by user)
    docs = get_inquiries_collection().stream()
    users = {}
    for doc in docs:
        data = doc.to_dict()
        user_id = data.get('user_id')
        if user_id and user_id not in users:
            users[user_id] = {
                'user_id': user_id,
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
    # Returns all messages for a conversation (by user_id)
    docs = get_inquiries_collection().where('user_id', '==', user_id).order_by('timestamp').stream()
    return [doc.to_dict() for doc in docs]

def add_message(user_id, user_name, message, user_photo=None, file_url=None, file_type=None):
    doc = {
        'user_id': user_id,
        'user_name': user_name,
        'message': message,
        'timestamp': datetime.utcnow(),
        'user_photo': user_photo or '',
        'file_url': file_url or '',
        'file_type': file_type or '',
    }
    get_inquiries_collection().add(doc)
    return doc
