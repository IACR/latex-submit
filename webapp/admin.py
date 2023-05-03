"""These routes are for admin only, and therefoer have the
admin_required decorator on them. All routes should start with /admin."""
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask import current_app as app
from flask_login import login_required, current_user
from flask_mail import Message
import json
import os
import secrets
import string
from pathlib import Path
from . import db, create_hmac, mail
from .metadata.compilation import Compilation, PaperStatus
from .metadata import validate_paperid
from .db_models import Role, User, validate_version
from .forms import AdminUserForm, RecoverForm
from functools import wraps

# decorator for views that require admin role.
def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if current_user.role == Role.ADMIN:
            return f(*args, **kwargs)
        else:
            flash('You need to be an admin to view that page')
            return redirect('/')
    return wrap

def admin_message(data):
    return app.jinja_env.get_template('admin/message.html').render(data)

admin_bp = Blueprint('admin_file', __name__)

@admin_bp.route('/admin/')
@login_required
@admin_required
def show_admin_home():
    papertree = {} # paperid -> version -> compilation
    errors = []
    for paperpath in Path(app.config['DATA_DIR']).iterdir():
        versions = {}
        for v in paperpath.iterdir():
            if v.is_dir() and validate_version(v.name):
                try:
                    cstr = (v / Path('compilation.json')).read_text(encoding='UTF-8')
                    versions[v.name] = {'url': url_for('home_bp.view_results',
                                                       paperid=paperpath.name,
                                                       version=v.name,
                                                       auth=create_hmac(paperpath.name,
                                                                        v.name,
                                                                        '',
                                                                        ''),
                                                       _external=True),
                                        'comp': Compilation.parse_raw(cstr)}
                except Exception as e:
                    errors.append(str(v) + ':' + str(e))
        papertree[paperpath.name] = versions
    data = {'title': 'IACR CC Upload Admin Home',
            'errors': errors,
            'papers': papertree}
    return render_template('admin/home.html', **data)

@admin_bp.route('/admin/view/<paperid>')
@login_required
@admin_required
def show_admin_paper(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    status_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path('status.json')
    if not status_path.is_file():
        return admin_message('Unknown paper: {}'.format(paperid))
    try:
        status = PaperStatus.parse_raw(status_path.read_text(encoding='UTF-8'))
    except Exception as e:
        return admin_message('Unable to parse status:{}'.format(str(status_path)))
    data = {'title': 'Viewing {}'.format(paperid),
            'paper': status}
    return render_template('admin/view.html', **data)

@admin_bp.route('/admin/allusers', methods=['GET'])
@login_required
@admin_required
def all_users():
    data = {'title': 'All users',
            'all_users': User.query.all()}
    return render_template('admin/all_users.html', **data)

def _generate_password():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(12))

@admin_bp.route('/admin/user', methods=['GET', 'POST'])
@login_required
@admin_required
def user():
    """Used for editing a user or creating a new user. At this time, users
       may not signup themselves."""
    form = AdminUserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.old_email.data).first()
        if user:
            user.email = form.email.data
            if form.delete_cb.data: # delete the user
                if form.old_email.data == current_user.email:
                    return redirect(url_for('admin_file.all_users'))
                db.session.delete(user)
                db.session.commit()
            else: # change role or email.
                if user.role != form.role.data:
                    flash('User role changed from {} to {}'.format(user.role,
                                                                   form.role.data))
                    user.role = form.role.data
                    app.logger.info('role of {} changed to {}'.format(user.email, form.old_email.data, ))
                if user.email != form.old_email.data:
                    flash('User email changed from {} to {}'.format(form.old_email.data,
                                                                    form.email.data))
                    app.logger.info('email changed from {} to {}'.format(user.email, form.old_email.data, ))
                db.session.add(user)
                db.session.commit()
        else: # create a new user.
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('That user already exists')
                return redirect(url_for('admin_file.user'))
            password = _generate_password()
            user = User(email=form.email.data,
                        role=form.role.data,
                        password=password)
            db.session.add(user)
            db.session.commit()
            # notify the user by email.
            subject = 'New account for {} on {}'.format(user.email,
                                                        app.config['SITE_NAME'])
            msg = Message(subject,
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=['iacrcc@digicrime.com'])
            maildata = {'email': user.email,
                        'servername': app.config['SITE_NAME'],
                        'password': password,
                        'confirm_url': url_for('auth.confirm_email',
                                               email=user.email,
                                               auth=create_hmac(user.email,'', '', ''),
                                               _external=True)}
            msg.body = app.jinja_env.get_template('admin/new_account.txt').render(maildata)
            if 'TESTING' in app.config:
                print(msg.body)
            mail.send(msg)
            flash('User {} was created and they were notified.'.format(form.email.data))
            app.logger.info('user {} was created; redirecting'.format(form.email.data))
        return redirect(url_for('admin_file.all_users'))
    args = request.args.to_dict()
    if args.get('id'):
        # in this case, edit an existing user.
        user = User.query.filter_by(id=args.get('id')).first()
        if user:
            form.email.data = user.email
            form.old_email.data = user.email
            form.role.data = user.role
            form.submit.label.text = 'Update'
        else:
            flash('no such user {}'.format(args.get('id')))
    return render_template('admin/user.html', form=form)

@admin_bp.route('/admin/recover', methods=['POST', 'GET'])
@login_required
@admin_required
def recover():
    """This is behind /admin so we don't have to deal with captchas.
    It sets the password to something random, and sends an email to the owner
    of the account.
    """
    form = RecoverForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash('Unknown user')
            return redirect(url_for('admin_file.all_users'))
        # Change the password for the user and send them an email.
        password = _generate_password()
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        subject = 'Account recovery on {} for {}'.format(app.config['SITE_NAME'],
                                                         form.email.data)
        msg = Message(subject,
                      sender=app.config['EDITOR_EMAILS'],
                      recipients=[form.email.data])
        maildata = {'email': user.email,
                    'servername': app.config['SITE_NAME'],
                    'password': password,
                    'recover_url': url_for('auth.confirm_email',
                                           email=user.email,
                                           auth=create_hmac(user.email, '', '', ''),
                                           _external=True)}
        msg.body = app.jinja_env.get_template('admin/recover_password.txt').render(maildata)
        mail.send(msg)
        flash('User {} password was changed and they were notified'.format(form.email.data))
        app.logger.info('user {} had their password changed'.format(form.email.data))
        return redirect(url_for('admin_file.all_users'))
    args = request.args.to_dict()
    email = args.get('email')
    if not email:
        flash('missing email parameter for /recover')
        return redirect(url_for('admin_bp.all_users'))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Unknown user')
        return redirect(url_for('admin_file.all_users'))
    form.email.data = user.email
    return render_template('admin/recover.html', form=form)
