"""
This defines the database models for SQLAlchemy in 2.0 style.
"""
from datetime import datetime
from enum import Enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Boolean, Integer, String, Text, DateTime, UniqueConstraint, ForeignKey, Table, Column, select
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_security.models import sqla as sqla
from typing import List, Optional
try:
    from .compilation import PubType
except:
    from compilation import PubType

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
    PUBLISHED = 'Exported (published)'
  
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

roles_users = Table(
    "roles_users",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("role_id", Integer, ForeignKey("role.id"))
)

"""
The design of the Role is one of many possible designs.
1. in this choice, we do not use Role.permissions, and there are
   four kinds of roles:
  * admin (essentially root on the site). There must be one, and only
    they can create other users.
  * editor for a journal, named Role.editor_role(journal_key)
  * copyeditor for a journal, named as Role.copyeditor_role(journal_key).
  * viewer for a journal. They have no write permission on papers. This
    is named Role.viewer_role(journal_key)
2. Another choice is to make the roles be simply 'admin, 'editor', 'copyeditor', and
   'viewer', and store the list of journals in the permissions of the role.
   This makes it clumsy to look up whether a user has access to a journal.
3. Another choice is to make the role be the same as the journal,
   and store 'editor' or 'copyeditor' in the permissions for the role.
If we end up needing finer-grained access on the basis of role, then we
might change this in the future.
"""
class Role(Base, sqla.FsRoleMixin):
    ADMIN = 'admin'
    __tablename__ = 'role'
    users: Mapped[List['User']] = relationship('User',
                                               secondary=roles_users,
                                               back_populates='roles')
    @classmethod
    def editor_role(cls, journal_key):
        return journal_key + '_editor'
    @classmethod
    def copyeditor_role(cls, journal_key):
        return journal_key + '_copyeditor'
    @classmethod
    def viewer_role(cls, journal_key):
        return journal_key + '_viewer'
    @classmethod
    def user_journal_keys(cls, user):
        journal_keys = set()
        for role in user.roles:
            if 'editor' in role.name:
                journal_keys.add(role.name.split('_')[0])
        return journal_keys

