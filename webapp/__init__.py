"""
This is used to manage the submission of final papers. Authors enter the site via
an authenticated URL with a paper ID from hotcrp. When a paper is submitted, it
receives an upload of a zip file with at least one tex file. We start a docker instance
in a celery task to compile the output.
"""

from flask import Flask, request, render_template
from flask_mail import Mail
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
from celery import Celery
import os
import sys
from config import Config

# Make sure we aren't running on an old python.
assert sys.version_info >= (3, 7)

# Globally accessible SMTP client. This can be used in unit tests as well.
mail = Mail()
# Globally accessible rate limiter. This is initialized in create_app
#limiter = Limiter(key_func=get_remote_address,
#                  default_limits=[]) # default is no limit
celery = Celery('webapp', broker='redis://:localhost:6379/0')

def create_app(config):
    app = Flask('webapp', static_folder='static/', static_url_path='/')
    app.config.from_object(config)

    mail.init_app(app)
    # limiter.init_app(app)
    celery.conf.update(app.config)
    
    with app.app_context():
        # from admin import admin_routes
        from . import routes
        app.register_blueprint(routes.home_bp)
        return app


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
