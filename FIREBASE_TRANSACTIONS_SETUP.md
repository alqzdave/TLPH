# Firebase Firestore Transaction Storage Setup

## Overview
Transactions are now stored in **Firebase Firestore** instead of local JSON files. This provides:
- Real-time synchronization
- Scalability
- Better security
- Cloud backup

## Setup Instructions

### 1. Firebase Console Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **denr-d02ae**
3. Navigate to **Firestore Database** (in the left sidebar)
4. Click **Create database** (if not already created)
   - Choose **Production mode** or **Test mode** (Test mode for development)
   - Select your closest region
5. Click **Enable**

### 2. Download Service Account Key

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Click on **Service accounts** tab
3. Click **Generate new private key**
4. Save the downloaded JSON file as `firebase-credentials.json` in your project root:
   ```
   C:\Users\LENOVO\Downloads\project\jabb\TLPH\firebase-credentials.json
   ```

### 3. Verify .env Configuration

Make sure your `.env` file has the Firebase configuration:

```env
FIREBASE_API_KEY=AIzaSyCj3EnEG1XhF7_xWgt1vQK_VkT7288yd64
FIREBASE_AUTH_DOMAIN=denr-d02ae.firebaseapp.com
FIREBASE_DATABASE_URL=https://denr-d02ae-default-rtdb.firebaseio.com
FIREBASE_PROJECT_ID=denr-d02ae
FIREBASE_STORAGE_BUCKET=denr-d02ae.appspot.com
FIREBASE_MESSAGING_SENDER_ID=499245517370
FIREBASE_APP_ID=1:499245517370:web:c66598d7c86d5567a64303
FIREBASE_CREDENTIALS=firebase-credentials.json
```

### 4. Firestore Security Rules (Optional but Recommended)

In Firebase Console → Firestore Database → Rules, set:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /transactions/{transactionId} {
      // Allow read/write only for authenticated users
      allow read, write: if request.auth != null;
      
      // Or for development (not recommended for production):
      // allow read, write: if true;
    }
  }
}
```

### 5. Run the Application

```powershell
py app.py
```

## Firestore Collection Structure

**Collection Name:** `transactions`

**Document Fields:**
- `user_email` (string): Email of the user who created the transaction
- `external_id` (string): Unique external reference ID
- `invoice_id` (string): Xendit invoice ID
- `transaction_name` (string): Name/type of the license application
- `description` (string): Detailed description
- `amount` (number): Payment amount in PHP
- `status` (string): "Pending", "Approved", "Rejected", or "Cancelled"
- `payment_method` (string): Payment method used
- `reference` (string): Reference number
- `created_at` (timestamp): Auto-generated server timestamp
- `updated_at` (timestamp): Auto-generated server timestamp
- `paid_at` (timestamp | null): Payment completion timestamp

## Troubleshooting

### Error: "Could not find firebase-credentials.json"
- Make sure you downloaded the service account key from Firebase Console
- Verify the file is named exactly `firebase-credentials.json`
- Check it's in the project root directory

### Error: "Permission denied"
- Update Firestore security rules to allow read/write access
- For development, temporarily set rules to allow all access

### Error: "Failed to initialize Firebase Admin"
- Check that `FIREBASE_PROJECT_ID` matches your actual Firebase project ID
- Verify the service account key is valid and not expired

## Migration from JSON to Firestore

If you have existing transactions in `data/transactions.json`, they will no longer be used. The old JSON file is kept for backup but won't be updated.

To migrate old data (if needed):
1. Keep the old `data/transactions.json` for reference
2. New transactions will automatically go to Firestore
3. Old transactions can be manually imported if necessary

## Testing

After setup, test the transaction system:
1. Apply for a license/permit
2. View **Transactions** page
3. Check Firebase Console → Firestore Database to see the new transaction document
4. Try canceling a pending transaction
5. Verify the status updates in Firestore

## Security Notes

- **NEVER commit `firebase-credentials.json` to Git** (already in .gitignore)
- Keep your service account key secure
- Use environment variables for sensitive data
- Enable Firestore security rules in production
