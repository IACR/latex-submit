"""
This defines the database models for SQLAlchemy in 2.0 style.
"""
from datetime import datetime
from enum import Enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Integer, String, Text, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional

# This is used for testing for papers that are submitted without hotcrp.
NO_HOTCRP = 'none'

class PaperStatusEnum(str, Enum):
    PENDING = 'In progress'
    SUBMITTED = 'Submitted'
    EDIT_PENDING = 'Awaiting copy editing'
    EDIT_FINISHED = 'Awaiting author response to copyedit'
    FINAL_SUBMITTED = 'Pending final review'
    EDIT_REVISED = 'Further revision requested'
    COPY_EDIT_ACCEPT = 'Copy edit complete'
    PUBLISHED = 'Published'
  
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

class TaskStatus(str, Enum):
    """Status of a paper."""
    PENDING = 'PENDING'
    CANCELLED = 'CANCELLED'
    RUNNING = 'RUNNING'
    FAILED_EXCEPTION = 'FAILED_EXCEPTION'
    FAILED_COMPILE = 'FAILED_COMPILE'
    FINISHED = 'FINISHED'
    ERROR = 'ERROR'

class Base(DeclarativeBase):
    def as_dict(self):
        """Convert to dict with Enum fields as {'name': ..., 'value': ...}."""
        retval = dict()
        for c in self.__table__.columns:
            obj = getattr(self, c.name)
            if isinstance(obj, Enum):
                obj = {'name': obj.name, 'value': obj.value}
            retval[c.name] = obj
        return retval

class User(UserMixin, Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    # TODO: make roles be a one-to-many relationship
    # See https://github.com/maxcountryman/flask-login/issues/421
    role: Mapped[Role] = mapped_column(nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(DateTime(), nullable=True)

    def __init__(self, email, role, password):
        self.email = email
        self.role = role
        self.set_password(password)
        self.created_on = datetime.now()

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User {}'.format(self.email)

class CompileRecord(Base):
    __tablename__ = 'compile_record'
    __table_args__ = (UniqueConstraint('paperid', 'version', name='paper_version_ind'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paperid: Mapped[str] = mapped_column(ForeignKey('paper_status.paperid', ondelete='CASCADE'), nullable=False, index=True)
    version: Mapped[Version] = mapped_column(nullable=False, index=True)
    task_status: Mapped[TaskStatus] = mapped_column(server_default = TaskStatus.PENDING.value)
    started: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    result: Mapped[str] = mapped_column(Text(16700000), nullable=True) # trigger longtext in mysql.

class DiscussionStatus(str, Enum):
    """Status of a copyedit discussion item."""
    PENDING = 'Pending'     # unanswered
    CANCELLED = 'Cancelled' # cancelled by creator
    DECLINED = 'Declined'   # declined by author
    CLARIFY = 'Clarify'     # clarification requested
    WILLFIX = 'Agreed to fix' # agreed to by author
    FIXED = 'Fixed'         # confirmed to be fixed

class Discussion(Base):
    __tablename__ = 'discussion'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warning_id: Mapped[Optional[int]] = mapped_column(Integer,
                                                      comment='Optional index of item from compilation.error_log that was escalated.')
    paperid: Mapped[str] = mapped_column(ForeignKey('paper_status.paperid', ondelete='CASCADE'), nullable=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=func.now())
    pageno: Mapped[int] = mapped_column(Integer, nullable=True)
    lineno: Mapped[int] = mapped_column(Integer, nullable=True) # line number in pdf
    logline: Mapped[int] = mapped_column(Integer, nullable=True) # line number in main.log
    source_file: Mapped[str] = mapped_column(Text, nullable=True)
    source_lineno: Mapped[int] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    reply: Mapped[str] = mapped_column(Text, nullable=True) # from author
    status: Mapped[DiscussionStatus] = mapped_column(default=DiscussionStatus.PENDING)
    archived: Mapped[Optional[datetime]] = mapped_column(default=None,
                                                         comment=('An item can be archived when it no longer applies '
                                                                  'to the current candidate version. This usually means that '
                                                                  'things like logline, pageno, etc are no longer derived from the '
                                                                  'current compiled version and are therefore unreliable. If '
                                                                  'this is non-null, then it indicates when the item was archived.'))

class PaperStatus(Base):
    """Primary record for a paper. It may have compilations, discussion, etc associated with it."""
    __tablename__ = 'paper_status'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paperid: Mapped[str] = mapped_column(String(32),
                                         nullable = False,
                                         unique=True,
                                         index=True,
                                         comment=('Assumed to be globally unique across all journals, volumes, and issues.'
                                                  'This is used to construct the DOI'))
    email: Mapped[str] = mapped_column(String(50), nullable=False)
    submitted: Mapped[str] = mapped_column(String(32), nullable=False)
    accepted: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[PaperStatusEnum] = mapped_column(default=PaperStatusEnum.PENDING)
    hotcrp: Mapped[str] = mapped_column(String(32),
                                        default=NO_HOTCRP,
                                        comment='This is the shortName of the HotCRP instance.')
    hotcrp_id: Mapped[str] = mapped_column(String(32),
                                           comment='The paperid in the HotCRP instance')
    journal_key: Mapped[str] = mapped_column(String(32), nullable=False,
                                             comment='Original journal::hotcrp_key. Should not be changed.')
    volume_key: Mapped[str] = mapped_column(String(32), nullable=False,
                                            comment='Original volume::hotcrp_key. Should not be changed.')
    issue_key: Mapped[str] = mapped_column(String(32), nullable=False,
                                           comment='Original issue::hotcrp_key. Should not be changed.')
    issue_id: Mapped[Optional[int]] = mapped_column(ForeignKey('issue.id'),
                                                    nullable=True,
                                                    comment='May be changed if moved to another issue for the journal')
    issue: Mapped['Issue'] = relationship(back_populates='papers')
    # This could use ON UPDATE CURRENT_TIMESTAMP, but that's mysql-specific. We could also try to use
    # sqlalchemy.event, but it's easy to just update it manually.
    lastmodified: Mapped[datetime] = mapped_column(DateTime(),
                                                   server_default=func.now())
    # This is created the first time someone uploads a paper with this paperid.
    creationtime: Mapped[datetime] = mapped_column(DateTime(),
                                                   server_default=func.now())
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='Last recorded title')
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='Last recorded, comma-delimited list of authors')

class LogEvent(Base):
    __tablename__ = 'log_event'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paperid: Mapped[str] = mapped_column(ForeignKey('paper_status.paperid', ondelete='CASCADE'), nullable=False)
    dt: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False) # free text field

def log_event(db, paperid, action):
    event = LogEvent(paperid=paperid,dt=datetime.now(),action=action)
    db.session.add(event)
    db.session.commit()

class Journal(Base):
    __tablename__ = 'journal'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hotcrp_key: Mapped[str] = mapped_column(String(32),
                                            unique=True,
                                            nullable=False,
                                            comment='What the journal is known by in hotcrp')
    acronym: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text)
    EISSN: Mapped[str] = mapped_column(String(10), nullable=False)
    DOI_PREFIX: Mapped[str] = mapped_column(String(10), nullable=False)
    volumes: Mapped[List['Volume']] = relationship(back_populates='journal', cascade="all, delete-orphan")
    def __init__(self, data):
        self.EISSN = data['EISSN']
        self.hotcrp_key = data['hotcrp_key']
        self.acronym = data['acronym']
        self.name = data['name']
        self.DOI_PREFIX = data['DOI_PREFIX']

