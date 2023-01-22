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
    XAPIAN_DB_PATH = 'webapp/fundreg/xapian.db'
    DATA_DIR = 'webapp/data'
    SITE_NAME = 'IACR Publishing Pipeline'
    SITE_SHORTNAME = 'IACR CiC'
    USERS = None
    ROOT_URL = 'http://localhost:5000'

class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    XAPIAN_DB_PATH = '/var/www/wsgi/latex-submit/webapp/fundreg/xapian.db'
    DATA_DIR = '/var/www/wsgi/latex-submit/webapp/data'
    ROOT_URL = 'https://publish.iacr.org'
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    USERS = [{'email': 'testing@example.com',
              'password': 'mypowers',
              'role': 'admin'}]
    
