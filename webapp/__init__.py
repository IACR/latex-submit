from collections import OrderedDict
from datetime import datetime
from flask import Flask, request, render_template, current_app
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import flask_security
from flask_security import datastore
from flask_sqlalchemy_lite import SQLAlchemy
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
from .init_data import InitData
from .metadata.db_models import User, Journal, Role

# Make sure we aren't running on an old python.
assert sys.version_info >= (3, 7)

def format_dt(dt):
    """A flask filter to format datetime."""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return ''

def obfuscate_email(email):
    """A flask filter to modify emails."""
    return email.replace('@', ' (at) ')

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

class Scheduler(BackgroundScheduler):
    """A simple wrapper around apscheduler. Much simpler than flask_apscheduler."""
    def init_app(self, app):
        self.app = app

# DB wrapper is global so we can have easy access to engine and session. It is configured
# in create_app.
db = SQLAlchemy()
user_datastore = flask_security.FSQLALiteUserDatastore(db, User, Role)
security = flask_security.Security()
# scheduler is only used to clean up old jobs in case it has config.DEMO_INSTANCE set to tru
scheduler = Scheduler(executors={'default': pool.ThreadPoolExecutor(1)},
                      timezone='America/Los_Angeles')


# In case we want to try to force the pragma for sqlite3.
# @event.listens_for(Engine, 'connect')
# def set_sqlite_pragma(conn, record):
#    """This can be used to enable cascade deletes automatically."""
#    print('connected')
#    cursor = conn.cursor()
#    cursor.execute('PRAGMA foreign_keys=ON')
#    cursor.close

def _get_journals():
    return db.session.execute(select(Journal)).scalars().all()

def initialize_data(init_path: str, admin_role: Role, db: SQLAlchemy, user_datastore: flask_security.FSQLALiteUserDatastore):
    """Used to initialize data in the database. This is useful for setting up a debug or test environment."""
    print('initialize data from ', init_path)
    init_file = Path(init_path)
    if not init_file.is_file():
        raise(ValueError('Missing initialization file'))
    init_data = InitData.model_validate_json(init_file.read_text(encoding='UTF-8'))
    if init_data.users:
        for user in init_data.users:
            user = user.model_dump()
            if not user_datastore.find_user(email=user['email']):
                user['password'] = flask_security.hash_password(user['password'])
                is_admin = False
                if 'is_admin' in user:
                    if user['is_admin']:
                        is_admin = True
                del user['is_admin']
                if 'confirmed' in user:
                    if user['confirmed']:
                        user['confirmed_at'] = datetime.now()
                    del user['confirmed']
                u = user_datastore.create_user(**user)
                user_datastore.commit()
                if is_admin:
                    user_datastore.add_role_to_user(u, admin_role)
                    user_datastore.commit()
    for j in init_data.journals:
        journal = db.session.execute(select(Journal).where(Journal.acronym==j.acronym)).scalar_one_or_none()
        if not journal:
            jdata = j.model_dump()
            del jdata['editors']
            del jdata['copyeditors']
            del jdata['viewers']
            db.session.add(Journal(**jdata))
            db.session.commit()
            journal = db.session.execute(select(Journal).where(Journal.acronym==j.acronym)).scalar_one_or_none()
        editor_role = user_datastore.find_role(Role.editor_role(journal.hotcrp_key))
        if not editor_role:
            editor_role = user_datastore.create_role(name=Role.editor_role(journal.hotcrp_key),
                                                     description='editor for {}'.format(journal.name),
                                                     permissions='journal-read,journal-write')
            user_datastore.commit()
        for editor_email in j.editors:
            editor = user_datastore.find_user(email=editor_email)
            if not editor:
                raise ValueError('unknown editor email: ' + editor_email)
            user_datastore.add_role_to_user(editor, editor_role)
        ce_role = user_datastore.find_role(Role.copyeditor_role(journal.hotcrp_key))
        if not ce_role:
            ce_role = user_datastore.create_role(name=Role.copyeditor_role(journal.hotcrp_key),
                                                 description='copyeditor for {}'.format(journal.name),
                                                 permissions='journal-read,journal-write')
            user_datastore.commit()
        for ce_email in j.copyeditors:
            ce = user_datastore.find_user(email=ce_email)
            if not ce:
                raise ValueError('unknown copyeditor email: ' + ce_email)
            user_datastore.add_role_to_user(ce, ce_role)
        viewer_role = user_datastore.find_role(Role.viewer_role(journal.hotcrp_key))
        if not viewer_role:
            viewer_role = user_datastore.create_role(name=Role.viewer_role(journal.hotcrp_key),
                                                     description='OJS viewer for {}'.format(journal.name),
                                                     permissions='')
            user_datastore.commit()
        for viewer_email in j.viewers:
            viewer = user_datastore.find_user(email=viewer_email)
            if not viewer:
                raise ValueError('unknown viewer email: ' + viewer_email)
            user_datastore.add_role_to_user(viewer, viewer_role)
    user_datastore.commit()

def create_app(config):
    app = Flask('webapp', static_folder='static/', static_url_path='/')
    app.config.from_object(config)
    mail.init_app(app)
    security = flask_security.Security(app, user_datastore)
    db.init_app(app)
    from webapp.metadata.db_models import Base
    if config.DEMO_INSTANCE and config.DEBUG:
        from .cleanup import cleanup_task
        scheduler.init_app(app)
        # Check every 15 minutes to clean up old papers.
        trigger = IntervalTrigger(minutes=15)
        scheduler.add_job(cleanup_task,
                          trigger=trigger,
                          args=[],
                          id='cleanup_update',
                          name='cleanup_update',
                          replace_existing=True)
        if not scheduler.running:
            try:
                scheduler.start()
            except SchedulerAlreadyRunningError:
                pass
        app.logger.warning([str(job) for job in scheduler.get_jobs()])
    else:
        app.logger.warning('Scheduler was not started')
    with app.app_context():
        app.jinja_env.filters['format_dt'] = format_dt
        app.jinja_env.filters['obfuscate_email'] = obfuscate_email
        # Create database tables if they don't already exist.
        Base.metadata.create_all(bind=db.engine)
        from . import routes
        from . import admin
        from . import ojs_admin
        app.register_blueprint(routes.home_bp)
        app.register_blueprint(admin.admin_bp)
        app.register_blueprint(ojs_admin.ojs_bp)
        #if config.DEBUG:
        #    for rule in app.url_map.iter_rules():
        #        print(rule.rule, '=> ', rule.endpoint)
        # We use rate limiting in the flask_security blueprint as well as admin_bp.
        limiter = Limiter(app=app,
                          storage_uri=app.config['RATELIMIT_STORAGE_URI'],
                          key_func=get_remote_address,
                          default_limits=[])
        limiter.limit("5/minute", error_message='Too many requests. Rate limiting is in effect.')(app.blueprints[config.SECURITY_BLUEPRINT_NAME])
        limiter.exempt(routes.home_bp)
        limiter.exempt(ojs_admin.ojs_bp)
        admin_role =  user_datastore.find_role(Role.ADMIN)
        if not admin_role:
            admin_role = user_datastore.create_role(name=Role.ADMIN,
                                                    description='Global site admin',
                                                    permissions='admin-read,admin-write')
            user_datastore.commit()
        if config.INIT_FILE:
            initialize_data(config.INIT_FILE, admin_role, db, user_datastore)
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
