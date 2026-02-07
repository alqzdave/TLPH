from flask import Blueprint, render_template, redirect, url_for

bp = Blueprint('service', __name__, url_prefix='/user')

@bp.route('/application')
def application():
    """Shows application page with pending applications"""
    return render_template('user/application.html')

@bp.route('/application/apply')
def application_form():
    """Shows application form"""
    return render_template('user/app-form.html')

@bp.route('/application/submit', methods=['POST'])
def application_submit():
    """Handles application submission and redirects to dashboard"""
    # Add your form processing logic here
    # For now, just redirect back to dashboard
    return redirect('/user/dashboard')
