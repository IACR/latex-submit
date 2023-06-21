"""These routes are for admin only, and therefoer have the
admin_required decorator on them. All routes should start with /admin."""
from difflib import HtmlDiff
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, jsonify
from flask import current_app as app
from sqlalchemy import select
from flask_login import login_required, current_user
from flask_mail import Message
import json
import os
import secrets
import string
from pathlib import Path
from . import db, create_hmac, mail
from .metadata.compilation import Compilation, PaperStatusEnum
from .metadata import validate_paperid
from .db_models import Role, User, validate_version, PaperStatus, Discussion, Version, LogEvent, DiscussionStatus, Discussion, Journal
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

def admin_message(msg):
    return app.jinja_env.get_template('admin/message.html').render({'msg': msg})

admin_bp = Blueprint('admin_file', __name__)

@admin_bp.route('/admin/')
@login_required
@admin_required
def show_admin_home():
    papertree = {} # paperid -> version -> compilation
    errors = []
    journals = db.session.execute(select(Journal)).scalars()
    papers = db.session.execute(select(PaperStatus)).scalars()
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
            'journal_name': app.config['SITE_SHORTNAME'],
            'papertree': papertree,
            'papers': papers,
            'journals': journals}
    return render_template('admin/home.html', **data)

@admin_bp.route('/admin/view/<paperid>')
@login_required
@admin_required
def show_admin_paper(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: paper_status = PaperStatus.query.filter_by(paperid=paperid).first()
    if not paper_status:
        return admin_message('Unknown paper: {}'.format(paperid))
    sql = select(LogEvent).filter_by(paperid=paperid)
    events = db.session.execute(sql).scalars().all()
    data = {'title': 'Viewing {}'.format(paperid),
            'paper': paper_status,
            'events': events}
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
        sql = select(User).filter_by(email=form.old_email.data)
        user = db.session.execute(sql).scalar_one_or_none()
        # Legacy API: user = User.query.filter_by(email=form.old_email.data).first()
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
            sql = select(User).filter_by(email=form.email.data)
            existing_user = db.session.execute(sql).scalar_one_or_none()
            # Legacy API: existing_user = User.query.filter_by(email=form.email.data).first()
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
                  recipients=['iacrcc@digicrime.com',form.email.data])
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
        sql = select(User).filter_by(id=args.get('id'))
        user = db.session.execute(sql).scalar_one_or_none()
        # Legacy API: user = User.query.filter_by(id=args.get('id')).first()
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
        sql = select(User).filter_by(email=form.email.data)
        user = db.session.execute(sql).scalar_one_or_none()
        # Legacy API: user = User.query.filter_by(email=form.email.data).first()
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
    sql = select(User).filter_by(email=email)
    user = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: user = User.query.filter_by(email=email).first()
    if not user:
        flash('Unknown user')
        return redirect(url_for('admin_file.all_users'))
    form.email.data = user.email
    return render_template('admin/recover.html', form=form)

@admin_bp.route('/admin/copyedit/<paperid>', methods=['GET'])
@login_required
@admin_required
def copyedit(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: paper_status = PaperStatus.query.filter_by(paperid=paperid).first()
    if not paper_status:
        return admin_message('Unknown paper: {}'.format(paperid))
    comp_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.CANDIDATE.value) / Path('compilation.json')
    compilation = Compilation.parse_file(comp_path)
    data = {'title': 'Viewing {}'.format(paperid),
            'warnings': compilation.warning_log,
            'log': compilation.log,
            'pdf_auth': create_hmac(paperid, 'copyedit', '', ''),
            'paper': paper_status}
    return render_template('admin/copyedit.html', **data)

@admin_bp.route('/admin/approve_final/<paperid>', methods=['POST'])
@login_required
@admin_required
def approve_final(paperid):
    """Called when the final version is approved."""
    return admin_message('This isn\'t finished yet')

