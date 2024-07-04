import datetime
from io import BytesIO
from flask import Blueprint, render_template, request, url_for, jsonify
from flask import current_app as app
from .index.search_lib import search

search_bp = Blueprint('search_bp',
                      __name__,
                      template_folder='templates',
                      static_folder='static')

def _get_dbpath(args):
    """Construct the database path from the arguments."""
    dbname = args.get('c', 'default')
    if dbname in app.config['XAPIAN_PATHS']:
        return app.config['XAPIAN_PATHS'][dbname]
    return app.config['XAPIAN_PATHS']['default']

@search_bp.route('/search', methods=['GET'])
def get_results():
    args = request.args.to_dict()
    if 'textq' not in args and 'locationq' not in args:
        response = jsonify({'error': 'missing queries'})
    else:
        db_path = _get_dbpath(args)
        response = jsonify(search(db_path,
                                  offset=args.get('offset', 0),
                                  textq=args.get('textq'),
                                  locationq=args.get('locationq'),
                                  source=args.get('source'),
                                  app=app))
    response.headers.add('Access-Control-Allow-Origin', '*');
    return response
