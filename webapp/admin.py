"""These routes are for admin only, and therefoer have the
admin_required decorator on them. All routes should start with /admin."""
from datetime import datetime, date
from difflib import HtmlDiff
try:
    from .export import export_issue
except Exception as e:
    from export import export_issue
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, jsonify
from flask import current_app as app
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.sql import func
from flask_security import auth_required, current_user, roles_required, hash_password
from flask_security.confirmable import generate_confirmation_link
from flask_mail import Message
import hashlib, hmac
import json
import logging
import os
from pathlib import Path
import time
from . import db, create_hmac, mail, generate_password, task_queue, paper_key, executor, user_datastore
from .metadata.compilation import Compilation, CompileStatus
from .metadata import validate_paperid
from .metadata.db_models import Role, User, validate_version, PaperStatus, PaperStatusEnum, Discussion, Version, LogEvent, DiscussionStatus, Discussion, Journal, Issue, Volume, CompileRecord, TaskStatus, log_event, NO_HOTCRP
from .forms import AdminUserForm, MoreChangesForm, PublishIssueForm, ChangeIssueForm, ChangePaperNumberForm, CopyeditClaimForm, DeletePaperForm
from .tasks import run_latex_task
from .routes import context_wrap
from .bibmarkup import mark_bibtex

from functools import wraps
import shutil
import urllib

# We switched to using role-based access control with flask_security
# instead of flask_login.  We do not use user accounts for authors,
# but we use them for admins, editors, and copy editors. The
# check_paper_access() method is used to check that a user has
# permission to modify a paper.  We also use check_journal_access() to
# check that an editor or copyeditor has access to a journal. Some
# things are only accessible to the ADMIN role, and those are marked
# with @roles_required(Role.ADMIN).

def check_paper_access(paperid: str) -> tuple[PaperStatus, str]:
    """If str is not None, then access fails with that reason."""
    if not current_user.is_authenticated:
        return None, 'User is not authenticated'
    paper_status = db.session.execute(select(PaperStatus).where(PaperStatus.paperid==paperid)).scalar_one_or_none()
    if not paper_status:
        return None, 'Unknown paper ' + paperid
    if (current_user.has_role(Role.ADMIN) or
        current_user.has_role(Role.editor_role(paper_status.journal_key)) or
        current_user.has_role(Role.copyeditor_role(paper_status.journal_key))):
        return paper_status, None
    return None, 'User lacks authorization for article '

def check_journal_access(journal: Journal) -> bool:
    return (Role.ADMIN in current_user.roles or
            Role.editor_role(journal.hotcrp_key) in current_user.roles or
            Role.copyeditor_role(journal.hotcrp_key) in current_user.roles)

def admin_message(msg):
    return app.jinja_env.get_template('admin/message.html').render({'msg': msg})

admin_bp = Blueprint('admin_file', __name__)

def viewer_only() -> bool:
    for role in current_user.roles:
        if role.name == Role.ADMIN or 'editor' in role.name:
            return False
    return True    
              
@admin_bp.context_processor
def inject_view_only():
    return {
        'view_only': viewer_only()
        }

@admin_bp.route('/admin/')
@auth_required()
def show_admin_home():
    """Users see different things depending on the roles they have."""
    errors = []
    all_roles = db.session.execute(select(Role)).scalars().all()
    all_journals = db.session.execute(select(Journal)).scalars().all()
    journals = []
    if Role.ADMIN in current_user.roles:
        journals = all_journals
    else:
        for j in all_journals:
            if (Role.copyeditor_role(j.hotcrp_key) in current_user.roles or
                Role.editor_role(j.hotcrp_key) in current_user.roles or
                Role.viewer_role(j.hotcrp_key) in current_user.roles):
                journals.append(j)
    journals = [j.as_dict() for j in journals]
    view_only = viewer_only()
    if view_only:
        for j in journals:
            j['ojs_view'] = url_for('ojs_file.show_ojs_journal', hotcrp_key=j['hotcrp_key'])
    if current_user.has_role(Role.ADMIN):
        papers = db.session.execute(select(PaperStatus).order_by(PaperStatus.lastmodified.desc())).scalars().all()
    else:
        # we could just select the papers that the user has access to, but it's not necessary for the UX.
        papers = []
    data = {'title': 'Upload Admin Home',
            'all_roles': all_roles,
            'errors': errors,
            'journal_name': app.config['SITE_SHORTNAME'],
            'papers': papers,
            'journals': journals}
    return render_template('admin/home.html', **data)

