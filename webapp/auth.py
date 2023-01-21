"""
Blueprint for login and logout.
"""
from flask import Blueprint, flash, abort, redirect, request, render_template, url_for
from flask_login import login_user, logout_user, login_required, current_user
#from . import User
from .db_models import User, Role
from . import db, login_manager
from .forms import LoginForm, SignupForm
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
            login_user(user)
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

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    return "Signup isn't active yet"

@login_manager.user_loader
def load_user(userid):
    """Check if user is logged-in upon page load."""
    if userid is not None:
        return User.query.get(userid)
    return None
