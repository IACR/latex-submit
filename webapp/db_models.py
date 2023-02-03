from datetime import datetime
from . import db
from enum import Enum
from flask_login import UserMixin
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

# from urlparse import urlparse, urljoin

# def is_safe_url(target):
#     # Is this URL safe to redirect to?
#     ref_url = urlparse(request.host_url)
#     test_url = urlparse(urljoin(request.host.url, target))
#     return test_user.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

class Role(str, Enum):
    AUTHOR = 'author'
    COPYEDIT = 'copyedit'
    ADMIN = 'admin'

class Version(str, Enum):
    CANDIDATE = 'candidate'
    COPYEDIT = 'copyedit'
    FINAL = 'final'

def validate_version(val):
    return val in [v.value for v in Version]

qclass TaskStatus(str, Enum):
    """Status of a paper."""
    PENDING = 'PENDING'
    CANCELLED = 'CANCELLED'
    RUNNING = 'RUNNING'
    FAILED_EXCEPTION = 'FAILED_EXCEPTION'
    FAILED_COMPILE = 'FAILED_COMPILE'
    FINISHED = 'FINISHED'
    ERROR = 'ERROR'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), primary_key=False, unique=False, nullable=False)
    role = db.Column(db.Enum(Role,
                             values_callable=lambda x: [str(member.value) for member in Role]),
                     unique=False,
                     nullable=False)
    created_on = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    def __init__(self, email, role, password):
        self.email = email
        self.role = role
        self.set_password(password)
        self.created_on = datetime.now()

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User {}'.format(self.email)

class CompileRecord(db.Model):
    __table_args__ = (db.UniqueConstraint('paperid', 'version', name='paper_version_ind'),)
    id = db.Column(db.Integer, primary_key=True)
    paperid = db.Column(db.String(32), nullable=False, index=True)
    version = db.Column(db.Enum(Version,
                                values_callable=lambda x: [str(v.value) for v in Version]),
                        nullable=False,index=True)
    task_status = db.Column(db.Enum(TaskStatus,
                                    values_callable=lambda x: [str(s.value) for s in TaskStatus]),
                            default=TaskStatus.PENDING.value)
    started = db.Column(db.DateTime, index=False, nullable=False)
    result = db.Column(db.String, nullable=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