"""
User permissions are implemented with the Role class using flask_security,
but there is an example of a one-to-many relationship for roles with
flask_login located at https://github.com/maxcountryman/flask-login/issues/421
"""
class User(Base, sqla.FsUserMixin):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    alternate_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    # last_login was replaced by last_login_at from FsUserMixin.
    # last_login: Mapped[datetime] = mapped_column(DateTime(), nullable=True)
    fs_uniquifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    roles: Mapped[List['Role']] = relationship('Role',
                                               secondary=roles_users,
                                               back_populates='users')
    @property
    def is_active(self):
        return self.active
    def description(self):
        return self.name + ' (' + ', '.join(json.loads(self.affiliations)) + ')'
    def html(self):
        return self.name + '<div class="form-text">' + ', '.join(json.loads(self.affiliations)) + '</div>'
    def __repr__(self):
        """We use a simplistic version of repr because we use cache.memoize on
        some functions that take a user as an argument.

        """
        return 'user{}'.format(self.id)

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
    creator: Mapped[str] = mapped_column(ForeignKey('user.email', ondelete='CASCADE'), nullable=False)
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
    revised: Mapped[str] = mapped_column(String(32), nullable=False, default='')
    pubtype: Mapped[PubType] = mapped_column(default=PubType.RESEARCH)
    status: Mapped[PaperStatusEnum] = mapped_column(default=PaperStatusEnum.PENDING)
    hotcrp: Mapped[str] = mapped_column(String(32),
                                        default=NO_HOTCRP,
                                        comment='This is the shortName of the HotCRP instance.')
    hotcrp_id: Mapped[str] = mapped_column(String(32),
                                           comment='The paperid in the HotCRP instance')
    # journal_key is how the journal is known. This should have been
    # a foreign key to journal, but schema changes are hard.
    journal_key: Mapped[str] = mapped_column(String(32), nullable=False,
                                             comment='Original journal::hotcrp_key. Should not be changed.')
    volume_key: Mapped[str] = mapped_column(String(32), nullable=False,
                                            comment='Original volume::hotcrp_key. Should not be changed.')
    issue_key: Mapped[str] = mapped_column(String(32), nullable=False,
                                           comment='Original issue::hotcrp_key. Should not be changed.')
    issue_id: Mapped[Optional[int]] = mapped_column(ForeignKey('issue.id', ondelete='SET NULL'),
                                                    nullable=True,
                                                    comment='May be changed if moved to another issue for the journal')
    issue: Mapped['Issue'] = relationship(back_populates='papers')
    paperno: Mapped[int] = mapped_column(Integer, nullable=True, comment='Paper number within its issue')
    # This could use ON UPDATE CURRENT_TIMESTAMP, but that's mysql-specific. We could also try to use
    # sqlalchemy.event, but it's easy to just update it manually.
    lastmodified: Mapped[datetime] = mapped_column(DateTime(),
                                                   server_default=func.now())
    # This is created the first time someone uploads a paper with this paperid.
    creationtime: Mapped[datetime] = mapped_column(DateTime(),
                                                   server_default=func.now())
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='Last recorded title')
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='Last recorded, comma-delimited list of authors')
    copyeditor: Mapped[str] = mapped_column(ForeignKey('user.email', ondelete='SET NULL'), default=None, nullable=True)
    def journal(self, db):
        """TODO: change this to use a foreign key in journal."""
        return db.session.execute(select(Journal).where(Journal.hotcrp_key == self.journal_key)).scalar_one_or_none()


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
    # The hotcrp_key is very important, because it is used to uniquely refer
    # to a journal both within this system and in the HotCRP review system.
    # They show up in the Role permissions.
    hotcrp_key: Mapped[str] = mapped_column(String(32),
                                            unique=True,
                                            nullable=False,
                                            comment='What the journal is known by in hotcrp')
    acronym: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(Text, nullable=False)
    EISSN: Mapped[str] = mapped_column(String(10), nullable=True)
    DOI_PREFIX: Mapped[str] = mapped_column(String(10), nullable=False)
    volumes: Mapped[List['Volume']] = relationship(back_populates='journal', cascade="all, delete-orphan")
    def copyedit_contacts(self, db):
        """Return copyeditors, or failing that, the editors, or failing that, an admin."""
        role = db.session.execute(select(Role).where(Role.name == Role.copyeditor_role(self.hotcrp_key))).scalar()
        users= role.users
        if len(users) > 0:
            return users
        role = db.session.execute(select(Role).where(Role.name == Role.editor_role(self.hotcrp_key))).scalar()
        users = role.users
        if len(users) > 0:
            return users
        # There is always supposed to be someone with the admin role.
        role = db.session.execute(select(Role).where(Role.name == Role.ADMIN)).scalar()
        return role.users


class Volume(Base):
    __tablename__ = 'volume'
    __table_args__ = (UniqueConstraint('journal_id', 'name', name='journal_volume_ind'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[int] = mapped_column(Integer,
                                      comment='Usually the year or a number. Should match value in hotcrp instance.')
    journal_id: Mapped[int] = mapped_column(ForeignKey('journal.id', ondelete='CASCADE'), nullable=False)
    journal: Mapped['Journal'] = relationship(back_populates='volumes')
    issues: Mapped[List['Issue']] = relationship(back_populates='volume', cascade='all, delete-orphan')

# Each hotcrp instance corresponds to an issue. An issue is created by
# uploading the first paper from the hotcrp instance.  In any event
# the hotcrp value should be the hotcrp shortName value so we can show
# pending papers for the issue.

class Issue(Base):
    __tablename__ = 'issue'
    __table_args__ = (UniqueConstraint('volume_id', 'name', name='volume_issue_ind'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exported: Mapped[Optional[datetime]] = mapped_column(DateTime(),
                                                         default=None,
                                                         comment='When an issue is exported')
    hotcrp: Mapped[Optional[str]] = mapped_column(String(32),
                                                  default=None,
                                                  comment=('The shortName of the hotcrp instance this issue is matched to. '
                                                 'Each issue corresponds to a hotcrp instance, but other papers may '
                                                 'be added to the issue. This value should not be changed.'))
    name: Mapped[int] = mapped_column(Integer,
                                      comment=('Issues are numbered starting at 1 within a volume. If this is '
                                               'changed then papers uploaded from the hotcrp instance '
                                               'will create a new issue with the name in hotcrp.'))
    volume_id: Mapped[int] = mapped_column(ForeignKey('volume.id', ondelete='cascade'), nullable=False)
    volume: Mapped['Volume'] = relationship(back_populates='issues')
    papers: Mapped[List['PaperStatus']] = relationship(back_populates='issue')
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True,
                                                       comment='For example, "Special issue on secure messaging"')
