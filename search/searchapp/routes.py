import datetime
from io import BytesIO
from flask import Blueprint, render_template, request, url_for, jsonify
from flask import current_app as app
from .index.search_lib import search

search_bp = Blueprint('search_bp',
                      __name__,
                      template_folder='templates',
                      static_folder='static')

@search_bp.route('/search', methods=['GET'])
def get_results():
    args = request.args.to_dict()
    if 'textq' not in args and 'locationq' not in args:
        response = jsonify({'error': 'missing queries'})
    else:
        response = jsonify(search(app.config['XAPIAN_DB_PATH'],
                                  offset=args.get('offset', 0),
                                  textq=args.get('textq'),
                                  locationq=args.get('locationq'),
                                  source=args.get('source'),
                                  app=app))
    response.headers.add('Access-Control-Allow-Origin', '*');
    return response
