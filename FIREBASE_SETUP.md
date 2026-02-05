# Firebase Integration Setup Guide

## 1. Get Firebase Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing project
3. Go to **Project Settings** (gear icon)
4. Under **General** tab, find **Your apps** section
5. If no app exists, click "Add app" and select Web (</>) icon
6. Copy the Firebase configuration values

## 2. Get Service Account Key

1. In Firebase Console, go to **Project Settings** > **Service Accounts**
2. Click **Generate New Private Key**
3. Save the JSON file as `firebase-credentials.json` in your project root
4. **IMPORTANT**: Add this file to `.gitignore` (already done)

## 3. Setup Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your Firebase credentials in `.env`:
   - FIREBASE_API_KEY
   - FIREBASE_AUTH_DOMAIN
   - FIREBASE_DATABASE_URL
   - FIREBASE_PROJECT_ID
   - FIREBASE_STORAGE_BUCKET
   - FIREBASE_MESSAGING_SENDER_ID
   - FIREBASE_APP_ID

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Firebase Database Options

### Firestore (NoSQL Document Database)
```python
from firebase_config import get_firestore_db

db = get_firestore_db()

# Add data
db.collection('inventory').add({
    'name': 'Product Name',
    'quantity': 100,
    'price': 50.00
})

# Get data
items = db.collection('inventory').stream()
for item in items:
    print(item.to_dict())
```

### Realtime Database
```python
from firebase_config import get_realtime_db

ref = get_realtime_db()

# Add data
ref.child('inventory').push({
    'name': 'Product Name',
    'quantity': 100,
    'price': 50.00
})

# Get data
data = ref.child('inventory').get()
```

## 6. Enable Database in Firebase Console

1. Go to **Build** > **Firestore Database** or **Realtime Database**
2. Click **Create Database**
3. Choose production mode or test mode
4. Select your region

## File Structure
```
TLPH_Project/
├── firebase_config.py       # Firebase initialization
├── firebase-credentials.json # Service account key (DO NOT COMMIT)
├── .env                      # Environment variables (DO NOT COMMIT)
├── .env.example              # Example environment variables
└── app.py                    # Now includes Firebase initialization
```
