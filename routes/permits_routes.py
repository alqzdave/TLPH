from flask import Blueprint, render_template

bp = Blueprint('permits', __name__, url_prefix='/user/license/permits')

@bp.route('/')
def permits_main():
    return render_template('user/license/permits/permits.html')

@bp.route('/export')
def export_permit():
    return render_template('user/license/permits/export.html')

@bp.route('/operation')
def operation_permit():
    return render_template('user/license/permits/operation-permit.html')

@bp.route('/import')
def import_permit():
    return render_template('user/license/permits/import.html')

@bp.route('/wildlife')
def wildlife_trade():
    return render_template('user/license/permits/wildlife.html')

@bp.route('/local-transport')
def local_transport():
    return render_template('user/license/permits/local-transport.html')

@bp.route('/harvest')
def harvest_permit():
    return render_template('user/license/permits/harvest.html')
