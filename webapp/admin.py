"""These routes are for admin only, and therefoer have the
admin_required decorator on them. All routes should start with /admin."""
from datetime import datetime, date
from difflib import HtmlDiff
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, jsonify
from flask import current_app as app
from sqlalchemy import select, or_, and_
from sqlalchemy.sql import func
from flask_login import login_required, current_user
from flask_mail import Message
import hashlib, hmac
import json
import os
from pathlib import Path
import time
from . import db, create_hmac, mail, generate_password, task_queue, paper_key, executor
from .metadata.compilation import Compilation, CompileStatus
from .metadata import validate_paperid
from .metadata.db_models import Role, User, validate_version, PaperStatus, PaperStatusEnum, Discussion, Version, LogEvent, DiscussionStatus, Discussion, Journal, Issue, Volume, CompileRecord, TaskStatus, log_event, NO_HOTCRP
from .forms import AdminUserForm, MoreChangesForm, PublishIssueForm, ChangeIssueForm, ChangePaperNumberForm
from .tasks import run_latex_task
from .routes import context_wrap
from functools import wraps
import shutil
import urllib

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
    errors = []
    journals = db.session.execute(select(Journal)).scalars().all()
    papers = db.session.execute(select(PaperStatus).order_by(PaperStatus.lastmodified.desc())).scalars().all()
    data = {'title': 'IACR CC Upload Admin Home',
            'errors': errors,
            'journal_name': app.config['SITE_SHORTNAME'],
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
    if not paper_status:
        return admin_message('Unknown paper: {}'.format(paperid))
    issue = db.session.execute(select(Issue).where(Issue.id==paper_status.issue_id)).scalar_one_or_none()
    sql = select(LogEvent).filter_by(paperid=paperid)
    events = db.session.execute(sql).scalars().all()
    paper_path = Path(app.config['DATA_DIR']) / Path(paperid)
    discussion = db.session.execute(select(Discussion).where(Discussion.paperid==paperid)).scalars().all()
    versions = {}
    for v in paper_path.iterdir():
        if v.is_dir() and validate_version(v.name):
            if v.name == Version.CANDIDATE:
                url = url_for('home_bp.view_results',
                              paperid=paper_path.name,
                              version=v.name,
                              auth=create_hmac([paper_path.name,
                                                v.name]))
            elif v.name == Version.COPYEDIT:
                url = url_for('admin_file.copyedit',
                              paperid=paper_path.name)
            else: # final
                url = url_for('admin_file.final_review',
                              paperid = paper_path.name)
            try:
                cstr = (v / Path('compilation.json')).read_text(encoding='UTF-8')
                versions[v.name] = {'url': url,
                                    'comp': Compilation.model_validate_json(cstr)}
            except Exception as e:
                errors.append(str(v) + ':' + str(e))
    data = {'title': 'Paper status: {}'.format(paperid),
            'paper_status': paper_status,
            'issue': issue,
            'versions': versions,
            'discussion': discussion,
            'events': events}
    return render_template('admin/view.html', **data)

@admin_bp.route('/admin/allusers', methods=['GET'])
@login_required
@admin_required
def all_users():
    data = {'title': 'All users',
            'all_users': User.query.all()}
    return render_template('admin/all_users.html', **data)

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
            password = generate_password()
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
                  recipients=[form.email.data])
            timestamp = str(int(time.time()))
            maildata = {'email': user.email,
                        'servername': app.config['SITE_NAME'],
                        'password': password,
                        'confirm_url': url_for('auth.confirm_email',
                                               email=user.email,
                                               auth=create_hmac([user.email, timestamp]),
                                               ts=timestamp,
                                               _external=True)}
            msg.body = app.jinja_env.get_template('admin/new_account.txt').render(maildata)
            if app.config['TESTING']:
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
        if user:
            form.email.data = user.email
            form.old_email.data = user.email
            form.role.data = user.role
            form.submit.label.text = 'Update'
        else:
            flash('no such user {}'.format(args.get('id')))
    return render_template('admin/user.html', form=form)

