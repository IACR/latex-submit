"""Some forms are here as WTF forms."""

from flask import current_app as app
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired, FileField
from wtforms.validators import InputRequired, Email, EqualTo, Length
from wtforms import EmailField, PasswordField, SubmitField, BooleanField, HiddenField, SelectField, StringField, ValidationError
from .db_models import Role, validate_version, Version
from .metadata import validate_paperid
import random, string # TODO - remove this
from datetime import datetime
import hmac, hashlib
import logging

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
    old_password = PasswordField('Old password')
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
    email = EmailField('Email', validators=[InputRequired(),
                                            Email(message='Enter a valid email')])
    submit = SubmitField('Send recovery information')

class ValidPaperId(object):
    """Validator to check paperid."""
    def __init__(self, message=None):
        if not message:
            message = 'Invalid paperid'
        self.message = message

    def __call__(self, form, field):
        if not validate_paperid(field.data):
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

class ValidDatetime(object):
    """Validator to check datetime for accepted and submitted fields."""
    def __init__(self, message=None):
        if not message:
            message = 'Invalid paperid'
        self.message = message

    def __call__(self, form, field):
        try:
            then = datetime.fromisoformat(field.data)
        except ValueError as e:
            msg = 'Invalid {}:{}'.format(field.id, str(e))
            raise ValidationError(msg)


class SubmitForm(FlaskForm):
    """Form to submit a version of a paper. The auth field authenticates
    required fields. This may be supplied by an external link for the
    first submission, or may be supplied by the server for subsequent
    versions.
    """
    def __init__(self, *args, **kwargs):
        """Set auth value from other fields."""
        super(SubmitForm, self).__init__(*args, **kwargs)
        if not self.auth.data:
            self.auth.data = self.create_hmac()
    paperid = StringField(label='Paper ID',
                          id='paperid',
                          name='paperid',
                          validators=[InputRequired(), ValidPaperId()],
                          # TODO - remove default below
                          default=''.join(random.choices(string.ascii_lowercase + string.digits, k=8)))
    version = HiddenField(id='version',
                          name='version',
                          validators=[InputRequired(), ValidVersion()],
                          default=Version.CANDIDATE.value)
    venue = SelectField(label='Select a venue. At present only iacrcc is fully supported',
                        id='venue',
                        name='venue',
                        choices=[('iacrcc', 'IACR Communications in Cryptology'),
                                 ('tosc', 'IACR Transactions on Symmetric Cryptology (partially supported)'),
                                 ('tches', 'IACR Transactions on Cryptographic Hardware and Embedded Systems (partially supported)'),
                                 ('asiacrypt', 'Asiacrypt (Springer LNCS)'),
                                 ('crypto', 'Crypto (Springer LNCS)'),
                                 ('eurocrypt', 'Eurocrypt (Springer LNCS)'),
                                 ('pkc', 'PKC (Springer LNCS)'),
                                 ('tcc', 'TCC (Springer LNCS)')],
                        default = 'iacrcc',
                        validators=[InputRequired()])
    submitted = HiddenField(id='submitted',
                            name='submitted',
                            validators=[InputRequired(), ValidDatetime()],
                            default='2022-08-03T06:44:30.468749+00:00') # TODO remove this.
    accepted = HiddenField(id='accepted',
                           name='accepted',
                           validators=[InputRequired(), ValidDatetime()],
                           default='2022-09-30T06:49:20.468749+00:00') # TODO remove this.
    auth = HiddenField(id='auth',
                       name='auth',
                       validators = [InputRequired()])
    email = EmailField(id='email',
                       name='email',
                       validators=[InputRequired(), Email()])
    # NOTE: A relatively new version of wtforms allows choices to be a
    # a list of triples in order to set the 'disabled' attribute on a choice.
    # We do not rely upon this, using javascript in the browser to
    # disable some fields upon load. We later validate combination of
    # engine and venue in the validate() method.
    engine = SelectField(label='LaTeX engine to use',
                         id='engine',
                         name='engine',
                         choices=[('lualatex', 'lualatex (required for iacrcc class)'),
                                  ('pdflatex', 'pdflatex'),
                                  ('xelatex', 'xelatex')],
                         default = 'lualatex')
    zipfile = FileField(id='zipfile',
                        name='zipfile',
                        validators=[FileRequired(), FileAllowed(['zip'])])
    submit = SubmitField('Upload')

    def create_hmac(self):
        # Note that all fields have default values.
        val = ''.join([self.paperid.data,
                       self.version.data,
                       self.submitted.data,
                       self.accepted.data])
        # TODO add this when we go live, since the dropdowns to
        # select them will disappear.
        # self.venue.data])
        return hmac.new(bytes(app.config['AUTHKEY'], 'utf-8'),
                        bytes(val, 'utf-8'),
                        hashlib.sha256).hexdigest()

    def validate(self, extra_validators=None):
        """Basic validation on a GET. extra validators may be used on POST."""
        if not super().validate():
            logging.warning('failed to validate: ' + str(self.errors))
            return False
        if (self.venue.data == 'iacrcc' and
            self.engine.data != 'lualatex'):
            self.engine.errors.append('lualatex is required for iacrcc')
            return False
        return hmac.compare_digest(self.auth.data, self.create_hmac())
