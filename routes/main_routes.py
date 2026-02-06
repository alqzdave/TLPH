from flask import Blueprint, render_template, redirect, url_for

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

@bp.route('/farmer/dashboard')
def farmer_dashboard():
    return render_template('farmer_dashboard.html')

@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