@admin_bp.route('/admin/final_review/<paperid>', methods=['GET'])
@login_required
@admin_required
def final_review(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: paper_status = PaperStatus.query.filter_by(paperid=paperid).first()
    if not paper_status:
        return admin_message('Unknown paper: {}'.format(paperid))
    candidate_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.CANDIDATE.value)
    final_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.FINAL.value)
    diffs = {}
    candidate_tex_files = list(candidate_path.glob('output/**/*.tex'))
    candidate_tex_files.extend(list(candidate_path.glob('output/**/*.sty')))
    candidate_output = candidate_path / Path('output')
    candidate_file_map = {str(path.relative_to(candidate_output)): path for path in candidate_tex_files}
    final_tex_files = list(final_path.glob('output/**/*.tex'))
    final_tex_files.extend(list(final_path.glob('output/**/*.sty')))
    final_output = final_path / Path('output')
    final_file_map = {str(path.relative_to(final_output)): path for path in final_tex_files}
    for filename, file in candidate_file_map.items():
        final_file = final_file_map.get(filename)
        if final_file:
            candidate_lines = file.read_text(encoding='UTF-8').splitlines()
            final_lines = final_file.read_text(encoding='UTF-8').splitlines()
            if candidate_lines != final_lines:
                htmldiff = HtmlDiff(tabsize=2)
                diffs[filename] = htmldiff.make_table(candidate_lines, final_lines, fromdesc='Original', todesc='Final version', context=True, numlines=5)
            del final_file_map[filename]
        else:
            diffs[filename] = 'File was removed'
    for filename, file in final_file_map.items():
        diffs[filename] = 'File is new'
    compilation = Compilation.parse_file(final_path / Path('compilation.json'))
    sql = select(Discussion).filter_by(paperid=paperid)
    items = db.session.execute(sql).scalars().all()
    data = {'title': 'Final review on paper # {}'.format(paperid),
            'warnings': compilation.warning_log,
            'log': compilation.log,
            'discussion': items,
            'pdf_copyedit_auth': create_hmac(paperid, 'copyedit', '', ''),
            'pdf_final_auth': create_hmac(paperid, 'final', '', ''),
            'diffs': diffs,
            'paper': paper_status}
    return render_template('admin/final_review.html', **data)

@admin_bp.route('/admin/finish_copyedit', methods=['POST'])
@login_required
@admin_required
def finish_copyedit():
    args = request.form.to_dict()
    paperid = args.get('paperid')
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if not paper_status:
        return admin_message('Unknown paper: {}'.format(paperid))
    paper_status.status = PaperStatusEnum.EDIT_FINISHED.value
    db.session.add(paper_status)
    db.session.commit()
    numitems = db.session.query(Discussion).filter_by(paperid=paperid,status=DiscussionStatus.PENDING).count()
    msg = Message('Copy editing was finished on your paper',
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=[paper_status.email])
    maildata = {'journal_name': app.config['JOURNAL_NAME'],
                'paperid': paperid,
                'numitems': numitems,
                'pdf_auth': create_hmac(paperid, 'copyedit', '', ''),
                'final_url': url_for('home_bp.view_copyedit', paperid=paperid,auth=create_hmac(paperid, Version.COPYEDIT.value, '', ''),
                                     _external=True)}
    msg.body = app.jinja_env.get_template('admin/copyedit_finished.txt').render(maildata)
    if 'TESTING' in app.config:
        print(msg.body)
    mail.send(msg)
    return redirect(url_for('admin_file.copyedit_home'), code=302)

@admin_bp.route('/admin/copyedit', methods=['GET'])
@login_required
@admin_required
def copyedit_home():
    papers = PaperStatus.query.filter((PaperStatus.status == PaperStatusEnum.EDIT_PENDING) |
                                      (PaperStatus.status == PaperStatusEnum.EDIT_FINISHED)).all()
    data = {'title': 'Papers for copy editing',
            'papers': papers}
    return render_template('admin/copyedit_home.html', **data)

@admin_bp.route('/admin/comments/<paperid>', methods=['GET'])
@login_required
@admin_required
def comments(paperid):
    if not validate_paperid(paperid):
        return jsonify([])
    sql = select(Discussion).filter_by(paperid=paperid)
    notes = db.session.execute(sql).scalars().all()
    # notes = Discussion.query.filter(paperid==paperid).all()
    return jsonify([n.as_dict() for n in notes])

@admin_bp.route('/admin/comment', methods=['POST'])
@login_required
@admin_required
def comment():
    """This is for handling copy editing comments."""
    data = request.json
    print('data=' + json.dumps(data))
    try:
        action = data['action']
        if action == 'delete':
            db.session.query(Discussion).filter(Discussion.id==data['id']).delete()
            db.session.commit()
            return jsonify({'id': data['id']})
        elif action == 'add':
            d = Discussion(paperid=data['paperid'],
                           creator_id=data['creator_id'],
                           pageno=data['pageno'],
                           lineno=data['lineno'],
                           text=data['text'])
            db.session.add(d)
            db.session.commit()
            return jsonify(d.as_dict())
    except Exception as e:
        return jsonify({'error': str(e)})
