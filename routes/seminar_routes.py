from flask import Blueprint, render_template

bp = Blueprint('seminar', __name__, url_prefix='/user/seminar')

@bp.route('/')
def seminar_list():
    return render_template('user/Seminar/seminar_list.html')

@bp.route('/gap/apply')
def gap_application():
    return render_template('user/Seminar/gap_application.html')

@bp.route('/pest-disease/apply')
def pest_disease_application():
    return render_template('user/Seminar/pest_disease_application.html')

@bp.route('/pesticide/apply')
def pesticide_application():
    return render_template('user/Seminar/pesticide_application.html')

@bp.route('/nursery/apply')
def nursery_application():
    return render_template('user/Seminar/nursery_application.html')

@bp.route('/regulatory/apply')
def regulatory_application():
    return render_template('user/Seminar/regulatory_application.html')
