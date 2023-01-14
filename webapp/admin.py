from flask import Blueprint, render_template, request, jsonify, send_file
from flask import current_app as app
import json
import os
from pathlib import Path
from .metadata.compilation import Compilation, PaperStatus
from .metadata import validate_paperid

"""This has the views for the admin section under /admn. Everything
should be protected with HTTP authentication in apache, but in
development there is no authentication."""

def admin_message(data):
    return app.jinja_env.get_template('admin/message.html').render(data)

admin_bp = Blueprint('admin_file', __name__)

@admin_bp.route('/admin/')
def show_admin_home():
    papers = []
    errors = []
    for f in Path(app.config['DATA_DIR']).glob('**/compilation.json'):
        try:
            comp = Compilation.parse_raw(f.read_text(encoding='UTF-8'))
            papers.append(comp)
        except Exception as e:
            errors.append(str(f) + ':' + str(e))
    data = {'title': 'IACR CC Upload Admin Home',
            'errors': errors,
            'papers': sorted(papers, key=lambda x: x.compiled, reverse=True)}
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