def _copyedit_url(paperid: str, status: PaperStatusEnum) -> str:
    """A paper can have several admin views on the copy editing, depending on
       what the status is. This includes first copyedit and approve_final."""
    if (status == PaperStatusEnum.EDIT_PENDING.name or
        status == PaperStatusEnum.EDIT_REVISED.name or
        status == PaperStatusEnum.EDIT_FINISHED.name):
        return url_for('admin_file.copyedit', paperid=paperid)
    if (status == PaperStatusEnum.FINAL_SUBMITTED.name or
        status == PaperStatusEnum.COPY_EDIT_ACCEPT.name or
        status == PaperStatusEnum.PUBLISHED.name):
        return url_for('admin_file.final_review', paperid=paperid)
    return None

@admin_bp.route('/admin/copyedit/<paperid>', methods=['GET'])
@login_required
@admin_required
def copyedit(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if not paper_status:
        return admin_message('Unknown paper: {}'.format(paperid))
    paper_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.CANDIDATE.value)
    input_dir = paper_path / Path('input')
    input_files = sorted([str(p.relative_to(str(input_dir))) for p in input_dir.rglob('*') if p.is_file()])
    comp_path = paper_path / Path('compilation.json')
    compilation = Compilation.model_validate_json(comp_path.read_text(encoding='UTF-8'))
    data = {'title': 'Viewing {}'.format(paperid),
            'comp': compilation,
            'input_files': input_files,
            'version': Version.CANDIDATE.value,
            'warnings': compilation.warning_log,
            'source_auth': create_hmac([paperid, Version.CANDIDATE.value]),
            'pdf_auth': create_hmac([paperid, 'copyedit']),
            'paper': paper_status}
    log_file = paper_path / Path('output') / Path('main.log')
    latexlog = log_file.read_text(encoding='UTF-8', errors='replace')
    data['loglines'] = latexlog.splitlines()
    return render_template('admin/copyedit.html', **data)

@admin_bp.route('/admin/approve_final', methods=['POST'])
@login_required
@admin_required
def approve_final():
    """Called when the final version is approved by the copy editor."""
    args = request.form.to_dict()
    if 'paperid' not in args:
        return admin_message('Missing paperid!')
    paperid = args.get('paperid')
    paper_status = db.session.execute(select(PaperStatus).filter_by(paperid=paperid)).scalar_one_or_none()
    if not paper_status:
        return admin_message('Missing PaperStatus for paperid {}'.format(paperid))
    paper_status.status = PaperStatusEnum.COPY_EDIT_ACCEPT
    paper_status.lastmodified = datetime.now()
    db.session.add(paper_status)
    db.session.commit()
    log_event(db, paperid, 'Final version approved for publication')
    editor_msg = Message('Copy edit changes approved for {}'.format(paperid),
                         sender=app.config['EDITOR_EMAILS'],
                         recipients=[app.config['EDITOR_EMAILS']])
    maildata = {'journal_name': paper_status.journal_key,
                'paperid': paperid,
                'issue_url': url_for('admin_file.copyedit_home', _external=True)}
    editor_msg.body = app.jinja_env.get_template('admin/copyedit_approved.txt').render(maildata)
    if app.config['TESTING']:
        print(editor_msg.body)
    mail.send(editor_msg)
    ############ send a message to the author.
    try:
        comp_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.FINAL.value) / Path('compilation.json')
        comp = Compilation.model_validate_json(comp_path.read_text(encoding='UTF-8'))
        maildata = {'paperid': paperid,
                    'paper_title': comp.meta.title,
                    'journal_name': paper_status.journal_key,
                    'volume': paper_status.volume_key,
                    'issue': paper_status.issue_key}
        author_msg = Message('Copy edit changes approved for {}'.format(paperid),
                             sender=app.config['EDITOR_EMAILS'],
                             recipients=[paper_status.email])
        author_msg.body = app.jinja_env.get_template('admin/author_finished.txt').render(maildata)
        if app.config['TESTING']:
            print(author_msg.body)
        mail.send(author_msg)
    except Exception as e:
        flash('Error in sending author email: ' + str(e))
    return redirect(url_for('admin_file.copyedit_home'), code=302)

