from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, Email, EqualTo, Length
from wtforms import EmailField, PasswordField, SubmitField, BooleanField

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(),
                                            Email(message='Enter a valid email')])
    password = PasswordField('Password', validators=[InputRequired(message='Password must be at least 8 characters')])
    submit = SubmitField('Login')

class SignupForm(FlaskForm):
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
