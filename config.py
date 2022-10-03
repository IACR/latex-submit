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
    REDIS_PASSWORD = 'go35HyTzf0rnowpl3ase'
    CELERY_BROKER_URL = f'redis://:{REDIS_PASSWORD}@localhost:6379/0'
    CELERY_RESULT_BACKEND = f'redis://:{REDIS_PASSWORD}@localhost:6379/0'
    DATA_DIR = 'webapp/data'

class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    
