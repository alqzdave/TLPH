import firebase_admin
from firebase_admin import credentials, db, firestore
import pyrebase
from config import Config

# Initialize Firebase Admin SDK
def initialize_firebase_admin():
    """Initialize Firebase Admin SDK for server-side operations"""
    try:
        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred, {
            'databaseURL': Config.FIREBASE_CONFIG['databaseURL']
        })
        print("Firebase Admin initialized successfully!")
    except Exception as e:
        print(f"Error initializing Firebase Admin: {e}")

# Initialize Pyrebase for client-side operations
def get_firebase_client():
    """Get Pyrebase client for authentication and client operations"""
    try:
        firebase = pyrebase.initialize_app(Config.FIREBASE_CONFIG)
        return firebase
    except Exception as e:
        print(f"Error initializing Pyrebase: {e}")
        return None

# Get Firestore database reference
def get_firestore_db():
    """Get Firestore database reference"""
    return firestore.client()

# Get Realtime Database reference
def get_realtime_db():
    """Get Realtime Database reference"""
    return db.reference()
