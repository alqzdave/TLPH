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

@bp.route('/service/service')
def service_request():
    """Shows service request page"""
    return render_template('user/service/service.html')


@bp.route('/compensation/typhoon')
def compensation_typhoon():
    """Shows typhoon compensation page"""
    return render_template('user/service/compensation/typhoon.html')

@bp.route('/compensation/pest')
def compensation_pest():
    """Shows pest compensation page"""
    return render_template('user/service/compensation/pest.html')

@bp.route('/inventory')
def inventory():
    """Shows inventory page"""
    return render_template('user/inventory/stock-list.html')

@bp.route('/license/license')
def license_request():
    """Shows license/permit request page"""
    return render_template('user/license/license.html')

@bp.route('/service/farm')
def service_farm():
    """Shows farm visit service page"""
    return render_template('user/service/farm/farm.html')

@bp.route('/service/fertilizer')
def service_fertilizer():
    """Shows fertilizer/pesticide service page"""
    return render_template('user/service/fertilizer/fertilizer.html')

@bp.route('/service/financial')
def service_financial():
    """Shows financial assistance service page"""
    return render_template('user/service/financial/financial.html')

@bp.route('/service/fertilizer/fertilizer')
def service_fertilizer_page():
    """Alias route for fertilizer page"""
    return render_template('user/service/fertilizer/fertilizer.html')

@bp.route('/service/fertilizer/input-usage')
def service_fertilizer_input_usage():
    """Shows input usage approval page"""
    return render_template('user/service/fertilizer/input_usage.html')

@bp.route('/service/fertilizer/chemical-registration')
def service_fertilizer_chemical_registration():
    """Shows chemical registration/clearance page"""
    return render_template('user/service/fertilizer/chemical_registration.html')

@bp.route('/service/fertilizer/emergency-post-control')
def service_fertilizer_emergency_post_control():
    """Shows emergency post control request page"""
    return render_template('user/service/fertilizer/emergency_post_control.html')

@bp.route('/service/fertilizer/fertilizer-recommendation')
def service_fertilizer_recommendation():
    """Shows fertilizer recommendation page"""
    return render_template('user/service/fertilizer/fertilizer_recommendation.html')

@bp.route('/service/fertilizer/pesticide-recommendation')
def service_fertilizer_pesticide_recommendation():
    """Shows pesticide recommendation page"""
    return render_template('user/service/fertilizer/pesticide_recommendation.html')

@bp.route('/service/financial/financial')
def service_financial_page():
    """Alias route for financial page"""
    return render_template('user/service/financial/financial.html')

@bp.route('/service/financial/subsidy')
def service_financial_subsidy():
    """Shows subsidy application page"""
    return render_template('user/service/financial/subsidy.html')

@bp.route('/service/financial/grant')
def service_financial_grant():
    """Shows grant assistance page"""
    return render_template('user/service/financial/grant.html')

@bp.route('/service/financial/loan')
def service_financial_loan():
    """Shows loan endorsement page"""
    return render_template('user/service/financial/loan.html')

@bp.route('/service/financial/crop')
def service_financial_crop():
    """Shows crop insurance support page"""
    return render_template('user/service/financial/crop.html')

@bp.route('/service/financial/startup')
def service_financial_startup():
    """Shows startup/expansion support page"""
    return render_template('user/service/financial/startup.html')

@bp.route('/license/fisheries')
def license_fisheries():
    """Shows fisheries license page"""
    return render_template('user/license/fisheries/fisheries.html')

@bp.route('/license/wildlife')
def license_wildlife():
    """Shows wildlife license page"""
    return render_template('user/license/wildlife/wildlife.html')

@bp.route('/license/livestock')
def license_livestock():
    """Shows livestock license page"""
    return render_template('user/license/livestock/livestock.html')

@bp.route('/license/environment')
def license_environment():
    """Shows environment clearance page"""
    return render_template('user/license/environment/environment.html')

@bp.route('/license/forest')
def license_forest():
    """Shows forest license page"""
    return render_template('user/license/forest/forest.html')

@bp.route('/license/permits')
def license_permits():
    """Shows other permits page"""
    return render_template('user/license/permits/permits.html')
@bp.route('/inventory/stock-history')
def inventory_stock_history():
    """Shows inventory stock history page"""
    return render_template('user/inventory/stock-history.html')

@bp.route('/inventory/stock-info')
def inventory_stock_info():
    """Shows inventory stock info page"""
    return render_template('user/inventory/stock-info.html')