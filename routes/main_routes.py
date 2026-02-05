from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/inventory')
def inventory():
    return render_template('inventory.html')

@bp.route('/about')
def about():
    return render_template('about.html')
