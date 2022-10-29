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
    JOURNAL_NAME = 'IACR Communications in Cryptology'

class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    
