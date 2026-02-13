from flask import Blueprint, render_template

bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

@bp.route('/inventory')
def inventory_view():
    return render_template('super-admin/inventory-superadmin/inventory-superadmin.html')

@bp.route('/user-application')
def user_application_view():
    return render_template('super-admin/application-superadmin/application-superadmin.html')

@bp.route('/user-service-request')
def user_request_view():
    return render_template('super-admin/service-request-superadmin/service-request-superadmin.html')

@bp.route('/user-inventory')
def user_inventory_view():
    return render_template('super-admin/user-inventory-superadmin/user-inventory-superadmin.html')

@bp.route('/permits')
def permits_view():
    return render_template('super-admin/permits-license-superadmin/permits-license-superadmin.html')

@bp.route('/transaction')
def transaction_permits_view():
    return render_template('super-admin/transaction-permit-superadmin/transaction-permit-superadmin.html')

@bp.route('/account')
def accounts_view():
    return render_template('super-admin/superadmin-account/superadmin-account.html')

@bp.route('/audit-logs')
def audit_logs_view():
    return render_template('super-admin/audit-logs-superadmin/audit-logs-superadmin.html')

@bp.route('/superadmin-profile')
def superadmin_profile():
    return render_template('super-admin/superadmin-profile.html')

@bp.route('/superadmin-notification')
def superadmin_notification():
    return render_template('super-admin/superadmin-notification.html')