from flask import Blueprint, render_template

bp = Blueprint('regional', __name__, url_prefix='/regional')

@bp.route('/profile')
def profile_view():
    return render_template('regional/profile.html')

@bp.route('/application-list')
def application_list_view():
    return render_template('regional/application-regional-list.html')

@bp.route('/service-list')
def service_list_view():
    return render_template('regional/service-regional-list.html')

@bp.route('/service-view')
def service_info_view():
    return render_template('regional/service-regional-view.html')

@bp.route('/inventory-view')
def inventory_view():
    return render_template('regional/inventory-regional-list.html')

@bp.route('/license-view')
def license_view():
    return render_template('regional/license-regional-list.html')

@bp.route('/transaction-view')
def transaction_view():
    return render_template('regional/transaction-regional-list.html')

@bp.route('/municipal-account-management-view')
def municipal_account_management_view():
    return render_template('regional/user-management-regional-list.html')

@bp.route('/audit-logs-view')
def audit_logs_view():
    return render_template('regional/audit-logs-regional-view.html')