from os import path

basedir = path.abspath(path.dirname(__file__))

class Config:
    EMAIL_NOREPLY = 'iacrcc-noreply@iacr.org'
    EDITOR_EMAILS = 'iacrcc-editor@iacr.org'
    UPLOAD_FOLDER = '/tmp'
    DB_USER = 'iacrcc'
    DB_NAME = 'iacrcc'
    DB_PASSWORD = 'l3t_m3_in_n0w'
    DB_HOST = 'localhost'
    DATA_DIR = 'webapp/data'
    SITE_NAME = 'IACR Publishing Pipeline'
    SITE_SHORTNAME = 'IACR CiC'

class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    DATA_DIR = '/var/www/wsgi/latex-submit/webapp/data'
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    