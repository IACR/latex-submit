from os import path

basedir = path.abspath(path.dirname(__file__))

class Config:
    EMAIL_NOREPLY = 'iacrcc-noreply@iacr.org'
    EDITOR_EMAILS = 'iacrcc-editor@iacr.org'
    MAIL_SERVER = 'mx2.iacr.org'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'testing'
    MAIL_PASSWORD = 'removed_in_checked_in_version'
    SECRET_KEY = 'removed_in_checked_in_version'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///db.sqlite'
    UPLOAD_FOLDER = '/tmp'
    DATA_DIR = 'webapp/data'
    SITE_NAME = 'IACR Publishing Pipeline'
    SITE_SHORTNAME = 'IACR CiC'
    USERS = None

class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    DATA_DIR = '/var/www/wsgi/latex-submit/webapp/data'
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    USERS = [{'email': 'testing@iacr.org',
              'password': 'myenigm@',
              'role': 'admin'}]
    
