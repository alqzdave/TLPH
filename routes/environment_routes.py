from flask import Blueprint, render_template

bp = Blueprint('environment', __name__, url_prefix='/user/license/environment')

@bp.route('/')
def environment_main():
    return render_template('user/license/environment/environment.html')

@bp.route('/ecc')
def environment_clearance():
    return render_template('user/license/environment/environment-clearance.html')

@bp.route('/waste')
def waste_management():
    return render_template('user/license/environment/waste.html')

@bp.route('/water')
def water_use():
    return render_template('user/license/environment/water-use.html')

@bp.route('/hazardous')
def hazardous_material():
    return render_template('user/license/environment/hazardous.html')
