"""Some forms are here as WTF forms."""

from flask import current_app as app
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired, FileField
from wtforms.validators import InputRequired, Email, EqualTo, Length, Regexp, NumberRange, AnyOf
from wtforms import EmailField, PasswordField, SubmitField, BooleanField, HiddenField, SelectField, StringField, ValidationError, IntegerField, FieldList, Form, FormField
from .metadata.db_models import Role, validate_version, Version
from .metadata import validate_paperid
from .metadata.compilation import dt_regex, PubType
import random, string # TODO - remove this
from . import create_hmac, validate_hmac
import logging
import time

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(),
                                            Email(message='Enter a valid email')])
    password = PasswordField('Password', validators=[InputRequired(message='Password must be at least 8 characters')])
    submit = SubmitField('Login')

class SignupForm(FlaskForm):
    """Not used at present."""
    email = EmailField('Email', validators=[InputRequired(),
                                            Email(message='Invalid email')])
    password = PasswordField('Password',
                             validators=[
                                 InputRequired(message='Password must be at least 8 characters'),
                                 Length(min=8,max=30),
                                 EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat password')
    accept_tos = BooleanField('I accept the terms of service.', validators=[InputRequired()])
    submit = SubmitField('Sign up')

class AdminUserForm(FlaskForm):
    """Used by admin to invite new user or change a user's role or email."""
    old_email = HiddenField('old_email')
    email = EmailField('Email', validators=[InputRequired(),
                                            Email(message='Invalid email')])
    role = SelectField('role', choices=[(str(r.value), str(r.value)) for r in Role])
    submit = SubmitField('Create user')
    delete_cb = BooleanField('Delete user',description="Delete user")

class PasswordForm(FlaskForm):
    """User to change their own password."""
    password = PasswordField('New password',
                             validators=[
                                 InputRequired(message='Password must be at least 8 characters'),
                                 Length(min=8,max=30),
                                 EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat new password')
    email = HiddenField('email', validators=[InputRequired()])
    submit = SubmitField('Change password')

class RecoverForm(FlaskForm):
    """Password recovery request. This must be behind admin."""
    email = EmailField('Email of user', validators=[InputRequired(),
                                                    Email(message='Enter a valid email')])
    submit = SubmitField('Send recovery information')

class CaptchaForm(FlaskForm):
    email = EmailField('Email',
                       render_kw={'readonly': True},
                       validators=[InputRequired(),
                                   Email(message='Enter a valid email')])
    auth = HiddenField(id='auth',
                       name='auth',
                       validators = [InputRequired('auth field is required')])
    challenge = StringField('Challenge', render_kw={'readonly': True}, validators=[InputRequired()])
    response = StringField('Response', validators=[InputRequired()])
    submit = SubmitField('Submit answer')

class ValidPaperId(object):
    """Validator to check paperid."""
    def __init__(self, message=None):
        if not message:
            message = 'Invalid paperid'
        self.message = message

    def __call__(self, form, field):
        if not validate_paperid(field.data):
            raise ValidationError(self.message)

class ValidPubType(object):
    """Validator to check for a valid pubtype field."""
    def __init__(self, message=None):
        if not message:
            message = 'Invalid pubtype'
        self.message = message

    def __call__(self, form, field):
        val = PubType.from_str(field.data)
        if not val:
            raise ValidationError(self.message)

class ValidVersion(object):
    """Validator to check version."""
    def __init__(self, message=None):
        if not message:
            message = 'Invalid paperid'
        self.message = message

    def __call__(self, form, field):
        if not validate_version(field.data):
            raise ValidationError(self.message)

def maxmin_check(name, min=-1, max=-1):
    if min >= 0 and max >= 0:
        message = 'Invalid {}: must be an integer between {} and {}'.format(name, min, max)
    elif min >= 0:
        message = 'Invalid {}: must be an integer at least {}'.format(name, min)
    elif max >= 0:
        message = 'Invalid {}: must be integer at most {}'.format(name, max)
    else:
        'Invalid {}'.format(name)

    def _check_hidden(form, field):
        if len(field.data) < 1:
            raise ValidationError(message)
        try:
            intval = int(field.data)
            if ((min != -1 and intval < min) or
                (max != -1 and intval > max)):
                raise ValidationError(message)
        except Exception as e:
            raise ValidationError(str(e))
    return _check_hidden


class SubmitForm(FlaskForm):
    """Form to submit a version of a paper. The auth field authenticates
    required fields. This may be supplied by an external link for the
    first submission, or may be supplied by the server for subsequent
    versions. Validation for a POST is different than validation for a GET.
    In the case of a GET, we only validate the auth field, but for a POST
    we validate that all required fields are submitted.
    """
    def __init__(self, *args, **kwargs):
        """Set auth value from other fields."""
        super(SubmitForm, self).__init__(*args, **kwargs)

    paperid = HiddenField(label='Paper ID',
                          id='paperid',
                          name='paperid',
                          validators=[InputRequired('paper id is required'),
                                      ValidPaperId()],
                          # TODO - remove default below
                          default= '')
    version = HiddenField(id='version',
                          name='version',
                          validators=[InputRequired('version field is required'),
                                      ValidVersion()],
                          default=Version.CANDIDATE.value)
    hotcrp = HiddenField(id='hotcrp',
                         name='hotcrp',
                         default='',
                         validators=[InputRequired('hotcrp instance shortName')])
    hotcrp_id = HiddenField(id='hotcrp_id',
                            name='hotcrp_id',
                            default='',
                            validators=[InputRequired('paper id in HotCRP instance')])
    journal = HiddenField(id='journal',
                          name='journal',
                          description='key to select the journal from the list of journals',
                          validators=[InputRequired('journal is required'),
                                      AnyOf([j['hotcrp_key'] for j in app.config['JOURNALS']])])
    volume = HiddenField(id='volume',
                         name='volume',
                         description='This is the name field on volume',
                         validators=[InputRequired('Volume is required')])
    issue = HiddenField(id='issue',
                        name='issue',
                        description='This is the name field on Issue',
                        validators=[InputRequired('Issue is required')])
    submitted = HiddenField(id='submitted',
                            name='submitted',
                            validators=[InputRequired('Submission date is required'),
                                        Regexp(dt_regex, message='Format of submitted is YYYY-mm-dd HH:MM:SS')],
                            default='')
    accepted = HiddenField(id='accepted',
                           name='accepted',
                           validators=[InputRequired('Accepted date is required'),
                                       Regexp(dt_regex, message='Format of accepted is YYYY-mm-dd HH:MM:SS')],
                           default='')
    pubtype = HiddenField(id='pubtype',
                          name='pubtype',
                          validators=[InputRequired('pubtype field is required'),
                                      ValidPubType()],
                          default=PubType.RESEARCH.name)
    errata_doi = HiddenField(id='errata_doi',
                             name='errata_doi',
                             validators=[Regexp('(^$|^10.[0-9]{4,9}/[-._/a-zA-Z0-9]+$)', message='DOI format must be empty or start with 10.')],
                             default='')
    auth = HiddenField(id='auth',
                       name='auth',
                       validators = [InputRequired('auth field is required')])
    email = EmailField(id='email',
                       name='email',
                       validators=[InputRequired(), Email()])
    engine = SelectField(label='LaTeX engine to use',
                         id='engine',
                         name='engine',
                         choices=[('lualatex', 'lualatex'),
                                  ('pdflatex', 'pdflatex'),
                                  ('xelatex', 'xelatex')],
                         default = 'pdflatex')
    zipfile = FileField(id='zipfile',
                        name='zipfile',
                        validators=[FileRequired(),
                                    FileAllowed(['zip'])])
    submit = SubmitField('Upload')

    def check_auth(self):
        # TODO also validate the email from hotcrp?
        return validate_hmac([self.paperid.data,
                              self.hotcrp.data,
                              self.hotcrp_id.data,
                              self.version.data,
                              self.submitted.data,
                              self.accepted.data,
                              self.journal.data,
                              self.volume.data,
                              self.issue.data,
                              self.pubtype.data],
                             self.auth.data)

    # TODO: remove this. It's only for testing.
    def generate_auth(self):
        self.auth.data = create_hmac([self.paperid.data,
                                      self.hotcrp.data,
                                      self.hotcrp_id.data,
                                      self.version.data,
                                      self.submitted.data,
                                      self.accepted.data,
                                      self.journal.data,
                                      self.volume.data,
                                      self.issue.data,
                                      self.pubtype.data])

    def validate(self, extra_validators=None):
        if not super(FlaskForm, self).validate():
            logging.warning('failed to validate: ' + str(self.errors))
            return False
        return self.check_auth()

class NotifyFinalForm(FlaskForm):
    """Form to notify copy editor that final version is ready."""
    paperid = HiddenField(id='paperid',
                          name='paperid',
                          validators=[InputRequired('paper id is required'),
                                      ValidPaperId()])
    version = HiddenField(id='version',
                          name='version',
                          validators=[InputRequired('version field is required'),
                                      ValidVersion()],
                          default=Version.FINAL.value)
    auth = HiddenField(id='auth',
                       name='auth',
                       validators = [InputRequired('auth field is required')])
    email = HiddenField(id='email',
                        name='email',
                        validators=[InputRequired(), Email()])
    submit = SubmitField('Submit final version')
    def validate(self, extra_validators=None):
        if not super(FlaskForm, self).validate():
            logging.warning('failed to validate: ' + str(self.errors))
            return False
        if (self.version.data != Version.FINAL.value):
            logging.warning('NotifyFinalForm has wrong version: {}'.format(version.data))
            return False
        return validate_hmac([self.paperid.data,
                              Version.FINAL.value,
                              self.email.data],
                             self.auth.data)


class CompileForCopyEditForm(FlaskForm):
    """This is a simple form submitted by the author to send their
    candidate version or final version to the copy editor. The auth field
    authenticates required fields. Validation for a POST is different than
    validation for a GET.  In the case of a GET, we only validate the
    auth field, but for a POST we validate that all required fields
    are submitted. Submitting this form will result in creating the
    copyedit version as a copy of the version that was requested.
    """
    def __init__(self, *args, **kwargs):
        """Set auth value from other fields."""
        super(CompileForCopyEditForm, self).__init__(*args, **kwargs)
        if not self.auth.data:
            self.auth.data = create_hmac([self.paperid.data,
                                          self.version.data,
                                          self.email.data])
    paperid = HiddenField(label='Paper ID',
                          id='paperid',
                          name='paperid',
                          validators=[InputRequired('paper id is required'),
                                      ValidPaperId()])
    version = HiddenField(id='version',
                          name='version',
                          validators=[InputRequired('version field is required'),
                                      ValidVersion()],
                          default=Version.CANDIDATE.value)
    auth = HiddenField(id='auth',
                       name='auth',
                       validators = [InputRequired('auth field is required')])
    email = HiddenField(id='email',
                        name='email',
                        validators=[InputRequired(), Email()])
    submit = SubmitField('Finalize for copyedit')
    def check_auth(self):
        return validate_hmac([self.paperid.data,
                              self.version.data,
                              self.email.data],
                             self.auth.data)

    def validate(self, extra_validators=None):
        if not super(FlaskForm, self).validate():
            logging.warning('failed to validate: ' + str(self.errors))
            return False
        if (self.version.data != Version.CANDIDATE.value and
            self.version.data != Version.FINAL.value):
            logging.warning('CompileForCopyEditForm has wrong version: {}'.format(version.data))
            return False
        return self.check_auth()

class MoreChangesForm(FlaskForm):
    """This is used to replace the candidate version by the copyedit version, and is only
       called by the admin in the final review phase."""
    paperid = HiddenField(id='paperid', name='paperid',
                          validators=[InputRequired('paper id is required'),
                                      ValidPaperId()])
    submit = SubmitField('Replace candidate version by final version')

class PublishIssueForm(FlaskForm):
    """This is used by the admin to publish an issue for a journal."""
    issueid = HiddenField(name='issueid',
                          validators=[InputRequired()])
    submit = SubmitField('Export issue for publishing')

class ChangeIssueForm(FlaskForm):
    """Used to change the issue for a paper."""
    paperid = HiddenField(name='paperid',
                          validators=[InputRequired(),
                                      ValidPaperId()])
    # If this is missing, it means to unassign the paper.
    issueid = HiddenField(name='issueid')
    # nexturl is used for redirection.
    nexturl = HiddenField(name='nexturl', validators=[InputRequired()])
    submit = SubmitField(label='bump')

class ChangePaperNumberForm(FlaskForm):
    """Use to change the paperno on an issue."""
    issueid = HiddenField(name='issueid', validators=[InputRequired()])
    paperid = HiddenField(name='paperid', validators=[InputRequired()])
    upbutton = SubmitField(name='up', label='⇑')
    downbutton = SubmitField(name='down', label='⇓')

class CopyeditClaimForm(FlaskForm):
    """Used to claim a paper for copy editing."""
    paperid = HiddenField(name='paperid',
                          validators=[InputRequired(),
                                      ValidPaperId()])
    view = HiddenField('view the paper', default='')
    copyeditor = HiddenField(name='copyeditor', validators=[InputRequired()])

class DeletePaperForm(FlaskForm):
    paperid = HiddenField(name='paperid',
                          validators=[InputRequired(),
                                      ValidPaperId()])
    # A paper may not belong to this issue, but it's used for
    # determining where to forward the user to. Once the issue has no
    # papers, it can be deleted.
    issueid = HiddenField(name='issueid',
                          validators=[InputRequired()])
