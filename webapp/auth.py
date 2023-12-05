"""Blueprint for login, logout, and password changes.  We may
eventually enable signup and password recovery, but for now these
functions are reserved for admins only because I don't want to deal
with complicated captchas, rate limiting, and annoyance.
"""
from datetime import datetime
from flask import Blueprint, flash, abort, redirect, request, render_template, url_for
from flask import current_app as app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from .metadata.db_models import User, Role
from . import db, login_manager, validate_hmac, mail, create_hmac
from .forms import LoginForm, PasswordForm, RecoverForm, CaptchaForm
import random
from sqlalchemy import select
import time
from urllib.parse import urlparse, urljoin

auth_bp = Blueprint('auth', __name__)

def is_safe_url(target):
    """Determine if a url is safe to redirect to."""
    base_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and base_url.netloc == test_url.netloc

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(password=form.password.data):
            user.last_login = datetime.now()
            login_user(user)
            db.session.add(user)
            db.session.commit()
            next = request.args.get('next')
            if next:
                if not is_safe_url(next):
                    abort(400)
                return redirect(next)
            else:
                return redirect(url_for('admin_file.show_admin_home'))
        flash("Invalid username/password combination")
        return redirect(url_for("auth.login"))
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You were logged out')
    return redirect('/')

@auth_bp.route('/confirm_email/<email>/<auth>/<ts>', methods=['GET'])
def confirm_email(email, auth, ts):
    """This just sets the last_login time."""
    if not validate_hmac([email, ts], auth):
        flash('Invalid url')
        return redirect(url_for('home_bp.home'))
    if time.time() > int(ts) + 172800: # 48 hour expiration.
        flash('URL has expired. Request a new one at /recover')
        return redirect(url_for('home_bp.home'))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Unknown user')
        return redirect(url_for('home_bp.home'))
    user.last_login = datetime.now()
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for('auth.change_password'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordForm()
    form.email.data = current_user.email
    if form.validate_on_submit():
        user = User.query.filter_by(email=current_user.email).first()
        if user:
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            return redirect('/')
        else:
            flash('Invalid username and/or old password')
            return redirect(url_for('auth.change_password'))
    return render_template('change_password.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Currently disabled."""
    return 'Signup is not available'

@login_manager.user_loader
def load_user(userid):
    """Check if user is logged-in upon page load."""
    if userid is not None:
        return User.query.get(userid)
    return None

def _send_login_link(initiator, email):
    sql = select(User).filter_by(email=email)
    user = db.session.execute(sql).scalar_one_or_none()
    if not user:
        return False
    subject = 'Account recovery on {} for {}'.format(app.config['SITE_NAME'],
                                                     email)
    msg = Message(subject,
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=[email])
    ts = int(time.time())
    maildata = {'initiator': initiator,
                'email': email,
                'servername': app.config['SITE_NAME'],
                'recover_url': url_for('auth.confirm_email',
                                       email=email,
                                       ts=ts,
                                       auth=create_hmac([email, str(ts)]),
                                       _external=True)}
    msg.body = app.jinja_env.get_template('recover_password.txt').render(maildata)
    if app.config['TESTING']:
        print(msg.body)
    mail.send(msg)
    return True

_challenges = {
    'What is the first name of the D in DH?': [
        'Whitfield',
        'Whit'
    ],
    'What is the first name of the H in DH?': [
        'Margin',
        'Marty'
    ],
    'What is the first name of the A in RSA?': [
        'Adi',
        'adi'
    ],
    'What city is the Crypto conference always held in?': [
        'Goleta',
        'Santa Barbara'
    ],
    'What is the name of the website where people post preprints on cryptology?': [
        'eprint',
        'eprint.iacr.org',
        'Cryptology ePrint Archive'
    ],
    'What is the first name of one of the first editors-in-chief of Communications in Cryptology?': [
        'Joppe',
        'Andreas',
        'Andy'
    ],
    'What is the LaTeX document class used for the Communications in Cryptology?': [
        'iacrcc',
        'iacrcc.cls'
    ],
    'What is the name of the US Government agency responsible for government information security?': [
        'NSA',
        'National Security Agency'
    ]
}

@auth_bp.route('/recover', methods=['POST', 'GET'])
def recover():
    """This allows reset of a password by email. If the user isn't logged in,
    then it leads to a simple captcha page.
    """
    form = RecoverForm()
    if form.validate_on_submit():
        if current_user and current_user.is_authenticated:
            if not _send_login_link(current_user.email, form.email.data):
                flash('Unknown user')
                return redirect(url_for('home_bp.home'))
            flash('User {} was sent a link to login and change their password'.format(form.email.data))
            app.logger.info('Login link for user {} requested by {}'.format(form.email.data,
                                                                            current_user.email))
            return redirect(url_for('home_bp.home'))
        else: # show them a captcha
            auth = create_hmac([form.email.data, form.email.data])
            return redirect(url_for('auth.captcha', email=form.email.data, auth=auth))
    args = request.args.to_dict()
    if 'email' in args:
        form.email.data = args.get('email')
    return render_template('recover.html', form=form)


@auth_bp.route('/captcha', methods=['GET', 'POST'])
def captcha():
    time.sleep(2)
    form = CaptchaForm()
    if form.validate_on_submit():
        email = form.email.data
        if not validate_hmac([email, email], form.auth.data):
            flash('Invalid request')
            return redirect(url_for('home_bp.home'))
        challenge = form.challenge.data
        if challenge not in _challenges:
            flash('Invalid challenge')
            return redirect(url_for('home_bp.home'))
        response = form.response.data.strip()
        if response not in _challenges.get(challenge):
            flash('Invalid response')
            return redirect(url_for('home_bp.home'))
        if _send_login_link('An anonymous request', form.email.data):
            flash('A login link was sent to user {}'.format(form.email.data))
            return redirect(url_for('home_bp.home'))
        flash('Invalid request format')
        return redirect(url_for('home_bp.home'))
    args = request.args.to_dict()
    if 'email' in args and 'auth' in args:
        form.email.data = args.get('email')
        form.auth.data = args.get('auth')
        # construct the challenge from auth.
        index = 1
        for c in form.auth.data:
            if c.isdigit():
                index += int(c)
        keys = list(_challenges.keys())
        form.challenge.data = keys[index % len(keys)]
        return render_template('captcha.html', form=form)
    flash('Invalid request')
    return redirect(url_for('home_bp.home'))