@admin_bp.route('/admin/view/<paperid>')
@auth_required()
def show_admin_paper(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        flash(msg)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    issue = db.session.execute(select(Issue).where(Issue.id==paper_status.issue_id)).scalar_one_or_none()
    sql = select(LogEvent).filter_by(paperid=paperid)
    events = db.session.execute(sql).scalars().all()
    paper_path = Path(app.config['DATA_DIR']) / Path(paperid)
    discussion = db.session.execute(select(Discussion).where(Discussion.paperid==paperid)).scalars().all()
    versions = {}
    journal = db.session.execute(select(Journal).where(Journal.hotcrp_key == paper_status.journal_key)).scalar_one_or_none()
    if not paper_path.is_dir():
        return admin_message('Unable to open directory: ' + str(paper_path))
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
                flash('Error: {}:{}'.format(str(v), str(e)))
    data = {'title': 'Paper status: {}'.format(paperid),
            'paper_status': paper_status,
            'issue': issue,
            'versions': versions,
            'discussion': discussion,
            'journal': journal,
            'events': events}
    return render_template('admin/view.html', **data)

@admin_bp.route('/admin/allusers', methods=['GET'])
@auth_required()
@roles_required(Role.ADMIN)
def all_users():
    data = {'title': 'All users',
            'all_users': db.session.execute(select(User)).scalars().all()}
    return render_template('admin/all_users.html', **data)

@admin_bp.route('/admin/user', methods=['GET', 'POST'])
@auth_required()
@roles_required(Role.ADMIN)
def edit_user():
    """Used for editing a user or creating a new user. At this time, users
       may not signup themselves. This is controlled in the configuration setting
       SECURITY_REGISTERABLE"""
    form = AdminUserForm()
    if form.validate_on_submit():
        sql = select(User).filter_by(email=form.old_email.data)
        user = db.session.execute(sql).scalar_one_or_none()
        if user:
            user.email = form.email.data
            if form.delete_cb.data: # delete the user
                if form.old_email.data == current_user.email:
                    flash('You are unable to delete yourself')
                    return redirect(url_for('admin_file.all_users'))
                user_datastore.delete_user(user)
                user_datastore.commit()
                flash('User {} was removed'.format(user.email))
                return redirect(url_for('admin_file.all_users'))
            else: # change role or email or name.
                user_roles = [r.name for r in user.roles]
                if set(user_roles) != set(form.roles.data):
                    all_roles = db.session.execute(select(Role)).scalars().all()
                    all_roles = {r.name: r for r in all_roles}
                    for r in user_roles:
                        if r not in form.roles.data:
                            if r == Role.ADMIN and len(all_roles[r].users) == 1:
                                flash('Unable to remove the last admin user')
                                return redirect(url_for('admin_file.all_users'))
                            user.roles.remove(all_roles[r])
                    for r in form.roles.data:
                        if r not in user_roles:
                            user.roles.append(all_roles[r])
                if user.email != form.old_email.data:
                    flash('User email changed from {} to {}'.format(form.old_email.data,
                                                                    form.email.data))
                    app.logger.info('email changed from {} to {}'.format(user.email, form.old_email.data, ))
                if user.name != form.name.data:
                    user.name = form.name.data
                    flash('User name changed from {} to {}'.format(user.name,
                                                                   form.name.data))
                db.session.add(user)
                db.session.commit()
        else: # create a new user.
            sql = select(User).filter_by(email=form.email.data)
            existing_user = db.session.execute(sql).scalar_one_or_none()
            if existing_user:
                flash('That user already exists')
                return redirect(url_for('admin_file.user'))
            password = generate_password()
            udata = {'password': hash_password(password),
                     'name': form.name.data,
                     'email': form.email.data,
                     'roles': form.roles.data}
            user = user_datastore.create_user(**udata)
            user_datastore.commit()
            # notify the user by email.
            subject = 'New account for {} on {}'.format(user.email,
                                                        app.config['SITE_NAME'])
            msg = Message(subject,
                  sender=app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[form.email.data])
            timestamp = str(int(time.time()))
            link, token = generate_confirmation_link(user)
            maildata = {'email': user.email,
                        'servername': app.config['SITE_NAME'],
                        'password': password,
                        'confirm_url': link}
            msg.body = app.jinja_env.get_template('admin/new_account.txt').render(maildata)
            if app.config['DEBUG']:
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
            form.name.data = user.name
            form.roles.process_data([r.name for r in user.roles])
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
@auth_required()
def copyedit(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        flash(msg)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    paper_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.CANDIDATE.value)
    input_dir = paper_path / Path('input')
    input_files = sorted([str(p.relative_to(str(input_dir))) for p in input_dir.rglob('*') if p.is_file()])
    comp_path = paper_path / Path('compilation.json')
    compilation = Compilation.model_validate_json(comp_path.read_text(encoding='UTF-8'))
    claimform = CopyeditClaimForm(paperid=paperid,
                                  copyeditor=current_user.email,
                                  view='y')
    data = {'title': 'Copy edit on {} {}'.format(paperid, paper_status.title),
            'comp': compilation,
            'claimform': claimform,
            'paperid': paperid,
            'input_files': input_files,
            'version': Version.CANDIDATE.value,
            'warnings': compilation.warning_log,
            'source_auth': create_hmac([paperid, Version.CANDIDATE.value]),
            'pdf_auth': create_hmac([paperid, 'copyedit']),
            'paper': paper_status}
    log_file = paper_path / Path('output') / Path('main.log')
    latexlog = log_file.read_text(encoding='UTF-8', errors='replace')
    data['loglines'] = latexlog.splitlines()
    bibtex_log = paper_path / Path('output') / Path('main.blg')
    if bibtex_log.is_file():
        data['bibtex_log'] = bibtex_log.read_text(encoding='UTF-8', errors='replace').splitlines()
    else:
        data['bibtex_log'] = ['No bibtex log']
    if compilation.bibtex:
        data['marked_bibtex'] = mark_bibtex(compilation.bibtex)
    return render_template('admin/copyedit.html', **data)

@admin_bp.route('/admin/approve_final', methods=['POST'])
@auth_required()
def approve_final():
    """Called when the final version is approved by the copy editor."""
    args = request.form.to_dict()
    if 'paperid' not in args:
        return admin_message('Missing paperid!')
    paperid = args.get('paperid')
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        flash(msg)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    paper_status.status = PaperStatusEnum.COPY_EDIT_ACCEPT
    paper_status.lastmodified = datetime.now()
    if paper_status.issue_id:
        issue = paper_status.issue
        if issue and issue.exported:
            # In this case the issue for the paper was already exported, so we unassign the paper.
            paper_status.issue_id = None
            paper_status.paperno = None
    db.session.add(paper_status)
    db.session.commit()
    log_event(db, paperid, 'Final version approved for publication')
    users = journal.copyedit_contacts(db)
    recipients = [u.email for u in users]
    editor_msg = Message('Copy edit changes approved for {}'.format(paperid),
                         sender=app.config['MAIL_DEFAULT_SENDER'],
                         recipients=recipients)
    maildata = {'journal_name': paper_status.journal_key,
                'paperid': paperid,
                'copyedit_url': url_for('admin_file.copyedit_home', _external=True)}
    editor_msg.body = app.jinja_env.get_template('admin/copyedit_approved.txt').render(maildata)
    if app.config['DEBUG']:
        print(editor_msg.body)
    mail.send(editor_msg)
    ############ send a message to the author.
    try:
        comp_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.FINAL.value) / Path('compilation.json')
        comp = Compilation.model_validate_json(comp_path.read_text(encoding='UTF-8'))
        maildata = {'paperid': paperid,
                    'paper_title': comp.meta.title}
        author_msg = Message('Copy edit changes approved for {}'.format(paperid),
                             sender=app.config['MAIL_DEFAULT_SENDER'],
                             recipients=[paper_status.email])
        author_msg.body = app.jinja_env.get_template('admin/author_finished.txt').render(maildata)
        if app.config['DEBUG']:
            print(author_msg.body)
        mail.send(author_msg)
    except Exception as e:
        flash('Error in sending author email: ' + str(e))
    flash('Paper {} was approved for publication and author was notified'.format(paperid))
    return redirect(url_for('admin_file.copyedit_home'), code=302)

