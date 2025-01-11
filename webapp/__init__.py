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
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import hashlib, hmac
import os
from pathlib import Path
import secrets
import string
import sys
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors import pool
from apscheduler.triggers.interval import IntervalTrigger

# Make sure we aren't running on an old python.
assert sys.version_info >= (3, 7)

def paper_key(paperid, version):
    return '/'.join((paperid, version))

def get_json_path(paperid, version):
    """Path to a paper version, where compilation.json is located."""
    return Path(current_app.config['DATA_DIR']) / Path(paperid) / Path(version) / Path('compilation.json')

def create_hmac(args: list[str], key=None):
    """Create hmac used for validating local URLs."""
    if not key:
        key = current_app.config['HOTCRP_POST_KEY'].encode('utf-8')
    return hmac.new(key, (''.join(args)).encode('utf-8'), hashlib.sha256).hexdigest()

def validate_hmac(args: list[str], auth):
    """Validate hmac from create_hmac."""
    return hmac.compare_digest(create_hmac(args), auth)

def get_pdf_url(paperid, version):
    return '/view/{}/{}/{}/main.pdf'.format(paperid, version, create_hmac([paperid, version]))

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

class Scheduler(BackgroundScheduler):
    """A simple wrapper around apscheduler. Much simpler than flask_apscheduler."""
    def init_app(self, app):
        self.app = app

class SQLAlchemy():
    """Wrapper for sqlalchemy scoped_session and engine, like flask-sqlalchemy."""
    def __init__(self, engine, session):
        self.engine = engine
        self.session = session

# DB wrapper is global so we can have easy access to engine and session.
db = SQLAlchemy(None, None)
# scheduler is only used to clean up old jobs in case it has config.DEMO_INSTANCE set to tru
scheduler = Scheduler(executors={'default': pool.ThreadPoolExecutor(1)},
                      timezone='America/Los_Angeles')

# In case we want to try to force the pragma for sqlite3.
# @event.listens_for(Engine, 'connect')
# def set_sqlite_pragma(conn, record):
#     """This can be used to enable cascade deletes automatically."""
#     print('connected')
#     cursor = conn.cursor()
#     cursor.execute('PRAGMA foreign_keys=ON')
#     cursor.close

def create_app(config):
    app = Flask('webapp', static_folder='static/', static_url_path='/')
    app.config.from_object(config)
    mail.init_app(app)
    db.engine = create_engine(config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    db.session = scoped_session(sessionmaker(autocommit=False,autoflush=False,bind=db.engine))
    def shutdown_session(ex):
        db.session.remove()
    app.teardown_request(shutdown_session)
    from webapp.metadata.db_models import Base, User, Journal, Volume, Issue
    Base.query = db.session.query_property()
    # Create database tables if they don't already exist.
    Base.metadata.create_all(bind=db.engine)
    login_manager.init_app(app)
    if config.DEMO_INSTANCE:
        from .cleanup import cleanup_task
        scheduler.init_app(app)
        scheduler.start()
        # Check every 15 minutes to clean up old papers.
        trigger = IntervalTrigger(minutes=15)
        scheduler.add_job(cleanup_task,
                          trigger=trigger,
                          args=[],
                          id='cleanup_update',
                          name='cleanup_update')
        app.logger.warning([str(job) for job in scheduler.get_jobs()])
    else:
        app.logger.warning('Scheduler was not started')
    with app.app_context():
        from . import admin
        from . import routes
        from . import auth
        app.register_blueprint(routes.home_bp)
        app.register_blueprint(admin.admin_bp)
        app.register_blueprint(auth.auth_bp)
        # We use rate limiting in auth_bp.
        limiter = Limiter(app=app,
                          storage_uri=app.config['RATELIMIT_STORAGE_URI'],
                          key_func=get_remote_address,
                          default_limits=[])
        limiter.limit("5/minute", error_message='Too many requests. Rate limiting is in effect.')(auth.auth_bp)
        limiter.exempt(admin.admin_bp)
        limiter.exempt(routes.home_bp)
        if config.USERS:
            for user in config.USERS:
                u = User.query.filter_by(email=user['email']).first()
                if not u:
                    db.session.add(User(user['email'],
                                        user['role'],
                                        user['password']))
            db.session.commit()
        for journal in config.JOURNALS:
            j = db.session.execute(select(Journal).where(Journal.name==journal['name'])).scalar_one_or_none()
            if not j:
                db.session.add(Journal(journal))
        db.session.commit()
        # This makes it possible for bibexport to find cryptobib.
        os.environ['BIBINPUTS'] = '.:{}'.format(os.path.join(app.root_path,
                                                             'metadata/latex/iacrcc'))
        return app


def generate_password():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(12))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
