# notification_storage.py
# Firestore logic for notifications collection
from firebase_admin import firestore
from datetime import datetime, timezone

db = firestore.client()

NOTIFICATION_TYPES = [
    "system", "user", "transactional", "promotional", "reminder", "security", "administrative"
]

def create_notification(type, content, post_date, end_date, created_by, scope, target_users=None):
    assert type in NOTIFICATION_TYPES, "Invalid notification type"
    assert scope in ["user", "end-user", "municipal", "regional", "national", "all"], "Invalid scope"
    # Ensure post_date and end_date are timezone-aware UTC
    if isinstance(post_date, str):
        post_date = datetime.fromisoformat(post_date)
    if post_date.tzinfo is None:
        post_date = post_date.replace(tzinfo=timezone.utc)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    doc = {
        "type": type,
        "scope": scope,
        "content": content,
        "post_date": post_date,
        "end_date": end_date,
        "created_by": created_by,
        "status": "scheduled" if post_date > now else "active",
        "target_users": target_users or [],
        "created_at": now,
    }
    ref = db.collection("notifications").add(doc)
    return ref


from google.cloud.firestore import DocumentReference

def _serialize_value(val):
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_serialize_value(v) for v in val]
    elif isinstance(val, datetime):
        return val.isoformat()
    elif hasattr(val, 'isoformat'):
        return val.isoformat()
    elif isinstance(val, DocumentReference):
        return str(val)
    else:
        return val

def _serialize_notification(doc):
    d = doc.to_dict()
    d = _serialize_value(d)
    d["id"] = doc.id
    return d

def get_active_notifications(now=None):
    now = now or datetime.now(timezone.utc)
    notifications = []
    for d in db.collection("notifications").stream():
        notif = d.to_dict()
        # Skip canceled notifications
        if notif.get("status") == "canceled":
            continue
        post_date = notif.get("post_date")
        end_date = notif.get("end_date")
        # Convert Firestore Timestamp or string to timezone-aware UTC datetime
        def to_aware(dt):
            if hasattr(dt, 'isoformat'):
                if getattr(dt, 'tzinfo', None) is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            try:
                parsed = datetime.fromisoformat(dt)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except Exception:
                return None
        post_date_dt = to_aware(post_date)
        end_date_dt = to_aware(end_date)

        # Determine status
        if end_date_dt and end_date_dt < now:
            notif["status"] = "inactive"
        elif post_date_dt and post_date_dt > now:
            notif["status"] = "to_post"
        elif post_date_dt and end_date_dt and post_date_dt <= now <= end_date_dt:
            notif["status"] = "posted"
        # else keep original status if dates are missing

        notif["id"] = d.id
        notifications.append(_serialize_value(notif))
    return notifications

def expire_old_notifications():
    now = datetime.utcnow()
    docs = db.collection("notifications") \
        .where("end_date", "<", now) \
        .where("status", "!=", "expired") \
        .stream()
    for d in docs:
        d.reference.update({"status": "expired"})
    # Optionally, delete expired notifications
    # for d in docs:
    #     d.reference.delete()
