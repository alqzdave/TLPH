from flask import Blueprint, render_template

bp = Blueprint('forest', __name__, url_prefix='/user/license/forest')

@bp.route('/')
def forest_main():
    return render_template('user/license/forest/forest.html')

@bp.route('/tree-cutting')
def tree_cutting():
    return render_template('user/license/forest/tree.html')

@bp.route('/timber')
def timber():
    return render_template('user/license/forest/timber.html')

@bp.route('/reforestation')
def reforestation():
    return render_template('user/license/forest/reforestation.html')

@bp.route('/nursery')
def nursery():
    return render_template('user/license/forest/nursery.html')

@bp.route('/non-timber')
def non_timber():
    return render_template('user/license/forest/non-timber.html')
