from os import path

basedir = path.abspath(path.dirname(__file__))

class Config:
    XAPIAN_DB_PATH = 'searchapp/index/xapian.db'
    TESTING = False
    APPLICATION_ROOT='/'

class ProdConfig(Config):
    FLASK_ENV = 'production'
    XAPIAN_DB_PATH = '/var/www/wsgi/latex-submit/idsearch/searchapp/index/xapian.db'
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    # Ordinarily in production we would run under /funding using
    # apache configuration to set this.
    APPLICATION_ROOT='/searchapi'
