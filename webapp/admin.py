from flask import Blueprint, render_template, request, jsonify, send_file
from flask import current_app as app
import json
import os
from pathlib import Path
from .metadata.compilation import Compilation, PaperStatus
from .metadata import validate_paperid, validate_version

"""This has the views for the admin section under /admn. Everything
should be protected with HTTP authentication in apache, but in
development there is no authentication."""

def admin_message(data):
    return app.jinja_env.get_template('admin/message.html').render(data)

admin_bp = Blueprint('admin_file', __name__)

@admin_bp.route('/admin/')
def show_admin_home():
    papertree = {} # paperid -> version -> compilation
    errors = []
    for paperpath in Path(app.config['DATA_DIR']).iterdir():
        versions = {}
        for v in paperpath.iterdir():
            if v.is_dir() and validate_version(v.name):
                try:
                    cstr = (v / Path('compilation.json')).read_text(encoding='UTF-8')
                    versions[v.name] = Compilation.parse_raw(cstr)
                except Exception as e:
                    errors.append(str(v) + ':' + str(e))
        papertree[paperpath.name] = versions
    data = {'title': 'IACR CC Upload Admin Home',
            'errors': errors,
            'papers': papertree}
    return render_template('admin/home.html', **data)

@admin_bp.route('/admin/view/<paperid>')
def show_admin_paper(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    status_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path('status.json')
    if not status_path.is_file():
        return admin_message('Unknown paper: {}'.format(paperid))
    try:
        status = PaperStatus.parse_raw(status_path.read_text(encoding='UTF-8'))
    except Exception as e:
        return admin_message('Unable to parse status:{}'.format(str(status_path)))
    data = {'title': 'Viewing {}'.format(paperid),
            'paper': status}
    return render_template('admin/view.html', **data)

