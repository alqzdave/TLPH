import os
import uuid
from datetime import datetime
from firebase_admin import firestore
from flask import current_app

# Firestore collection name
def get_inquiries_collection():
    return firestore.client().collection('inquiries')


def _conversation_key_from_doc(data):
    if not isinstance(data, dict):
        return ''
    return (data.get('user_id') or data.get('email') or data.get('user_email') or '').strip()


def _timestamp_sort_value(ts):
    if hasattr(ts, 'timestamp'):
        try:
            return ts.timestamp()
        except Exception:
            return 0
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
        except Exception:
            return 0
    return 0

def get_conversations():
    # Returns a list of unique conversations (by user)
    docs = get_inquiries_collection().stream()
    users = {}
    for doc in docs:
        data = doc.to_dict() or {}
        if not isinstance(data, dict):
            continue
        user_id = str(_conversation_key_from_doc(data) or '').strip()
        user_email = str(data.get('email') or data.get('user_email') or '').strip().lower()
        if not user_email and '@' in user_id:
            user_email = user_id.lower()

        msg_ts = data.get('timestamp', datetime.utcnow())
        msg_ts_sort = _timestamp_sort_value(msg_ts)

        if user_id and user_id not in users:
            users[user_id] = {
                'user_id': user_id,
                'email': user_email,
                'user_email': user_email,
                'user_name': data.get('user_name', ''),
                'user_photo': data.get('user_photo', ''),
                'last_message': data.get('message', ''),
                'last_time': msg_ts,
                '_last_time_sort': msg_ts_sort,
            }
        elif user_id:
            # Update last message if newer
            if msg_ts_sort > users[user_id].get('_last_time_sort', 0):
                users[user_id]['last_message'] = data.get('message', '')
                users[user_id]['last_time'] = msg_ts
                users[user_id]['_last_time_sort'] = msg_ts_sort

    conversations = list(users.values())
    for convo in conversations:
        convo.pop('_last_time_sort', None)
    return conversations

def get_messages(user_id):
    # Returns all messages for a conversation keyed by user_id/email.
    if not user_id:
        return []

    key = str(user_id).strip()

    docs = []

    # Query fast path first.
    try:
        docs = list(get_inquiries_collection().where('user_id', '==', key).stream())
    except Exception:
        docs = []
    if not docs:
        try:
            docs = list(get_inquiries_collection().where('email', '==', key.lower()).stream())
        except Exception:
            docs = []
    if not docs:
        try:
            docs = list(get_inquiries_collection().where('user_email', '==', key.lower()).stream())
        except Exception:
            docs = []

    # Ultimate fallback: full scan filter to avoid hard failures from query/index issues.
    if not docs:
        try:
            all_docs = list(get_inquiries_collection().stream())
            key_l = key.lower()
            for d in all_docs:
                data = d.to_dict() or {}
                if not isinstance(data, dict):
                    continue
                convo_id = str(data.get('user_id') or '').strip()
                convo_email = str(data.get('email') or data.get('user_email') or '').strip().lower()
                if convo_id == key or convo_email == key_l:
                    docs.append(d)
        except Exception:
            docs = []

    messages = []
    for doc in docs:
        data = doc.to_dict() or {}
        if isinstance(data, dict):
            messages.append(data)

    def _ts_value(msg):
        ts = msg.get('timestamp')
        if hasattr(ts, 'timestamp'):
            try:
                return ts.timestamp()
            except Exception:
                return 0
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
            except Exception:
                return 0
        return 0

    messages.sort(key=_ts_value)
    return messages

def add_message(
    user_id,
    user_name,
    message,
    user_photo=None,
    file_url=None,
    file_type=None,
    file_name=None,
    user_email=None,
    sender_email=None,
    sender_role=None,
    is_admin=False,
):
    user_id = str(user_id or '').strip()
    user_email = str(user_email or '').strip().lower()
    if not user_email and '@' in user_id:
        user_email = user_id.lower()

    doc = {
        'user_id': user_id,
        'email': user_email,
        'user_email': user_email,
        'user_name': user_name,
        'sender_email': (sender_email or user_email or '').strip().lower(),
        'sender_role': (sender_role or '').strip(),
        'is_admin': bool(is_admin),
        'message': message,
        'timestamp': datetime.utcnow(),
        'user_photo': user_photo or '',
        'file_url': file_url or '',
        'file_type': file_type or '',
        'file_name': file_name or '',
    }
    get_inquiries_collection().add(doc)
    return doc


def delete_conversation(conversation_key):
    """Delete all inquiry messages for a conversation key (user_id/email)."""
    key = str(conversation_key or '').strip()
    if not key:
        return 0

    key_l = key.lower()
    collection = get_inquiries_collection()
    deleted = 0
    seen_ids = set()

    for field, value in (('user_id', key), ('email', key_l), ('user_email', key_l)):
        try:
            docs = list(collection.where(field, '==', value).stream())
        except Exception:
            docs = []

        for doc in docs:
            if doc.id in seen_ids:
                continue
            try:
                doc.reference.delete()
                deleted += 1
                seen_ids.add(doc.id)
            except Exception:
                continue

    # Fallback full scan for inconsistent legacy rows.
    if deleted == 0:
        try:
            for doc in collection.stream():
                data = doc.to_dict() or {}
                if not isinstance(data, dict):
                    continue
                msg_uid = str(data.get('user_id') or '').strip()
                msg_email = str(data.get('email') or data.get('user_email') or '').strip().lower()
                if msg_uid == key or msg_email == key_l:
                    try:
                        doc.reference.delete()
                        deleted += 1
                    except Exception:
                        continue
        except Exception:
            pass

    return deleted