@admin_bp.route('/admin/view_journal/<jid>', methods=['GET'])
@login_required
@admin_required
def view_journal(jid):
    journal = db.session.execute(select(Journal).where(Journal.id==jid)).scalar_one_or_none()
    if not journal:
        flash('No such journal')
        return redirect(url_for('admin_file.show_admin_home'))
    volume_info = db.session.execute(select(Volume.id, Volume.name).where(Volume.journal_id==jid)).all()
    volumes = [obj._asdict() for obj in volume_info]
    for volume in volumes:
        volume['issues'] = db.session.execute(select(Issue).where(Issue.volume_id==volume['id'])).scalars().all()
    papers = db.session.execute(select(PaperStatus).where(PaperStatus.journal_key==journal.hotcrp_key)).scalars().all()
    data = {'title': journal.name,
            'journal': journal,
            'volumes': volumes,
            'papers': papers}
    return render_template('admin/view_journal.html', **data)

def _get_hotcrp_papers(issue: Issue):
    """Fetch papers from hotcrp and return JSON."""
    # Get the last paper added for this issue, because that has the hotcrp instance id.
    if not issue.hotcrp or issue.hotcrp == NO_HOTCRP:
        return {'error': ''}
    try:
        conf_msg = ':'.join([issue.hotcrp, 'cic'])
        auth = hmac.new(app.config['HOTCRP_API_KEY'].encode('utf-8'),
                        conf_msg.encode('utf-8'), hashlib.sha256).hexdigest()
        url = 'https://submit.iacr.org/{}/iacr/api/papers.php?auth={}'.format(issue.hotcrp, auth)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            return data
    except Exception as e:
        app.logger.critical('unable to fetch paper info from hotcrp {}:{} '.format(url, str(e)))
        return {'error': 'unable to retrieve hotcrp papers: ' + str(e)}

