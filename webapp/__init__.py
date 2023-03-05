"""
This is used to manage the submission of final papers. Authors enter the site via
an authenticated URL with a paper ID from hotcrp. When a paper is submitted, it
receives an upload of a zip file with at least one tex file. We start a docker instance
in a separate task to compile the output.
"""

from collections import OrderedDict
from flask import Flask, request, render_template, current_app
from flask_login import LoginManager, UserMixin
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import hashlib, hmac
import os
from pathlib import Path
import sys

# Make sure we aren't running on an old python.
assert sys.version_info >= (3, 7)

def paper_key(paperid, version):
    return '/'.join((paperid, version))

def get_json_path(paperid, version):
    """Path to a paper version, where compilation.json is located."""
    return Path(current_app.config['DATA_DIR']) / Path(paperid) / Path(version) / Path('compilation.json')
def create_hmac(paperid, version, submitted, accepted):
    """Create hmac used for validating local URLs."""
    return hmac.new(current_app.config['SECRET_KEY'].encode('utf-8'),
                    (paperid+version+submitted+accepted).encode('utf-8'), hashlib.sha256).hexdigest()

def validate_hmac(paperid, version, submitted, accepted, auth):
    """Validate hmac from create_hmac."""
    return hmac.compare_digest(create_hmac(paperid, version, submitted, accepted), auth)

def get_pdf_url(paperid, version):
    return '/view/{}/{}/{}/main.pdf'.format(paperid, version, create_hmac(paperid, version, '', ''))

# Globally accessible SMTP client. This can be used in unit tests as well.
mail = Mail()

# Used to keep track of compilations by paperid. When a task is
# submitted, then the paperid key is added to this with a value of the Future
# that will run the compilation.. When a task is finished it removes the paperid
# from the task_queue. This allows us to keep track of which
# papers are queued for processing so that we don't enqueue a paper
# twice and monitor the status of the queue in the admin interface.
task_queue = OrderedDict()

executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='compiler')

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

# DB used for keeping track of users.
db = SQLAlchemy()

# Now that db exists, we can import User
from webapp.db_models import User

def create_app(config):
    app = Flask('webapp', static_folder='static/', static_url_path='/')
    app.config.from_object(config)
    mail.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    with app.app_context():
        from . import admin
        from . import routes
        from . import auth
        app.register_blueprint(routes.home_bp)
        app.register_blueprint(admin.admin_bp)
        app.register_blueprint(auth.auth_bp)
        db.create_all()
        if config.USERS:
            for user in config.USERS:
                u = User.query.filter_by(email=user['email']).first()
                if not u:
                    db.session.add(User(user['email'],
                                        user['role'],
                                        user['password']))
            db.session.commit()
        return app


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
