from flask import Blueprint, request, jsonify, session
from flask_mail import Message, Mail
import random

bp = Blueprint('api', __name__, url_prefix='/api')

# Store OTPs temporarily (in production, use Redis or database)
otp_storage = {}

# Store users temporarily (in production, use database)
users_db = {
    'municipal@gmail.com': {
        'password': '123456',
        'role': 'municipal',
        'data': {
            'firstName': 'Municipal',
            'lastName': 'Admin',
            'email': 'municipal@gmail.com',
            'phone': '000-000-0000'
        }
    },
    'regional@gmail.com': {
        'password': '123456',
        'role': 'regional',
        'data': {
            'firstName': 'Regional',
            'lastName': 'Admin',
            'email': 'regional@gmail.com',
            'phone': '000-000-0000'
        }
    },
    'superadmin@gmail.com': {
        'password': '123456',
        'role': 'super-admin',
        'data': {
            'firstName': 'Super',
            'lastName': 'Admin',
            'email': 'superadmin@gmail.com',
            'phone': '000-000-0000'
        }
    },
    'national@gmail.com': {
        'password': '123456',
        'role': 'national',
        'data': {
            'firstName': 'National',
            'lastName': 'Admin',
            'email': 'national@gmail.com',
            'phone': '000-000-0000'
        }
    }
}

# Mail instance will be initialized later
mail = None

def init_mail(mail_instance):
    global mail
    mail = mail_instance

@bp.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if mail is configured
        if not mail:
            return jsonify({
                'success': False, 
                'message': 'Email service not configured. Please contact administrator.'
            }), 500
        
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store OTP (expires in 10 minutes)
        otp_storage[email] = otp
        
        # Send email
        msg = Message(
            subject='DENR TLPH - Email Verification Code',
            recipients=[email],
            body=f'''
Dear User,

Your verification code for DENR TLPH registration is: {otp}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
DENR TLPH Team
            '''
        )
        
        mail.send(msg)
        
        return jsonify({'success': True, 'message': 'OTP sent successfully'})
    
    except Exception as e:
        print(f'Error sending OTP: {str(e)}')
        return jsonify({'success': False, 'message': f'Failed to send OTP: {str(e)}'}), 500

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400
        
        # Check if OTP matches
        stored_otp = otp_storage.get(email)
        
        if not stored_otp:
            return jsonify({'success': False, 'message': 'OTP expired or not found'}), 400
        
        if stored_otp == otp:
            # Remove OTP after successful verification
            del otp_storage[email]
            return jsonify({'success': True, 'message': 'OTP verified successfully'})
        else:
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
    except Exception as e:
        print(f'Error verifying OTP: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('applicationType', 'user')  # Default to 'user'
        
        # Map application types to roles
        role_mapping = {
            'tenant': 'user',
            'cooperative': 'user',
            'agribusiness': 'user',
            'research': 'user',
            'municipal': 'municipal',
            'national': 'national',
            'regional': 'regional',
            'super-admin': 'super-admin'
        }
        
        user_role = role_mapping.get(role, 'user')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        # Check if user already exists
        if email in users_db:
            return jsonify({'success': False, 'message': 'User already exists'}), 400
        
        # Store user (in production, hash password and use database)
        users_db[email] = {
            'password': password,
            'role': user_role,
            'data': data
        }
        
        return jsonify({'success': True, 'message': 'Registration successful', 'role': user_role})
    
    except Exception as e:
        print(f'Error registering user: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        # Check if user exists
        user = users_db.get(email)
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Verify password (in production, use proper password hashing)
        if user['password'] != password:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Set session
        session['user_email'] = email
        session['user_role'] = user['role']
        
        # Determine redirect URL based on role
        redirect_urls = {
            'user': '/user/dashboard',
            'municipal': '/municipal/dashboard',
            'national': '/national/dashboard',
            'regional': '/regional/dashboard',
            'super-admin': '/super-admin/dashboard'
        }
        
        redirect_url = redirect_urls.get(user['role'], '/user/dashboard')
        
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'role': user['role'],
            'redirect': redirect_url
        })
    
    except Exception as e:
        print(f'Error logging in: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500
