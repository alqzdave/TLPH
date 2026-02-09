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

# Landing pages for different roles
@bp.route('/municipal/dashboard')
def municipal_dashboard():
    return render_template('municipal/landing-municipal.html')

@bp.route('/national/dashboard')
def national_dashboard():
    return render_template('national/landing-national.html')

@bp.route('/regional/dashboard')
def regional_dashboard():
    return render_template('regional/landing-regional.html')

@bp.route('/super-admin/dashboard')
def superadmin_dashboard():
    return render_template('super-admin/landing-superadmin.html')

@bp.route('/create-admin')
def create_admin():
    return render_template('create-admin.html')

@bp.route('/create-firebase-admins')
def create_firebase_admins():
    return render_template('create-firebase-admins.html')

@bp.route('/fix-admin-roles')
def fix_admin_roles():
    return render_template('fix-admin-roles.html')

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

@bp.route('/approval-status')
def approval_status():
    return render_template('approval_status.html')


