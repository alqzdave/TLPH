from flask import Blueprint, render_template

bp = Blueprint('livestock', __name__, url_prefix='/user/license/livestock')

@bp.route('/')
def livestock_main():
    return render_template('user/license/livestock/livestock.html')

@bp.route('/animal-transport')
def animal_transport():
    return render_template('user/license/livestock/animal-transport.html')

@bp.route('/meat-transport')
def meat_transport():
    return render_template('user/license/livestock/meat-transport.html')

@bp.route('/slaughterhouse')
def slaughterhouse():
    return render_template('user/license/livestock/slaughterhouse.html')

@bp.route('/poultry-farm')
def poultry_farm():
    return render_template('user/license/livestock/poultry-farm.html')

@bp.route('/animal-health')
def animal_health():
    return render_template('user/license/livestock/animal-health.html')
