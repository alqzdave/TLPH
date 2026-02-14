from flask import Blueprint, render_template

bp = Blueprint('national', __name__, url_prefix='/national')

@bp.route('/application-national')
def application_national_view():
    return render_template('national/applications-national.html')

@bp.route('/permit-national')
def permit_national_view():
    return render_template('national/licensing-permit-national.html')

@bp.route('/service-national')
def service_national_view():
    return render_template('national/service-national.html')

@bp.route('/inventory-national')
def inventory_national_view():
    return render_template('national/inventory-national.html')

@bp.route('/user-inventory-national')
def user_inventory_national_view():
    return render_template('national/user-inventory-national.html')

@bp.route('/transaction-national')
def transaction_national_view():
    return render_template('national/transaction-national.html')

@bp.route('/user-management-national')
def user_management_national_view():
    return render_template('national/user-national.html')

@bp.route('/profile-national')
def profile_national_view():
    return render_template('national/profile-national.html')