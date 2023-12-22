"""
This is used to manage the submission of final papers. Authors enter the site via
an authenticated URL with a paper ID from hotcrp. When a paper is submitted, it
receives an upload of a zip file with at least one tex file. We start a docker instance
in a separate task to compile the output.
"""

from flask import Flask, request, render_template, current_app

def create_app(config):
    app = Flask('searchapp', static_folder=config.STATIC_FOLDER, static_url_path='/')
    app.config.from_object(config)
    with app.app_context():
        from . import routes
        app.register_blueprint(routes.search_bp, url_prefix=app.config['APPLICATION_ROOT'])
        return app
