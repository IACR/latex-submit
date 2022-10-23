from flask import Blueprint, render_template, request, jsonify, send_file
from flask import current_app as app
import json
import os
from pathlib import Path

"""This has the views for the admin section under /admn. Everything is
protected with HTTP authentication in apache, but in development there is
no authentication."""

def admin_message(data):
    return app.jinja_env.get_template('admin/message.html').render(data)

admin_bp = Blueprint('admin_file', __name__)

@admin_bp.route('/admin')
def show_admin_home():
    papers = []
    data = {'title': 'IACR CC Upload Admin Home', 'errors': []}
    for f in Path(app.config['DATA_DIR']).glob('**/meta.json'):
        try:
            jdata = json.loads(f.read_text(encoding='UTF-8'))
            papers.append({'id': jdata['paperid'],
                           'date': jdata['date'][:19],
                           'execution_time': jdata['execution_time'],
                           'code': jdata['code']})
        except Exception as e:
            data['errors'].append(str(f) + ':' + str(e))
    print(json.dumps(papers,indent=2))
    data['papers'] = sorted(papers, key=lambda x: x['date'], reverse=True)
    print(json.dumps(data,indent=2))
    return render_template('admin/home.html', **data)
    