class Volume(Base):
    __tablename__ = 'volume'
    __table_args__ = (UniqueConstraint('journal_id', 'name', name='journal_volume_ind'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32),
                                      comment='Usually the year or a number. Should match value in hotcrp instance.')
    journal_id: Mapped[int] = mapped_column(ForeignKey('journal.id', ondelete='CASCADE'), nullable=False)
    journal: Mapped['Journal'] = relationship(back_populates='volumes')
    issues: Mapped[List['Issue']] = relationship(back_populates='volume', cascade='all, delete-orphan')

# Each hotcrp instance corresponds to an issue. An issue may be
# created by uploading the first paper from the hotcrp instance.
# In any event the hotcrp value
# should be the hotcrp shortName value so we can show pending papers
# for the issue.

class Issue(Base):
    __tablename__ = 'issue'
    __table_args__ = (UniqueConstraint('volume_id', 'name', name='volume_issue_ind'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    published: Mapped[Optional[datetime]] = mapped_column(DateTime(),
                                                          default=None,
                                                          comment='When an issue is published')
    hotcrp: Mapped[Optional[str]] = mapped_column(String(32),
                                                  default=None,
                                                  comment=('The shortName of the hotcrp instance this issue is matched to. '
                                                 'Each issue corresponds to a hotcrp instance, but other papers may '
                                                 'be added to the issue. This value should not be changed.'))
    name: Mapped[str] = mapped_column(String(32),
                                      comment=('Usually number, e.g., 2. Starts off as value from hotcrp.'
                                               'If this is changed then papers uploaded from the hotcrp instance '
                                               'will create a new issue with the name in hotcrp.'))
    volume_id: Mapped[int] = mapped_column(ForeignKey('volume.id', ondelete='cascade'), nullable=False)
    volume: Mapped['Volume'] = relationship(back_populates='issues')
    papers: Mapped[List['PaperStatus']] = relationship(back_populates='issue')
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True,
                                                       comment='For example, "Special issue on secure messaging"')