@admin_bp.route('/admin/view_issue/<issueid>', methods=['GET'])
@login_required
@admin_required
def view_issue(issueid):
    issue = db.session.execute(select(Issue).where(Issue.id==issueid)).scalar_one_or_none()
    if not issue:
        flash('No such issue')
        return redirect(url_for('admin_file.show_admin_home'))
    papers = db.session.execute(select(PaperStatus).where(PaperStatus.issue_id != None).order_by(PaperStatus.paperno)).scalars().all()
    finished_papers = [p for p in papers if p.status == PaperStatusEnum.COPY_EDIT_ACCEPT]
    unassigned_sql = select(PaperStatus).where(PaperStatus.issue_id == None)
    unassigned_papers = db.session.execute(unassigned_sql).scalars().all()
    bumpform = ChangeIssueForm(nexturl=request.path)
    includeform = ChangeIssueForm(issueid=issueid,nexturl=request.path)
    papernoform = ChangePaperNumberForm(issueid=issueid)
    data = {'title': 'Status of Volume {}, Issue {}'.format(issue.volume.name, issue.name),
            'issue': issue,
            'volume': issue.volume,
            'finished_papers': len(finished_papers),
            'unassigned_papers': unassigned_papers,
            'journal': issue.volume.journal,
            'bumpform': bumpform,
            'papernoform': papernoform,
            'includeform': includeform,
            'papers': papers}
    hotcrp_papers = _get_hotcrp_papers(issue)
    if 'error' in hotcrp_papers:
        if hotcrp_papers['error']:
            flash(hotcrp_papers['error'])
    else:
        if hotcrp_papers['issue'] != issue.name:
            flash('Mismatch in hotcrp key: {}/{}'.format(hotcrp_papers['issue'],
                                                         issue.name))
        elif hotcrp_papers['volume'] != issue.volume.name:
            flash('Mismatch in volume hotcrp_key: {}/{}'.format(hotcrp_papers['volume'],
                                                                issue.volume.name))
        else:
            # go through the hotcrp papers and remove any that already have a PaperStatus in papers.
            paperids = set()
            for p in papers:
                paperids.add(p.paperid)
            accepted = hotcrp_papers.get('acceptedPapers')
            for p in accepted[:]: # loop over a copy of accepted
                if p['paperid'] in paperids:
                    accepted.remove(p)
            data['hotcrp'] = hotcrp_papers
    formdata = [{'paperid': p.paperid} for p in finished_papers]
    if len(finished_papers) == len(papers):
        data['form'] = PublishIssueForm(issueid=issue.id)
    return render_template('admin/view_issue.html', **data)

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
            candidate_lines = file.read_text(encoding='UTF-8', errors='replace').splitlines()
            final_lines = final_file.read_text(encoding='UTF-8', errors='replace').splitlines()
            if candidate_lines != final_lines:
                htmldiff = HtmlDiff(tabsize=2)
                diffs[filename] = htmldiff.make_table(candidate_lines, final_lines, fromdesc='Original', todesc='Final version', context=True, numlines=5)
            del final_file_map[filename]
        else:
            diffs[filename] = 'File was removed'
    for filename, file in final_file_map.items():
        diffs[filename] = 'File is new'
    comp_path = final_path / Path('compilation.json')
    compilation = Compilation.model_validate_json(comp_path.read_text(encoding='UTF-8'))
    sql = select(Discussion).filter_by(paperid=paperid).order_by(Discussion.created.desc())
    items = db.session.execute(sql).scalars().all()
    morechangesform = MoreChangesForm(paperid=paperid)
    data = {'title': 'Final review on paper # {}'.format(paperid),
            'comp': compilation,
            'morechangesform': morechangesform,
            'discussion': items,
            'pdf_copyedit_auth': create_hmac([paperid, 'copyedit']),
            'pdf_final_auth': create_hmac([paperid, 'final']),
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
    paper_status.lastmodified = datetime.now()
    db.session.add(paper_status)
    db.session.commit()
    numitems = db.session.query(Discussion).filter_by(paperid=paperid,status=DiscussionStatus.PENDING).count()
    msg = Message('Copy editing was finished on your paper',
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=[paper_status.email])
    maildata = {'journal_name': app.config['SITE_NAME'],
                'paperid': paperid,
                'numitems': numitems,
                'pdf_auth': create_hmac([paperid, 'copyedit']),
                'final_url': url_for('home_bp.view_copyedit', paperid=paperid,auth=create_hmac([paperid, Version.COPYEDIT.value]),
                                     _external=True)}
    msg.body = app.jinja_env.get_template('admin/copyedit_finished.txt').render(maildata)
    if app.config['TESTING']:
        print(msg.body)
    mail.send(msg)
    log_event(db, paperid, 'Copy edit was finished and author notified')
    return redirect(url_for('admin_file.copyedit_home'), code=302)

## This method is used if a paper is being sent back to the author for
## further changes after their first round of responses. In this case
## 1. The candidate version is replaced by the final version and the
##    final version is removed
## 2. The copyedit version is generated from the new candidate version.
## 3. All Discussion items are "archived" to indicate that the data in them
##    is not trustworthy because it depends on a previous compilation.
@admin_bp.route('/admin/request_more_changes', methods=['POST'])
@login_required
@admin_required
def request_more_changes():
    form = MoreChangesForm()
    if not form.validate_on_submit():
        return admin_message('Invalid form submission. This is a bug.')
    paperid = form.paperid.data
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if not paper_status:
        return admin_message('Unknown paper: {}'.format(paperid))
    paper_status.status = PaperStatusEnum.EDIT_REVISED
    now = datetime.now()
    paper_status.lastmodified = now
    db.session.add(paper_status)
    db.session.commit()
    sql = select(Discussion).where(and_(Discussion.paperid==paperid, Discussion.archived == None))
    items = db.session.execute(sql).scalars().all()
    for item in items:
        item.archived = now
        db.session.add(item)
    db.session.commit()
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    candidate_dir = paper_dir / Path(Version.CANDIDATE.value)
    shutil.rmtree(candidate_dir)
    final_dir = paper_dir / Path(Version.FINAL.value)
    shutil.move(final_dir, candidate_dir)
    candidate_sql = select(CompileRecord).where(and_(CompileRecord.paperid == paperid,
                                                     CompileRecord.version == Version.CANDIDATE))
    candidate_comprec = db.session.execute(candidate_sql).scalar_one_or_none()
    db.session.delete(candidate_comprec)
    db.session.commit()
    sql = select(CompileRecord).where(and_(CompileRecord.paperid == paperid,
                                           CompileRecord.version == Version.FINAL))
    comprec = db.session.execute(sql).scalar_one_or_none()
    # change the version of comprec to CANDIDATE
    comprec.version = Version.CANDIDATE
    last_compilation = Compilation.model_validate_json(comprec.result)
    db.session.add(comprec)
    db.session.commit()
    copyedit_dir = paper_dir / Path(Version.COPYEDIT.value)
    if copyedit_dir.is_dir():
        shutil.rmtree(copyedit_dir)
    copyedit_dir.mkdir(parents=True)
    # copy everything from candidate input_dir
    candidate_input_dir = candidate_dir / Path('input')
    copyedit_input_dir = copyedit_dir / Path('input')
    shutil.copytree(candidate_input_dir,
                    copyedit_input_dir)
    copyedit_file = copyedit_input_dir / Path('main.copyedit')
    copyedit_file.touch() # this iacrcc.cls to add line numbers.

    copyedit_comprec_sql = select(CompileRecord).where(and_(CompileRecord.paperid == paperid,
                                                            CompileRecord.version == Version.COPYEDIT))
    copyedit_comprec = db.session.execute(copyedit_comprec_sql).scalar_one_or_none()
    copyedit_comprec.task_status = TaskStatus.PENDING
    copyedit_comprec.started = now
    compilation = Compilation(**{'paperid': paperid,
                                 'venue': paper_status.journal_key,
                                 'status': CompileStatus.COMPILING,
                                 'version': Version.COPYEDIT.value,
                                 'email': last_compilation.email,
                                 'submitted': last_compilation.submitted,
                                 'accepted': last_compilation.accepted,
                                 'compiled': now,
                                 'command': last_compilation.command,
                                 'error_log': [],
                                 'warning_log': [],
                                 'zipfilename': last_compilation.zipfilename})
    command = last_compilation.command
    compstr = compilation.model_dump_json(indent=2, exclude_none=True)
    copyedit_comprec.result = compstr
    db.session.add(copyedit_comprec)
    db.session.commit()
    compilation_file = copyedit_dir / Path('compilation.json')
    compilation_file.write_text(compstr, encoding='UTF-8')
    # fire off a separate task to compile. We wrap run_latex_task so it
    # can have the flask context to use sqlalchemy on the database.
    task_key = paper_key(paperid, Version.COPYEDIT.value)
    task_queue[task_key] = executor.submit(context_wrap(run_latex_task),
                                           command,
                                           str(copyedit_dir.absolute()),
                                           paperid,
                                           last_compilation.meta.DOI,
                                           Version.COPYEDIT.value,
                                           task_key)
    status_url = url_for('home_bp.get_status',
                         paperid=paperid,
                         version=Version.COPYEDIT.value,
                         auth=create_hmac([paperid, Version.COPYEDIT.value]),
                         request_more='yes',
                         _external=True)
    data = {'title': 'Recompiling copy editor version',
            'status_url': status_url,
            'headline': 'Recompiling your paper with line numbers for the copy editor'}
    log_event(db, paperid, 'Another round of copy edit initiated')
    return render_template('running.html', **data)


@admin_bp.route('/admin/copyedit', methods=['GET'])
@login_required
@admin_required
def copyedit_home():
    """Show the list of papers with pending copy edit actions."""
    sql = select(PaperStatus).where(or_(PaperStatus.status == PaperStatusEnum.EDIT_PENDING,
                                        PaperStatus.status == PaperStatusEnum.EDIT_REVISED,
                                        PaperStatus.status == PaperStatusEnum.EDIT_FINISHED,
                                        PaperStatus.status == PaperStatusEnum.FINAL_SUBMITTED)).order_by(PaperStatus.lastmodified)
    statuses = db.session.execute(sql).scalars().all()
    papers = [p.as_dict() for p in statuses]
    for paper in papers:
        paper['url'] = _copyedit_url(paper['paperid'], paper['status']['name'])
    data = {'title': 'Papers for copy editing',
            'papers': papers}
    return render_template('admin/copyedit_home.html', **data)

@admin_bp.route('/admin/comments/<paperid>', methods=['GET'])
@login_required
@admin_required
def comments(paperid):
    if not validate_paperid(paperid):
        return jsonify([])
    sql = select(Discussion).filter_by(paperid=paperid).order_by(Discussion.created)
    notes = db.session.execute(sql).scalars().all()
    return jsonify([n.as_dict() for n in notes])

@admin_bp.route('/admin/comment', methods=['POST'])
@login_required
@admin_required
def comment():
    """This is for ajax to handle copy editing comments."""
    data = request.json
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
            if 'source_file' in data:
                d.source_file = data['source_file']
            if 'source_lineno' in data:
                d.source_lineno = data['source_lineno']
            if 'warning_id' in data:
                d.warning_id = data['warning_id']
            db.session.add(d)
            db.session.commit()
            return jsonify(d.as_dict())
    except Exception as e:
        return jsonify({'error': str(e)})

@admin_bp.route('/admin/publish_issue', methods=['POST'])
@login_required
@admin_required
def publish_issue():
    form = PublishIssueForm()
    if not form.validate_on_submit():
        return admin_message('Invalid form submission. This is a bug.')
    # TODO: Finish this. We should export the archive, set the papers to published, and set the published date
    # on the issue.
    return admin_message('The form was validated. We still need to finish the push to cic.iacr.org')

@admin_bp.route('/admin/change_issue', methods=['POST'])
@login_required
@admin_required
def change_issue():
    form = ChangeIssueForm()
    if not form.validate_on_submit():
        for key, value in form.errors:
            log_event(db, form.paperid.data, 'Submission error: {}:{}'.format(key, value))
        return admin_message('Invalid form submission. This is a bug.')
    paper_status = db.session.execute(select(PaperStatus).where(PaperStatus.paperid==form.paperid.data)).scalar_one_or_none()
    if not paper_status:
        return admin_message('Unknown paper {}'.format(form.paperid.data))
    if not form.issueid.data: # paper is being removed from its issue.
        paperno = paper_status.paperno
        issueid = paper_status.issue_id
        paper_status.paperno = None
        paper_status.issue_id = None
        db.session.add(paper_status)
        # renumber the papers.
        later_papers = db.session.execute(select(PaperStatus).where(and_(PaperStatus.paperno > paperno,
                                                                         PaperStatus.issue_id==issueid))).scalars().all()
        for paper in later_papers:
            paper.paperno = paperno
            paperno += 1
            db.session.add(paper)
        db.session.commit()
        return redirect(form.nexturl.data, code=302)
    # In this case we need to recompile the final version of the paper in order to incorporate
    # the issue and volume names.
    issue = db.session.execute(select(Issue).where(Issue.id == form.issueid.data)).scalar_one_or_none()
    if not issue:
        return admin_message('Unknown issue {}'.format(form.issueid.data))
    paper_status.issue_id = form.issueid.data
    papernum = db.session.execute(select(func.max(PaperStatus.paperno)).where(PaperStatus.issue_id==issue.id)).scalar_one_or_none()
    if papernum is None:
        paper_status.paperno = 1
    else:
        paper_status.paperno = 1 + papernum # put it at the end of the list.
    db.session.add(paper_status)
    db.session.commit()
    volume = issue.volume
    journal = volume.journal
    paperid = paper_status.paperid
    task_key = paper_key(paperid, 'final')
    if task_queue.get(task_key):
        log_event(db, paperid, 'Attempt to recompile while already compiling')
        return render_template('message.html',
                               title='Another one is running',
                               error='At most one compilation may be queued on each paper.')
    now = datetime.now()
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    final_dir = paper_dir / Path('final')
    compilation_file = final_dir / Path('compilation.json')
    compilation = Compilation.model_validate_json(compilation_file.read_text(encoding='UTF-8'))
    compilation.error_log = []
    compilation.warning_log = []
    compilation.compiled = now
    compilation.status = CompileStatus.COMPILING
    input_dir = final_dir / Path('input')
    output_dir = final_dir / Path('output')
    sql = select(CompileRecord).filter_by(paperid=paperid).filter_by(version='final')
    comprec = db.session.execute(sql).scalar_one_or_none()
    comprec.task_status = TaskStatus.PENDING
    comprec.started = now
    compstr = compilation.model_dump_json(indent=2, exclude_none=True)
    compilation_file.write_text(compstr, encoding='UTF-8')
    comprec.result = compstr
    db.session.add(comprec)
    db.session.commit()
    publishedDate = date.today().strftime('%Y-%m-%d')
    metadata = '\\def\\IACR@DOI{' + compilation.meta.DOI + '}\n'
    if journal.EISSN:
        metadata += '\\def\\IACR@EISSN{' + journal.EISSN + '}\n'
    metadata += '\\def\\IACR@Received{' + compilation.submitted[:10] + '}\n'
    metadata += '\\def\\IACR@Accepted{' + compilation.accepted[:10] + '}\n'
    metadata += '\\def\\IACR@Published{' + publishedDate + '}\n'
    metadata += '\\setvolume{' + volume.name + '}\n'
    metadata += '\\setnumber{' + issue.name + '}\n'
    metadata_file = input_dir / Path('main.iacrmetadata')
    metadata_file.write_text(metadata)
    # Remove output from any previous run.
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    # fire off a separate task to compile. We wrap run_latex_task so it
    # can have the flask context to use sqlalchemy on the database.
    log_event(db, paperid, 'Recmpiled for volume {} issue {}'.format(volume.name, issue.name))
    task_queue[task_key] = executor.submit(context_wrap(run_latex_task),
                                           compilation.command,
                                           str(final_dir.absolute()),
                                           paperid,
                                           'final',
                                           task_key)
    if form.nexturl.data:
        next_url = form.nexturl.data
    else:
        next_url = url_for('admin_file.view_issue', issueid=issue.id)
    status_url = url_for('home_bp.get_status',
                         paperid=paperid,
                         version=Version.FINAL.value,
                         auth=create_hmac([paperid, Version.FINAL.value]),
                         next=next_url,
                         _external=True)
    data = {'title': 'Recompiling final version',
            'status_url': status_url,
            'headline': 'Recompiling final version with volume and issue'}
    return render_template('running.html', **data)


@admin_bp.route('/admin/change_paperno', methods=['POST'])
@login_required
@admin_required
def change_paperno():
    """This is for increasing or decreasing the paperno on an individual paper."""
    form = ChangePaperNumberForm()
    if not form.validate_on_submit():
        for key, value in form.errors.items():
            log_event(db, form.paperid.data, 'paperno error: {}:{}'.format(key, value))
        flash('Invalid values')
        return admin_message('Invalid form submission. This is a bug.')
    paperid = form.paperid.data
    issueid = form.issueid.data
    paper_status = db.session.execute(select(PaperStatus).where(PaperStatus.paperid==paperid)).scalar_one_or_none()
    old_paperno = paper_status.paperno
    if form.upbutton.data: # decrease the paperno by one. This means the paper above it must be renumbered.
        new_paperno = old_paperno - 1
        if new_paperno < 1:
            # can't move it up
            return redirect(url_for('admin_file.view_issue', issueid=form.issueid.data), code=302)
        upper_paper = db.session.execute(select(PaperStatus).where(PaperStatus.paperno==new_paperno).where(PaperStatus.issue_id==issueid)).scalar_one_or_none()
        if upper_paper:
            upper_paper.paperno = new_paperno + 1
            paper_status.paperno = new_paperno
            db.session.add(upper_paper)
            db.session.add(paper_status)
        else:
            # This would be a bug.
            paperno = 0
            issue_papers = db.session.execute(select(PaperStatus).where(PaperStatus.issue_id==issueid)).scalars().all()
            for paper in issue_papers:
                paperno += 1
                paper.paperno = paperno
                db.session.add(paper)
            flash('There is a bug in paper numbers. They were reset')
    else: # increase the paper number by one.
        max_paperno = db.session.execute(select(func.max(PaperStatus.paperno)).where(PaperStatus.issue_id==issueid)).scalar_one_or_none()
        if old_paperno == max_paperno:
            # can't move it down
            return redirect(url_for('admin_file.view_issue', issueid=form.issueid.data), code=302)
        new_paperno = old_paperno + 1
        lower_paper = db.session.execute(select(PaperStatus).where(PaperStatus.paperno==new_paperno).where(PaperStatus.issue_id==issueid)).scalar_one_or_none()
        if lower_paper:
            lower_paper.paperno = old_paperno
            paper_status.paperno = new_paperno
            db.session.add(lower_paper)
            db.session.add(paper_status)
        else:
            # This would be a bug.
            paperno = 0
            issue_papers = db.session.execute(select(PaperStatus).where(PaperStatus.issue_id==issueid)).scalars().all()
            for paper in issue_papers:
                paperno += 1
                paper.paperno = paperno
                db.session.add(paper)
            flash('There is a bug in paper numbers. They were reset')
    db.session.commit()
    return redirect(url_for('admin_file.view_issue', issueid=form.issueid.data), code=302)
