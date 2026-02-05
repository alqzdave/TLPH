from flask import Blueprint, render_template, redirect, url_for

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

@bp.route('/login')
def login():
    return render_template('login.html')

@bp.route('/register')
def signup():
    return render_template('signup.html')

@bp.route('/farmer/dashboard')
def farmer_dashboard():
    return render_template('farmer_dashboard.html')
