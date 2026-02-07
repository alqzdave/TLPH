from flask import Blueprint, render_template

bp = Blueprint('farm', __name__, url_prefix='/user/service/farm')

@bp.route('/')
def farm_main():
    return render_template('user/service/farm/farm.html')

@bp.route('/initial-visit')
def initial_visit():
    return render_template('user/service/farm/initial_visit.html')

@bp.route('/compliance')
def compliance():
    return render_template('user/service/farm/compliance.html')

@bp.route('/disease')
def disease():
    return render_template('user/service/farm/disease.html')

@bp.route('/soil')
def soil():
    return render_template('user/service/farm/soil.html')

@bp.route('/visit')
def visit():
    return render_template('user/service/farm/visit.html')
