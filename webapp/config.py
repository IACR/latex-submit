"""Configuration is now written in pydantic so that it can be
serialized and better documented. There are quite a few fields
that are specific to flask_security (these start with SECURITY_).
"""
from os import path

from enum import Enum
from pydantic import BaseModel, Field, AnyUrl, ConfigDict, EmailStr
from typing import List, Optional

basedir = path.abspath(path.dirname(__file__))

class Config(BaseModel):
    DEBUG: bool = Field(default=True,
                        title='Whether to enable debug mode',
                        description='Should be false in production')
    TESTING: bool = Field(default=False,
                          title='Whether to enable testing',
                          description='Should be false in production')
    HOTCRP_API_KEY: str = Field(default='ChangeThis',
                                title='Key used to authenticate API calls to HotCRP system',
                                description='This is used to record that a paper was uploaded and retrieve a list of papers.')
    HOTCRP_POST_KEY: str = Field(default='ChangeThis',
                                 title='Key used to authenticate uploads from hotcrp',
                                 description='Known as publish_shared_key in our HotCRP instance.')
    RATELIMIT_STORAGE_URI: str = Field(default='memory://',
                                       title='URL for flask_limiter storage location')
    SECRET_KEY: str = Field(default='ChangeThisInProduction',
                            title='A required key used in Flask to sign all tokens.')
    UPLOAD_FOLDER: str = Field(default='/tmp',
                               title='Folder for where file uploads go')
    DATA_DIR: str = Field('webapp/data',
                          title='Folder for where all data is stored for uploaded articles.')
    SITE_CONTACT_EMAIL: EmailStr = Field('nobody@example.com',
                                         title='Contact email for the site')
    SITE_NAME: str = Field(default='IACR Publishing Portal',
                           title='What the site will be known as.')
    SITE_SHORTNAME: str = Field(default = 'IACR Publishing',
                                title='The short name for the site. Used in mobile view.')
    PUBLISHER_NAME: str = Field(default='International Association for Cryptologic Research',
                                title='Name of the publisher')
    CROSSREF_PUBLISHER_EMAIL: EmailStr = Field(...,
                                               title='Email of account used for authenticating to crossref.')
    DEMO_INSTANCE: bool = Field(False,
                                title='Whether it is set up as a demonstration site with no authentication.',
                                description='This can be used in development or to run a demo site.')
    WTF_CSRF_TIME_LIMIT: Optional[int] = Field(None,
                                               title='Used by flask_wtf.')
    EXPORT_PATH: str = Field(default='/tmp',
                             title='Location for where exports go for a published issue')
    FUNDING_SEARCH_URL: str = Field(default='/searchapi/search',
                                    title='Allows search for ROR to be on a different site.')
    INIT_FILE: Optional[str] = Field(None,
                                     title='Path to initialization file to populate the database upon startup.',
                                     description='Used for simple setup in development')
    SQLALCHEMY_ENGINES: dict = Field(default={'default': 'sqlite:///db.sqlite'},
                                     title='Used by flask_sqlalchemy_lite')
    SQLALCHEMY_ENGINE_OPTIONS: dict = Field(default= {"pool_pre_ping": True},
                                            title='Used by flask_sqlalchemy_lite')
    ############################## options related to flask_security ######################################
    SECURITY_BLUEPRINT_NAME: str = Field(default='security_bp',
                                         title='Name of the blueprint from flask_security.')
    SECURITY_PASSWORD_SALT: str = Field(default='',
                                        title='This should be changed in production.')
    SECURITY_PASSWORD_HASH: str = Field(default='argon2',
                                        title='May be changed in testing')
    # Don't set this to true unless you know what you are doing.
    SECURITY_REGISTERABLE: bool = Field(default=False,
                                        title='Used by flask security',
                                        description='Create the /register route for security.register().')
    SECURITY_RECOVERABLE: bool = Field(default=True,
                                       title='Used by flask security',
                                        description='Create the /recover route for security.forgot_password().')
    SECURITY_SEND_REGISTER_EMAIL: bool = Field(default=True,
                                               title='Whether to send an email to people who register.')
    SECURITY_DEFAULT_REMEMBER_ME: bool = Field(default=True,
                                               title='Opts users into being remembered in their login.')
    SECURITY_USE_REGISTER_V2: bool = Field(default=True,
                                           title='This may not be needed in the future')
    SECURITY_CHANGEABLE: bool = Field(default=True,
                                      title='Used by flask security',
                                      description='Create the /change route for security.change_password.')
    SECURITY_CHANGE_EMAIL: bool = Field(default=True,
                                        title='Whether we allow users to change their email')
    SECURITY_CONFIRMABLE: bool = Field(default=True,
                                       title='Used by flask security',
                                       description='Create the /confirm/<token> route security.confirm_email and /confirm for security.send_confirmation.')
    SECURITY_URL_PREFIX: str = Field(default='/sec',
                                     title='Prefix on flask_security blueprint routes.')
    SECURITY_USERNAME_ENABLE: bool = Field(default=False,
                                           title='Whether to support username instead of email as username.')
    SECURITY_TRACKABLE: bool = Field(default=True,
                                     title='Used to track when people login and log their IP address')
    SECURITY_OAUTH_ENABLE: bool = Field(default=False,
                                        title='Whether to support OAUTH login providers')
    ############################## end options related to flask_security ######################################
    WTF_CSRF_ENABLED: bool = Field(default=True,
                                   title='Whether to use CSRF fields. Only turned off in testing.')
    SQLALCHEMY_ENGINES:dict = Field(default={'default': 'sqlite:///db.sqlite'},
                                    # 'pool_pre_ping': True},
                                    title='Config for flask_sqlalchemy_lite')
    SQLALCHEMY_ENGINE_OPTIONS: dict = Field(default= {"pool_pre_ping": True})
    SESSION_COOKIE_SAMESITE:str = Field(default='strict',
                                        title='how to remember cookies')
    REMEMBER_COOKIE_SAMESITE:str = Field(default='strict',
                                         title='only remember cookie for same site.')
    # flask_security works with either flask_mail or flask_mailman, but they have slightly
    # different settings.
    MAIL_SERVER: str = Field(...,
                             title='Domain for mail server',
                             description='You will need a username/password for this')
    MAIL_SUPPRESS_SEND: bool = Field(False,
                                     title='Whether to suppress sending mail with flask_mail.',
                                     description='This has no effect in flask_mailman')
    MAIL_DEFAULT_SENDER: str = Field(...,
                                     title='default return address for all email')
    MAIL_PORT: int = Field(587,
                           title='Port to contact the mail server.')
    MAIL_USE_TLS: bool = Field(default=True,
                               title='whether to use TLS for mail')
    MAIL_USERNAME: str = Field(default='notset',
                               title='You will need to set this in production')
    MAIL_PASSWORD: str = Field(default='',
                               title='You will need to set this in production')
    MAIL_BACKEND: str = Field(default='console',
                              title='Which backend to use for flask_mailman.',
                              description='In production this should be smtp, but in debug it should be console.')

