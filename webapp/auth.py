"""Blueprint for login, logout, and password changes.  We may
eventually enable signup and password recovery, but for now these
functions are reserved for admins only because I don't want to deal
with complicated captchas, rate limiting, and annoyance.
"""
from datetime import datetime
from flask import Blueprint, flash, abort, redirect, request, render_template, url_for
from flask_login import login_user, logout_user, login_required, current_user
#from . import User
from .db_models import User, Role
from . import db, login_manager, validate_hmac
from .forms import LoginForm, PasswordForm
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
                return redirect('/')
        flash("Invalid username/password combination")
        return redirect(url_for("auth.login"))
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You were logged out')
    return redirect('/')

@auth_bp.route('/confirm_email/<email>/<auth>', methods=['GET'])
def confirm_email(email, auth):
    """This just sets the last_login time."""
    if not validate_hmac(email, '', auth):
        return 'Invalid url'
    user = User.query.filter_by(email=email).first()
    if not user:
        return 'Unknown user'
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
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(password=form.old_password.data):
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