@admin_bp.route('/admin/view_journal/<jid>', methods=['GET'])
@auth_required()
def view_journal(jid):
    journal = db.session.execute(select(Journal).where(Journal.id==jid)).scalar_one_or_none()
    if not journal:
        flash('No such journal')
        return redirect(url_for('admin_file.show_admin_home'))
    if not check_journal_access(journal):
        flash('You do not have access to journal {}.'.format(journal.name))
        return redirect(url_for('home_bp.home'))
    volume_info = db.session.execute(select(Volume.id, Volume.name).where(Volume.journal_id==jid)).all()
    volumes = [obj._asdict() for obj in volume_info]
    for volume in volumes:
        volume['issues'] = db.session.execute(select(Issue).where(Issue.volume_id==volume['id'])).scalars().all()
    papers = db.session.execute(select(PaperStatus).where(PaperStatus.journal_key==journal.hotcrp_key).order_by(PaperStatus.lastmodified.desc())).scalars().all()
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
        journal = issue.volume.journal
        conf_msg = ':'.join([issue.hotcrp, journal.hotcrp_key])
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
@auth_required()
def view_issue(issueid):
    issue = db.session.execute(select(Issue).where(Issue.id==issueid)).scalar_one_or_none()
    if not issue:
        flash('No such issue')
        return redirect(url_for('admin_file.show_admin_home'))
    journal = issue.volume.journal
    if not check_journal_access(journal):
        flash('You do not have access to journal {}.'.format(journal.name))
        return redirect(url_for('home_bp.home'))
    papers = db.session.execute(select(PaperStatus).where(PaperStatus.issue_id == issue.id).order_by(PaperStatus.paperno)).scalars().all()
    finished_papers = [p for p in papers if p.status == PaperStatusEnum.COPY_EDIT_ACCEPT]
    unassigned_sql = select(PaperStatus).where(PaperStatus.issue_id == None)
    unassigned_papers = db.session.execute(unassigned_sql).scalars().all()
    bumpform = ChangeIssueForm(nexturl=request.path)
    includeform = ChangeIssueForm(issueid=issueid,nexturl=request.path)
    papernoform = ChangePaperNumberForm(issueid=issueid)
    deletepaperform = DeletePaperForm(issueid=issueid)
    data = {'title': 'Status of Volume {}, Issue {}'.format(issue.volume.name, issue.name),
            'issue': issue,
            'volume': issue.volume,
            'finished_papers': len(finished_papers),
            'unassigned_papers': unassigned_papers,
            'journal': issue.volume.journal,
            'bumpform': bumpform,
            'papernoform': papernoform,
            'includeform': includeform,
            'deletepaperform': deletepaperform,
            'papers': papers}
    hotcrp_papers = _get_hotcrp_papers(issue)
    if 'error' in hotcrp_papers:
        if hotcrp_papers['error']:
            flash(hotcrp_papers['error'])
    else:
        if hotcrp_papers['issue'] != str(issue.name):
            flash('Mismatch in hotcrp key: {}/{}'.format(hotcrp_papers['issue'],
                                                         issue.name))
        elif hotcrp_papers['volume'] != str(issue.volume.name):
            flash('Mismatch in volume hotcrp_key: {}/{}'.format(hotcrp_papers['volume'],
                                                                issue.volume.name))
        else:
            # go through the hotcrp papers and remove any that already have a PaperStatus in papers.
            paperids = set()
            for p in papers:
                paperids.add(p.paperid)
            for p in unassigned_papers:
                paperids.add(p.paperid)
            accepted = hotcrp_papers.get('acceptedPapers')
            for p in accepted[:]: # loop over a copy of accepted
                if p['paperId'] in paperids:
                    accepted.remove(p)
            data['hotcrp'] = hotcrp_papers
    formdata = [{'paperid': p.paperid} for p in finished_papers]
    if len(finished_papers) == len(papers) and len(papers) > 0 and not issue.exported:
        data['form'] = PublishIssueForm(issueid=issue.id)
    return render_template('admin/view_issue.html', **data)

