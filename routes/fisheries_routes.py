from flask import Blueprint, render_template

bp = Blueprint('fisheries', __name__, url_prefix='/user/license/fisheries')

@bp.route('/')
def fisheries_main():
    return render_template('user/license/fisheries/fisheries.html')

@bp.route('/aquafarm')
def aquafarm():
    return render_template('user/license/fisheries/aquafarm.html')

@bp.route('/transport')
def transport():
    return render_template('user/license/fisheries/transport.html')

@bp.route('/dealer')
def fish_dealer():
    return render_template('user/license/fisheries/fish-dealer.html')

@bp.route('/processing')
def processing():
    return render_template('user/license/fisheries/fish-process.html')

@bp.route('/harvest')
def harvest():
    return render_template('user/license/fisheries/harvest.html')
