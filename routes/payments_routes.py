from flask import Blueprint, request, jsonify, render_template
from config import Config
import requests
from datetime import datetime
import base64
import transaction_storage

bp = Blueprint('payments', __name__, url_prefix='/api/payments')

# Xendit API Base URL
XENDIT_BASE_URL = 'https://api.xendit.co'

def get_xendit_auth_header():
    """Generate Xendit API authentication header"""
    if not Config.XENDIT_API_KEY:
        return None
    api_key_bytes = (Config.XENDIT_API_KEY + ':').encode('utf-8')
    encoded = base64.b64encode(api_key_bytes).decode('utf-8')
    return f'Basic {encoded}'

@bp.route('/create-invoice', methods=['POST'])
def create_invoice():
    """Create a Xendit invoice for license/permit payments"""
    try:
        data = request.get_json(silent=True) or {}
        auth_header = get_xendit_auth_header()
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Xendit API key not configured'
            }), 400
        
        # Basic payload validation before calling Xendit
        raw_amount = data.get('amount')
        try:
            amount = int(raw_amount)
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:
            return jsonify({
                'status': 'error',
                'message': 'Amount must be greater than 0'
            }), 400

        email = (data.get('email') or '').strip()
        if email and '@' not in email:
            return jsonify({
                'status': 'error',
                'message': 'Invalid payer email'
            }), 400

        # Invoice parameters for Xendit API
        external_id = f"{data.get('external_id', 'invoice')}-{int(datetime.now().timestamp())}"
        
        invoice_payload = {
            'external_id': external_id,
            'amount': amount,
            'description': data.get('description', 'DENR License/Permit Payment'),
            'success_redirect_url': data.get('success_url', 'http://localhost:5000/payment-success'),
            'failure_redirect_url': data.get('failure_url', 'http://localhost:5000/payment-failed'),
            'items': [
                {
                    'name': data.get('item_name', 'License/Permit'),
                    'quantity': 1,
                    'price': amount
                }
            ]
        }

        if email:
            invoice_payload['payer_email'] = email
        
        # Add customer info if provided
        # Only include customer if we have at least one field
        customer = {}
        if data.get('first_name'):
            customer['given_names'] = data.get('first_name')
        if data.get('last_name'):
            customer['surname'] = data.get('last_name')
        if email:
            customer['email'] = email
        if data.get('phone'):
            customer['mobile_number'] = data.get('phone')
        
        if customer:
            invoice_payload['customer'] = customer
        
        # Create invoice via Xendit API
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{XENDIT_BASE_URL}/v2/invoices',
            json=invoice_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            invoice = response.json()
            
            # Save transaction record
            transaction_storage.add_transaction(
                user_email=email,
                external_id=external_id,
                invoice_id=invoice.get('id'),
                amount=amount,
                item_name=data.get('item_name', 'License/Permit'),
                description=data.get('description', 'DENR License/Permit Payment'),
                status='Pending'
            )
            
            return jsonify({
                'status': 'success',
                'invoice_id': invoice.get('id'),
                'invoice_url': invoice.get('invoice_url'),
                'amount': invoice.get('amount'),
                'external_id': invoice.get('external_id')
            }), 201
        else:
            try:
                error_body = response.json()
            except ValueError:
                error_body = {'raw': response.text}
            return jsonify({
                'status': 'error',
                'message': f"Xendit API error: {response.status_code}",
                'details': error_body
            }), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': f'Request failed: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@bp.route('/check-invoice/<invoice_id>', methods=['GET'])
def check_invoice_status(invoice_id):
    """Check the status of a Xendit invoice"""
    try:
        auth_header = get_xendit_auth_header()
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Xendit API key not configured'
            }), 400
        
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'{XENDIT_BASE_URL}/v2/invoices/{invoice_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            invoice = response.json()
            return jsonify({
                'status': 'success',
                'invoice_id': invoice.get('id'),
                'amount': invoice.get('amount'),
                'paid_amount': invoice.get('paid_amount', 0),
                'payment_status': invoice.get('status'),
                'paid_at': invoice.get('paid_at'),
                'payment_method': invoice.get('payment_method')
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Invoice not found or error: {response.status_code}'
            }), response.status_code
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@bp.route('/webhook', methods=['POST'])
def xendit_webhook():
    """Handle Xendit webhook notifications"""
    try:
        data = request.json
        
        # Validate webhook signature (optional but recommended)
        # You should verify the signature using Xendit's verification process
        
        invoice_id = data.get('id')
        status = data.get('status')
        payment_method = data.get('payment_method')
        paid_at = data.get('paid_at')
        
        # Update transaction status
        if invoice_id:
            transaction_storage.update_transaction_status(
                invoice_id=invoice_id,
                status=status,
                payment_method=payment_method,
                paid_at=paid_at
            )
        
        if status == 'PAID':
            # Process successful payment
            external_id = data.get('external_id')
            amount = data.get('amount')
            
            # Additional processing can be done here
            # Example: send email confirmation, update license status, etc.
            
            return jsonify({
                'status': 'success',
                'message': 'Webhook processed'
            }), 200
        
        return jsonify({
            'status': 'success',
            'message': 'Webhook received'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@bp.route('/payment-form/<service_type>', methods=['GET'])
def payment_form(service_type):
    """Display payment form for different service types"""
    return render_template('payment-form.html', 
                         service_type=service_type,
                         xendit_public_key=Config.XENDIT_PUBLIC_KEY)


@bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Get transactions for the logged-in user"""
    try:
        # Get user email from query parameter (sent from frontend)
        user_email = request.args.get('email')
        
        if not user_email:
            return jsonify({
                'status': 'error',
                'message': 'User email is required'
            }), 400
        
        transactions = transaction_storage.get_user_transactions(user_email)
        
        # Convert status to display format
        for transaction in transactions:
            status = transaction.get('status', 'Pending')
            if status == 'Approved' or status == 'PAID':
                transaction['display_status'] = 'approved'
            elif status == 'Rejected' or status == 'EXPIRED' or status == 'FAILED':
                transaction['display_status'] = 'rejected'
            else:
                transaction['display_status'] = 'pending'
        
        return jsonify({
            'status': 'success',
            'transactions': transactions
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

