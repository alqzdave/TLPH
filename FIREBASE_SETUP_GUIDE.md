# Firebase Setup Guide for Application Submission

## Issue: Application stuck at "Submitting..."

This happens because Firebase Storage and Firestore security rules need to be configured.

---

## Solution: Update Firebase Rules

### 1. **Firebase Storage Rules**

Go to Firebase Console → Storage → Rules

Replace with:
```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /applications/{userId}/{allPaths=**} {
      // Allow authenticated users to upload their own application files
      allow write: if request.auth != null && request.auth.uid == userId;
      
      // Allow authenticated users to read any application files
      allow read: if request.auth != null;
    }
    
    // Fallback: deny all other access
    match /{allPaths=**} {
      allow read, write: if false;
    }
  }
}
```

**Click "Publish"**

---

### 2. **Firestore Database Rules**

Go to Firebase Console → Firestore Database → Rules

Replace with:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Users collection
    match /users/{userId} {
      // Users can read and write their own data
      allow read, write: if request.auth != null && request.auth.uid == userId;
      
      // Allow read for admin roles
      allow read: if request.auth != null;
    }
    
    // Applications collection
    match /applications/{applicationId} {
      // Allow authenticated users to create applications
      allow create: if request.auth != null && 
                      request.resource.data.userId == request.auth.uid;
      
      // Allow users to read their own applications
      allow read: if request.auth != null && 
                     resource.data.userId == request.auth.uid;
      
      // Allow admin roles to read all applications
      allow read: if request.auth != null;
      
      // Allow admin roles to update status
      allow update: if request.auth != null;
    }
  }
}
```

**Click "Publish"**

---

## 3. **Test the Application**

1. Open browser console (F12)
2. Fill out the application form
3. Click "Apply"
4. Watch the console logs to see progress:
   - "Starting application submission..."
   - "Uploading file 1/7: title"
   - etc.

If you see an error like:
- **`storage/unauthorized`** → Fix Storage rules (Step 1)
- **`permission-denied`** → Fix Firestore rules (Step 2)
- **Network error** → Check internet connection

---

## 4. **Verify Setup**

After updating rules, test:
1. Login as a user
2. Go to `/user/application/apply`
3. Fill form and submit
4. Should see "Application submitted successfully!"
5. Redirect to `/user/application` showing your application

---

## Quick Troubleshooting

**Still stuck?**

1. Check browser console (F12) for error messages
2. Open Firebase Console → Storage → Files → Check if `applications/` folder exists
3. Open Firebase Console → Firestore → Data → Check if `applications` collection has documents
4. Verify you're logged in (check if `currentUser` is defined in console)

**To check if logged in:**
```javascript
// In browser console:
import { auth } from '/static/js/firebase-config.js';
console.log(auth.currentUser);
```

If `null`, you need to login first at `/login`
