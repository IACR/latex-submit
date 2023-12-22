import datetime
from io import BytesIO
from flask import Blueprint, render_template, request, url_for, jsonify
from flask import current_app as app
from .index.search_lib import search

search_bp = Blueprint('search_bp',
                      __name__,
                      template_folder='templates',
                      static_folder='static')

@app.context_processor
def inject_variables():
    return {'site_name': app.config['SITE_NAME'],
            'site_shortname': app.config['SITE_SHORTNAME']}

@search_bp.route('/')
def show_funding():
    return render_template('funding.html', title='Funding and affiliation data')

@search_bp.route('/view/<id>')
def view_funder(id):
    result = search(app.config['XAPIAN_DB_PATH'],
                    offset=0,
                    textq='id:' + id,
                    locationq=None,
                    app=app)
    if len(result.get('results')) > 0:
        result = {'item': result.get('results')[0]}
    else:
        result = {'error': 'no such item'}
    return render_template('funding.html', **result)

@search_bp.route('/search', methods=['GET'])
def get_results():
    args = request.args.to_dict()
    if 'textq' not in args and 'locationq' not in args:
        return jsonify({'error': 'missing queries'})
    return jsonify(search(app.config['XAPIAN_DB_PATH'],
                          offset=args.get('offset', 0),
                          textq=args.get('textq'),
                          locationq=args.get('locationq'),
                          source=args.get('source'),
                          app=app))