@admin_bp.route('/admin/final_review/<paperid>', methods=['GET'])
@auth_required()
def final_review(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        flash(msg)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    candidate_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.CANDIDATE.value)
    final_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.FINAL.value)
    diffs = {}
    candidate_tex_files = list(candidate_path.glob('output/**/*.tex'))
    candidate_tex_files.extend(list(candidate_path.glob('output/**/*.sty')))
    # Due to a bug in htmldiff, we omit bibtex files.
    # candidate_tex_files.extend(list(candidate_path.glob('output/**/*.bib')))
    candidate_output = candidate_path / Path('output')
    candidate_file_map = {str(path.relative_to(candidate_output)): path for path in candidate_tex_files}
    final_tex_files = list(final_path.glob('output/**/*.tex'))
    final_tex_files.extend(list(final_path.glob('output/**/*.sty')))
    # Due to a bug in htmldiff, we omit bibtex files.
    #   final_tex_files.extend(list(final_path.glob('output/**/*.bib')))
    final_output = final_path / Path('output')
    final_file_map = {str(path.relative_to(final_output)): path for path in final_tex_files}
    for filename, file in candidate_file_map.items():
        final_file = final_file_map.get(filename)
        if final_file:
            candidate_lines = file.read_text(encoding='UTF-8', errors='replace').splitlines()
            final_lines = final_file.read_text(encoding='UTF-8', errors='replace').splitlines()
            if candidate_lines != final_lines:
                htmldiff = HtmlDiff(tabsize=2)
                diffs[filename] = htmldiff.make_table(candidate_lines, final_lines, fromdesc='Original', todesc='Final version', context=True, numlines=5).replace('&nbsp;', ' ')
            del final_file_map[filename]
        else:
            diffs[filename] = 'File was removed'
    for filename, file in final_file_map.items():
        diffs[filename] = 'File is new'
    comp_path = final_path / Path('compilation.json')
    if not comp_path.is_file():
        logging.critical('{} does not exist'.format(str(comp_path)))
        return admin_message('Paper has not been finalized: {}'.format(paperid))
    compilation = Compilation.model_validate_json(comp_path.read_text(encoding='UTF-8'))
    sql = select(Discussion).filter_by(paperid=paperid).order_by(Discussion.created.desc())
    items = db.session.execute(sql).scalars().all()
    morechangesform = MoreChangesForm(paperid=paperid)
    data = {'title': 'Final review on paper # {}'.format(paperid),
            'comp': compilation,
            'morechangesform': morechangesform,
            'discussion': items,
            'version': Version.FINAL.value,
            'source_auth': create_hmac([paperid, Version.FINAL.value]),
            'pdf_copyedit_auth': create_hmac([paperid, 'copyedit']),
            'pdf_final_auth': create_hmac([paperid, 'final']),
            'diffs': diffs,
            'paper': paper_status}
    log_file = final_path / Path('output') / Path('main.log')
    latexlog = log_file.read_text(encoding='UTF-8', errors='replace')
    data['loglines'] = latexlog.splitlines()
    bibtex_log = final_path / Path('output') / Path('main.blg')
    if bibtex_log.is_file():
        data['bibtex_log'] = bibtex_log.read_text(encoding='UTF-8', errors='replace').splitlines()
    else:
        data['bibtex_log'] = ['No bibtex log']
    if compilation.bibtex:
        data['marked_bibtex'] = mark_bibtex(compilation.bibtex)
    return render_template('admin/final_review.html', **data)

