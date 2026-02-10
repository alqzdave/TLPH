import json
import os
from datetime import datetime
from pathlib import Path

TRANSACTIONS_FILE = Path(__file__).parent / 'data' / 'transactions.json'

def ensure_data_directory():
    """Ensure data directory exists"""
    TRANSACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TRANSACTIONS_FILE.exists():
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump([], f)

def load_transactions():
    """Load all transactions from JSON file"""
    ensure_data_directory()
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_transactions(transactions):
    """Save transactions to JSON file"""
    ensure_data_directory()
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(transactions, f, indent=2)

def add_transaction(user_email, external_id, invoice_id, amount, item_name, description, status='PENDING'):
    """Add a new transaction record"""
    transactions = load_transactions()
    
    transaction = {
        'id': len(transactions) + 1,
        'user_email': user_email or 'guest@denr.gov.ph',
        'external_id': external_id,
        'invoice_id': invoice_id,
        'transaction_name': item_name,
        'description': description,
        'amount': amount,
        'status': status,
        'payment_method': None,
        'reference': external_id,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'paid_at': None
    }
    
    transactions.append(transaction)
    save_transactions(transactions)
    return transaction

def update_transaction_status(invoice_id, status, payment_method=None, paid_at=None):
    """Update transaction status when webhook is received"""
    transactions = load_transactions()
    
    for transaction in transactions:
        if transaction.get('invoice_id') == invoice_id:
            transaction['status'] = status
            transaction['updated_at'] = datetime.now().isoformat()
            if payment_method:
                transaction['payment_method'] = payment_method
            if paid_at:
                transaction['paid_at'] = paid_at
            elif status == 'PAID':
                transaction['paid_at'] = datetime.now().isoformat()
            
            save_transactions(transactions)
            return transaction
    
    return None

def get_user_transactions(user_email):
    """Get all transactions for a specific user"""
    transactions = load_transactions()
    return [t for t in transactions if t.get('user_email') == user_email]

def get_all_transactions():
    """Get all transactions"""
    return load_transactions()

def find_transaction_by_external_id(external_id):
    """Find a transaction by external_id"""
    transactions = load_transactions()
    for transaction in transactions:
        if transaction.get('external_id') == external_id:
            return transaction
    return None
