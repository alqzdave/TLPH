from flask import Blueprint, render_template

bp = Blueprint('wildlife', __name__, url_prefix='/user/license/wildlife')

@bp.route('/')
def wildlife_main():
    return render_template('user/license/wildlife/wildlife.html')

@bp.route('/ownership')
def ownership():
    return render_template('user/license/wildlife/ownership.html')

@bp.route('/transport')
def transport():
    return render_template('user/license/wildlife/transport.html')

@bp.route('/collection')
def collection():
    return render_template('user/license/wildlife/collection.html')

@bp.route('/wildfarm')
def wildfarm():
    return render_template('user/license/wildlife/wildfarm.html')
