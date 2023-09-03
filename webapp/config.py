from os import path

basedir = path.abspath(path.dirname(__file__))

class Config:
    EMAIL_NOREPLY = 'iacrcc-noreply@iacr.org'
    EDITOR_EMAILS = 'iacrcc-editor@iacr.org'
    COPYEDITOR_EMAILS = 'iacrcc-copyedit@iacr.org'
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
    SITE_NAME = 'IACR Publishing Portal'
    SITE_SHORTNAME = 'IACR CiC'
    PUBLISHER_NAME = 'International Association for Cryptologic Research'
    CROSSREF_PUBLISHER_EMAIL = 'crossref@iacr.org'
    USERS = None
    TESTING = False
    JOURNALS = [
        {
            'key': 'cic',
            'name': 'IACR Communications in Cryptology',
            'EISSN': 'XXXX-YYYY',
            'DOI_PREFIX': '10.1729'
        },
        {
            'key': 'tosc',
            'name': 'IACR Transactions on Symmetric Cryptology',
            'EISSN': '2519-173X',
            'DOI_PREFIX': '10.46586'
        },
        {
            'key': 'tches',
            'name': 'IACR Transactions on Cryptographic Hardware and Embedded Systems',
            'EISSN': '2569-2925',
            'DOI_PREFIX': '10.45686'
        },
        {
            'key': 'lncs',
            'name': 'Lecture Notes in Computer Science',
            'EISSN': '1611-3349',
            'DOI_PREFIX': '10.1007'
        },
    ]

class ProdConfig(Config):
    FLASK_ENV = 'production'
    XAPIAN_DB_PATH = '/var/www/wsgi/latex-submit/webapp/fundreg/xapian.db'
    DATA_DIR = '/var/www/wsgi/latex-submit/webapp/data'
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    USERS = [{'email': 'testing@example.com',
              'password': 'mypowers',
              'role': 'admin'}]
