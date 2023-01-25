"""Some forms are here as WTF forms."""

from flask import current_app as app
from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, Email, EqualTo, Length
from wtforms import EmailField, PasswordField, SubmitField, BooleanField, HiddenField, SelectField
from .db_models import Role

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
