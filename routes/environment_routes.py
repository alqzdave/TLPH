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

@bp.route('/cco')
def cco():
    return render_template('user/license/environment/cco.html')

@bp.route('/hazardous-waste')
def hazardous_waste():
    return render_template('user/license/environment/hazardous-waste-generator.html')

@bp.route('pcl')
def pcl():
    return render_template('user/license/environment/pcl.html')

@bp.route('permit-to-operate-air')
def permit_to_operate_air():
    return render_template('user/license/environment/permit-to-operate-air.html')

@bp.route('piccs')
def piccs():
    return render_template('user/license/environment/piccs.html')

@bp.route('water-dispose')
def water_dispose():
    return render_template('user/license/environment/water-dispose.html')