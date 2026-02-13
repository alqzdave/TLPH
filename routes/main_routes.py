from flask import Blueprint, render_template, redirect, url_for, session

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    print("HOME.HTML IS BEING RENDERED")  # Debug line
    return render_template('home.html')

@bp.route('/login')
def login():
    return render_template('login.html')

@bp.route('/register')
def register():
    return render_template('signup.html')

@bp.route('/create-municipal-admin')
def create_municipal_admin():
    return render_template('create-municipal-admin.html')

# Landing pages for different roles
@bp.route('/national/dashboard')
def national_dashboard():
    return render_template('national/landing-national.html')

@bp.route('/regional/dashboard')
def regional_dashboard():
    return render_template('regional/landing-regional.html')

@bp.route('/super-admin/dashboard')
def superadmin_dashboard():
    return render_template('super-admin/landing-superadmin.html')

@bp.route('/farmer/dashboard')
def farmer_dashboard():
    return render_template('farmer_dashboard.html')

@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@bp.route('/user/dashboard')
def user_dashboard():
    return render_template('user/dashboard.html')

@bp.route('/user/profile')
def user_profile():
    return render_template('user/profile.html')

@bp.route('/user/transaction')
def user_transaction():
    return render_template('user/transaction.html')

@bp.route('/user/my-documents')
def user_my_documents():
    return render_template('user/my-documents.html')

@bp.route('/user/transaction-history')
def user_transaction_history():
    return render_template('user/transaction-history.html')

@bp.route('/user/history')
def user_history():
    return render_template('user/history.html')

@bp.route('/user/application')
def user_application():
    return render_template('user/application.html')

@bp.route('/user/application/apply')
def user_application_apply():
    return render_template('user/app-form.html')

@bp.route('/approval-status')
def approval_status():
    return render_template('approval_status.html')

@bp.route('/payment-success')
def payment_success():
    return render_template('payment-success.html')

@bp.route('/payment-failed')
def payment_failed():
    return render_template('payment-failed.html')

# Inventory routes
@bp.route('/user/inventory')
def user_inventory():
    return render_template('user/inventory/stock-list.html')

@bp.route('/user/inventory/add')
def user_inventory_add():
    return render_template('user/inventory/stock-form.html')

@bp.route('/user/inventory/info/<stock_id>')
def user_inventory_info(stock_id):
    return render_template('user/inventory/stock-info.html')

@bp.route('/user/inventory/history')
def user_inventory_history():
    return render_template('user/inventory/stock-history.html')