# class ProdConfig(Config):
#     FLASK_ENV = 'production'
#     SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://publication:st0remydata@localhost/publication'
#     DATA_DIR = '/var/www/wsgi/latex-submit/webapp/data'
#     RATELIMIT_STORAGE_URI = 'memcached://localhost:11211'
#     EXPORT_PATH = '/var/www/wsgi/cicjournal/archive'
#     FUNDING_SEARCH_URL = 'https://publish.iacr.org/searchapi/search'
#     INIT_FILE = 'prod_init.json'
    
# class DebugConfig(Config):
#     FLASK_ENV = 'development'
#     DEBUG = True
#     TESTING = True
#     DEMO_INSTANCE = True
#     # used by kevin.
#     #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://publication:st0remydata@localhost/publication'
#     SQLALCHEMY_DATABASE_URI = 'sqlite:///debug.db'
#     # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://publication:mystuff@localhost/publication'
#     FUNDING_SEARCH_URL = 'http://localhost:5001/searchapi/search'
#     INIT_FILE = 'debug_init.json'

# class TestConfig(Config):
#     FLASK_ENV = 'development'
#     DEBUG = True
#     TESTING = True
#     WTF_CSRF_ENABLED = False
#     INIT_FILE = 'test_init.json'

if __name__ == '__main__':
    import json
    conf = Config()
    print(conf.model_dump_json(indent=2))