@admin_bp.route('/admin/finish_copyedit', methods=['POST'])
@auth_required()
def finish_copyedit():
    args = request.form.to_dict()
    paperid = args.get('paperid')
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        flash(msg)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    numitems = db.session.query(Discussion).filter_by(paperid=paperid,status=DiscussionStatus.PENDING).count()
    if not numitems:
        # in this case, the paper has no issues for the author to
        # respond to, so we copy the candidate over to the final
        # version and tell the author that they are finished.
        # We also create a CompileRecord for the final version.
        candidate_sql = select(CompileRecord).where(and_(CompileRecord.paperid == paperid,
                                                         CompileRecord.version == Version.CANDIDATE))
        candidate_comprec = db.session.execute(candidate_sql).scalar_one_or_none()
        final_comprec = CompileRecord(paperid=paperid,
                                      version=Version.FINAL,
                                      result=candidate_comprec.result,
                                      task_status=TaskStatus.FINISHED,
                                      started=datetime.now())
        db.session.add(final_comprec)
        paper_status.status = PaperStatusEnum.COPY_EDIT_ACCEPT.value
        paper_status.lastmodified = datetime.now()
        if paper_status.issue_id:
            issue = paper_status.issue
            if issue and issue.exported:
                # In this case the issue for the paper was already exported, so we unassign the paper.
                paper_status.issue_id = None
                paper_status.paperno = None
        db.session.add(paper_status)
        db.session.commit()
        paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
        candidate_dir = paper_dir / Path(Version.CANDIDATE.value)
        final_dir = paper_dir / Path(Version.FINAL.value)
        shutil.copytree(candidate_dir,
                        final_dir)
        maildata = {'paperid': paperid,
                    'paper_title': paper_status.title}
        author_msg = Message('Copy edit changes approved for {}'.format(paperid),
                             sender=app.config['MAIL_DEFAULT_SENDER'],
                             recipients=[paper_status.email])
        author_msg.body = app.jinja_env.get_template('admin/author_finished.txt').render(maildata)
        if app.config['DEBUG']:
            print(author_msg.body)
        mail.send(author_msg)
        log_event(db, paperid, 'Copy edit was finished and author notified')
        flash('Author of {} was notified of acceptance'.format(paperid));
        return redirect(url_for('admin_file.copyedit_home'), code=302)
    paper_status.status = PaperStatusEnum.EDIT_FINISHED.value
    paper_status.lastmodified = datetime.now()
    if paper_status.issue_id:
        issue = paper_status.issue
        if issue and issue.exported:
            # In this case the issue for the paper was already exported, so we unassign the paper.
            paper_status.issue_id = None
            paper_status.paperno = None
    db.session.add(paper_status)
    db.session.commit()
    msg = Message('Copy editing was finished on your paper',
                  sender=app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[paper_status.email])
    maildata = {'journal_name': paper_status.journal_key,
                'paperid': paperid,
                'numitems': numitems,
                'pdf_auth': create_hmac([paperid, 'copyedit']),
                'final_url': url_for('home_bp.view_copyedit', paperid=paperid,auth=create_hmac([paperid, Version.COPYEDIT.value]),
                                     _external=True)}
    msg.body = app.jinja_env.get_template('admin/copyedit_finished.txt').render(maildata)
    if app.config['DEBUG']:
        print(msg.body)
    mail.send(msg)
    log_event(db, paperid, 'Copy edit was finished and author notified')
    flash('Author of {} was notified to review the copy editor suggestions'.format(paperid));
    return redirect(url_for('admin_file.copyedit_home'), code=302)

