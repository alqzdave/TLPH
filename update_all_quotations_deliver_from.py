# Script to update all quotations' deliver_from field to 'NATIONAL'
from firebase_config import get_firestore_db

def update_all_quotations_deliver_from_to_national():
    db = get_firestore_db()
    quotations = db.collection('quotations').stream()
    count = 0
    for doc in quotations:
        ref = doc.reference
        ref.update({'deliver_from': 'NATIONAL'})
        count += 1
    print(f"Updated {count} quotations to deliver_from='NATIONAL'.")

if __name__ == "__main__":
    update_all_quotations_deliver_from_to_national()
