from os import path

basedir = path.abspath(path.dirname(__file__))

class Config:
    EMAIL_NOREPLY = 'iacrcc-noreply@iacr.org'
    EDITOR_EMAILS = 'iacrcc-editors@iacr.org'
    COPYEDITOR_EMAILS = 'iacrcc-copyedit@iacr.org'
    HOTCRP_API_KEY = 'IChangedIt'  # used for API calls to hotcrp
    HOTCRP_POST_KEY = 'IChangedIt' # used for posting papers from hotcrp
    MAIL_SERVER = 'mx2.iacr.org'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'testing'
    MAIL_PASSWORD = 'removed_in_checked_in_version'
    RATELIMIT_STORAGE_URI = 'memory://'
    SECRET_KEY = 'removed_in_checked_in_version'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///db.sqlite'
    UPLOAD_FOLDER = '/tmp'
    DATA_DIR = 'webapp/data'
    SITE_NAME = 'IACR Publishing Portal'
    SITE_SHORTNAME = 'IACR CiC'
    PUBLISHER_NAME = 'International Association for Cryptologic Research'
    CROSSREF_PUBLISHER_EMAIL = 'crossref@iacr.org'
    USERS = None
    TESTING = False
    WTF_CSRF_TIME_LIMIT = None
    EXPORT_PATH = '/tmp'
    FUNDING_SEARCH_URL = '/searchapi/search'
    JOURNALS = [
        {
            'hotcrp_key': 'cic',
            'acronym': 'CiC',
            'name': 'IACR Communications in Cryptology',
            'publisher': 'International Association for Cryptologic Research',
            'EISSN': '3006-5496',
            'DOI_PREFIX': '10.62056'
        },
        {
            'hotcrp_key': 'tosc',
            'acronym': 'TOSC',
            'name': 'IACR Transactions on Symmetric Cryptology',
            'publisher': 'International Association for Cryptologic Research',
            'EISSN': '2519-173X',
            'DOI_PREFIX': '10.46586'
        },
        {
            'hotcrp_key': 'tches',
            'acronym': 'TCHES',
            'name': 'IACR Transactions on Cryptographic Hardware and Embedded Systems',
            'publisher': 'International Association for Cryptologic Research',
            'EISSN': '2569-2925',
            'DOI_PREFIX': '10.45686'
        },
        {
            'hotcrp_key': 'lncs',
            'acronym': 'LNCS',
            'name': 'Springer Lecture Notes in Computer Science',
            'publisher': 'Springer',
            'EISSN': '1611-3349',
            'DOI_PREFIX': '10.1007'
        },
    ]

class ProdConfig(Config):
    FLASK_ENV = 'production'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://publication:st0remydata@localhost/publication'
    DATA_DIR = '/var/www/wsgi/latex-submit/webapp/data'
    RATELIMIT_STORAGE_URI = 'memcached://localhost:11211'
    EXPORT_PATH = '/var/www/wsgi/cicjournal/archive'
    FUNDING_SEARCH_URL = 'https://publish.iacr.org/searchapi/search'
    
class DebugConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    # used by kevin.
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://publication:st0remydata@localhost/publication'
    USERS = [{'email': 'testing@example.com',
              'password': 'mypowers',
              'role': 'admin'}]
    FUNDING_SEARCH_URL = 'http://localhost:5001/searchapi/search'