## This method is used if a paper is being sent back to the author for
## further changes after their first round of responses. In this case
## 1. The candidate version is replaced by the final version and the
##    final version is removed
## 2. The copyedit version is generated from the new candidate version.
## 3. All Discussion items are "archived" to indicate that the data in them
##    is not trustworthy because it depends on a previous compilation.
@admin_bp.route('/admin/request_more_changes', methods=['POST'])
@auth_required()
def request_more_changes():
    form = MoreChangesForm()
    if not form.validate_on_submit():
        return admin_message('Invalid form submission. This is a bug.')
    paperid = form.paperid.data
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        flash(msg)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
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
                                 'revised': last_compilation.revised,
                                 'pubtype': last_compilation.pubtype,
                                 'errata_doi': last_compilation.errata_doi,
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
                                           app.root_path,
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
@auth_required()
def copyedit_home():
    """Show the list of papers with pending copy edit actions."""
    sql = select(PaperStatus).where(
        or_(PaperStatus.status == PaperStatusEnum.EDIT_PENDING,
            PaperStatus.status == PaperStatusEnum.EDIT_REVISED,
            PaperStatus.status == PaperStatusEnum.EDIT_FINISHED,
            PaperStatus.status == PaperStatusEnum.FINAL_SUBMITTED)).order_by(desc(PaperStatus.lastmodified))
    statuses = db.session.execute(sql).scalars().all()
    journal_keys = Role.user_journal_keys(current_user)
    papers = []
    for p in statuses:
        if p.journal_key in journal_keys:
            papers.append(p.as_dict())
    rows = db.session.execute(select(Discussion.paperid, func.count(Discussion.id).label('issues')).group_by(Discussion.paperid)).all()
    counts = {row.paperid: row.issues for row in rows}
    for paper in papers:
        paper['url'] = _copyedit_url(paper['paperid'], paper['status']['name'])
        paper['issues'] = counts.get(paper['paperid'], 0)
    data = {'title': 'Papers for copy editing',
            'claimform': CopyeditClaimForm(copyeditor=current_user.email),
            'papers': papers}
    return render_template('admin/copyedit_home.html', **data)

@admin_bp.route('/admin/comments/<paperid>', methods=['GET'])
@auth_required()
def comments(paperid):
    if not validate_paperid(paperid):
        return jsonify([])
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        logging.warning(msg)
        return jsonify({'error': msg})
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        logging.critical(msg)
        return jsonify([])
    sql = select(Discussion).where(Discussion.paperid == paperid).order_by(Discussion.created)
    notes = db.session.execute(sql).scalars().all()
    return jsonify([n.as_dict() for n in notes])

@admin_bp.route('/admin/comment', methods=['POST'])
@auth_required()
def comment():
    """This is for ajax to handle copy editing comments."""
    data = request.json
    # access control is tricky because we have to recover the relevant journal first. The
    # payload either contains the id of the comment or the paperid.
    if 'id' in data:
        # check if we can delete that one.
        paperid = db.session.execute(select(Discussion.paperid).where(Discussion.id==data['id'])).scalar_one_or_none()
    else:
        paperid = data['paperid']
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        logging.warning(msg)
        return jsonify({'error': msg})
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        logging.critical(msg)
        return jsonify({'error': msg})
    try:
        action = data['action']
        if action == 'delete':
            db.session.query(Discussion).filter(Discussion.id==data['id']).delete()
            db.session.commit()
            return jsonify({'id': data['id']})
        elif action == 'add':
            d = Discussion(paperid=data['paperid'],
                           creator=data['creator_email'],
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
@auth_required()
def publish_issue():
    form = PublishIssueForm()
    if not form.validate_on_submit():
        for key, value in form.errors.items():
            logging.warning('PublishIssueForm: {}:{}:{} is invalid'.format(form.issueid.datapaperid.data,
                                                                           key,
                                                                           str(value)))
        return admin_message('Invalid form submission. This is a bug.')
    issueid = form.issueid.data
    issue = db.session.execute(select(Issue).where(Issue.id==issueid)).scalar_one_or_none()
    if not issue:
        return admin_message('Nonexistent issue')
    journal = issue.volume.journal
    if not check_journal_access(journal):
        msg = 'User {} does not have access to journal {}'.format(current_user.email,
                                                                  journal.name)
        logging.critical(msg)
        return admin_message(msg)
    try:
        now = export_issue(app.config['DATA_DIR'], app.config['EXPORT_PATH'], issue)
        issue.exported = now
        db.session.add(issue)
        db.session.commit()
    except Exception as e:
        msg = 'Failure to export issue {}: {}'.format(issue.name, str(e))
        logging.critical(msg)
        return admin_message(msg)
    logging.info('Issue was exported {} to {}'.format(issue.name,
                                                      str(app.config['EXPORT_PATH'])))
    flash('Issue was exported to {}'.format(str(app.config['EXPORT_PATH'])))
    return redirect(url_for('admin_file.view_issue', issueid=issue.id))

@admin_bp.route('/admin/change_issue', methods=['POST'])
@auth_required()
def change_issue():
    form = ChangeIssueForm()
    if not form.validate_on_submit():
        for key, value in form.errors:
            log_event(db, form.paperid.data, 'Submission error: {}:{}'.format(key, value))
        return admin_message('Invalid form submission. This is a bug.')
    paper_status, msg = check_paper_access(form.paperid.data)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return admin_message('Unknown paper {}'.format(form.paperid.data))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(form.paperid.data,
                                                   paper_status.journal_key)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
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
    task_key = paper_key(paperid, Version.FINAL.value)
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
    doi = compilation.meta.DOI
    metadata = '\\def\\IACR@DOI{' + doi + '}\n'
    if journal.EISSN:
        metadata += '\\def\\IACR@EISSN{' + journal.EISSN + '}\n'
    metadata += '\\def\\IACR@Received{' + compilation.submitted[:10] + '}\n'
    metadata += '\\def\\IACR@Accepted{' + compilation.accepted[:10] + '}\n'
    metadata += '\\def\\IACR@Published{' + publishedDate + '}\n'
    metadata += '\\def\\IACR@vol{' + str(volume.name) + '}\n'
    metadata += '\\def\\IACR@no{' + str(issue.name) + '}\n'
    if compilation.revised:
        metadata += '\\def\\IACR@Revised{' + compilation.revised[:10] + '}\n'
    metadata += '\\def\\IACR@CROSSMARKURL{https://crossmark.crossref.org/dialog/?doi=' + doi + '\\&domain=pdf\\&date\\_stamp=' + publishedDate + '}\n'
    metadata_file = input_dir / Path('main.iacrmetadata')
    metadata_file.write_text(metadata)
    # Remove output from any previous run.
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    # fire off a separate task to compile. We wrap run_latex_task so it
    # can have the flask context to use sqlalchemy on the database.
    log_event(db, paperid, 'Recompiled for volume {} issue {}'.format(volume.name, issue.name))
    task_queue[task_key] = executor.submit(context_wrap(run_latex_task),
                                           app.root_path,
                                           compilation.command,
                                           str(final_dir.absolute()),
                                           paperid,
                                           compilation.meta.DOI,
                                           Version.FINAL.value,
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
@auth_required()
def change_paperno():
    """This is for increasing or decreasing the paperno on an individual paper. Only ADMIN and
    journal editors may do this."""
    form = ChangePaperNumberForm()
    if not form.validate_on_submit():
        for key, value in form.errors.items():
            log_event(db, form.paperid.data, 'paperno error: {}:{}'.format(key, str(value)))
        flash('Invalid values')
        return admin_message('Invalid form submission. This is a bug.')
    paperid = form.paperid.data
    issueid = form.issueid.data
    paper_status, msg = check_paper_access(paperid)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.view_issue', issueid=form.issueid.data), code=302)
    journal = paper_status.journal(db)
    if not (Role.ADMIN in current_user.roles or
            Role.editor_role(paper_status.journal_key) in current_user.roles):
        flash('You are not allowed to perform that action')
        return redirect(url_for('admin_file.show_admin_home'))
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

@admin_bp.route('/admin/claimcopyedit', methods=['POST'])
@auth_required()
def claimcopyedit():
    form = CopyeditClaimForm()
    if not form.validate_on_submit():
        for key, value in form.errors.items():
            flash('Invalid form: {}:{}'.format(key, value))
        return admin_message('Invalid form submission. This is a bug.')
    paper_status, msg = check_paper_access(form.paperid.data)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    journal = paper_status.journal(db)
    if not journal:
        msg = 'Paper {}:{} has no journal!'.format(paperid, paper_status.journal_key)
        flash(msg)
        logging.critical(msg)
        return redirect(url_for('admin_file.show_admin_home'))
    paper_status.copyeditor = form.copyeditor.data
    db.session.commit()
    if form.view.data:
        return redirect(url_for('admin_file.copyedit',
                                paperid=form.paperid.data))
    flash('Changed copy editor on {} to {}'.format(form.paperid.data,
                                                   form.copyeditor.data))
    return redirect(url_for('admin_file.copyedit_home'))

@admin_bp.route('/admin/deletepaper', methods=['POST'])
@auth_required()
def deletePaper():
    form = DeletePaperForm()
    if not form.validate_on_submit():
        for key, value in form.errors.items():
            flash('Invalid form: {}:{}'.format(key, value))
        return admin_message('Invalid form submission. This is a bug.')
    paper_status, msg = check_paper_access(form.paperid.data)
    if not paper_status:
        flash(msg)
        logging.warning(msg)
        return redirect(url_for('admin_file.view_issue',
                                issueid=form.issueid.data))
    if not (Role.ADMIN in current_user.roles or
            Role.editor_role(paper_status.journal_key) in current_user.roles):
        flash('You are not allowed to perform that action')
        return redirect(url_for('admin_file.view_issue',
                                issueid=form.issueid.data))
    paper_dir = app.config['DATA_DIR'] / Path(form.paperid.data)
    try:
        shutil.rmtree(paper_dir)
    except Exception as e:
        flash('Unable to delete the directory for the paper {}. Perhaps it was already deleted?'.format(form.paperid.data))
    db.session.delete(paper_status)
    db.session.commit()
    return redirect(url_for('admin_file.view_issue',
                            issueid=form.issueid.data))

