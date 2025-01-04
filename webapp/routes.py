import datetime
import time
from io import BytesIO
from flask import json, Blueprint, render_template, request, jsonify, send_file, redirect, url_for
from flask import current_app as app
from flask_mail import Message
import hmac
import markdown
import os
import re
from pathlib import Path
import random
import requests
import shutil
from sqlalchemy import select, and_
from sqlalchemy.sql import func
import string
from . import executor, mail, task_queue, get_json_path, get_pdf_url, validate_hmac, create_hmac, paper_key, db, admin
from .metadata.db_models import CompileRecord, validate_version, TaskStatus, PaperStatus, PaperStatusEnum, Version, log_event, Discussion, DiscussionStatus, Journal, Volume, Issue, NO_HOTCRP
import zipfile
from .metadata.compilation import Compilation, CompileStatus, CompileError, ErrorType, PubType
from .metadata import validate_paperid, get_doi
from .tasks import run_latex_task
from .forms import SubmitForm, CompileForCopyEditForm, NotifyFinalForm
from .bibmarkup import mark_bibtex
from werkzeug.datastructures import MultiDict
import hashlib
import logging
from .country_list import countries

ENGINES = {'lualatex': 'latexmk -g -recorder -pdflua -lualatex="lualatex --disable-write18 --nosocket --no-shell-escape" main',
           'pdflatex': 'latexmk -g -recorder -pdf -pdflatex="pdflatex -interaction=nonstopmode -disable-write18 -no-shell-escape" main',
           'xelatex': 'latexmk -g -recorder -pdfxe -xelatex="xelatex -interaction=nonstopmode -file-line-error -no-shell-escape" main'}

home_bp = Blueprint('home_bp',
                    __name__,
                    template_folder='templates',
                    static_folder='static')

@app.context_processor
def inject_variables():
    return {'site_name': app.config['SITE_NAME'],
            'site_shortname': app.config['SITE_SHORTNAME']}

@home_bp.route('/', methods=['GET'])
def home():
    return render_template('index.html',
                           title=app.config['SITE_NAME'])

@home_bp.route('/submit', methods=['GET'])
def show_submit_version():
    form = SubmitForm(request.args)
    if not form.paperid.data:
        bypass = request.args.get('bypass', None)
        if bypass != app.config['SUBMIT_BYPASS']: # just for testing.
            return redirect(url_for('home_bp.home'))
        #TODO: remove this if. It's only for testing to supply a paperid when it doesn't come from internal.
        # In this case the submission doesn't come from hotcrp, so we make up some fields.
        random.seed()
        form.paperid.data = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        form.hotcrp.data = NO_HOTCRP
        form.hotcrp_id.data = NO_HOTCRP
        form.version.data = 'candidate'
        form.accepted.data = '2022-09-30 17:49:20'
        form.submitted.data = '2022-08-03 06:44:30'
        form.journal.data = 'cic'
        form.volume.data = '1'
        form.issue.data = '1'
        form.generate_auth()
    else:
        # We only perform partial validation on the GET request to make sure that
        # the auth token is valid.
        if not form.check_auth():
            logging.warning('{}:{}:{} form not authenticated'.format(form.paperid.data,
                                                                     form.version.data,
                                                                     form.auth.data))
            for key, value in form.errors.items():
                flash('{}:{}'.format(key,value))
            return render_template('message.html',
                                   title='This submission is not authorized.',
                                   error='The token for this request is invalid')
    paperid = form.paperid.data
    # Submission form is limited to papers that are not in copy editing mode and not already
    # accepted for publication. 
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if paper_status:
        if (paper_status.status == PaperStatusEnum.SUBMITTED.value or
            paper_status.status == PaperStatusEnum.EDIT_PENDING.value):
            return render_template('message.html',
                                   title='Your paper has been sent to the copy editor.',
                                   error='Your paper {} has been sent to the copy editor.'.format(paperid))
        elif ((paper_status.status == PaperStatusEnum.EDIT_FINISHED.value or
               paper_status.status == PaperStatusEnum.EDIT_REVISED) and
              form.version.data != Version.FINAL.value):
            return render_template('message.html',
                                   title='Wrong version',
                                   error='Version should be final. This is a bug')
        elif paper_status.status == PaperStatusEnum.FINAL_SUBMITTED:
            return render_template('message.html',
                                   title='Your paper is pending final review.',
                                   error='Your paper ID {} is pending final review. No more revisions will be accepted.'.format(paperid))
        elif paper_status.status == PaperStatusEnum.COPY_EDIT_ACCEPT:
            return render_template('message.html',
                                   title='Your paper has been accepted by the copy editor.',
                                   error='Your paper is pending for publication. No more revisions will be accepted.')
        elif paper_status.status == PaperStatusEnum.PUBLISHED:
            return render_template('message.html',
                                   title='Your paper has already been published.',
                                   error='Your paper has already been published.')
    return render_template('submit.html', form=form, title='Upload your paper')

def context_wrap(fn):
    """Wrapper to pass context to function in thread."""
    app_context = app.app_context()
    def wrapper(*args, **kwargs):
        with app_context:
            return fn(*args, **kwargs)
    return wrapper

# NOTE: there are constraints on what can be submitted based on
# the current status for the paperid.
@home_bp.route('/submit', methods=['POST'])
def submit_version():
    form = SubmitForm()
    if not form.validate_on_submit():
        logging.critical('{}:{}:{} submission not authenticated'.format(form.paperid.data,
                                                                        form.version.data,
                                                                        form.auth.data))
        return render_template('message.html',
                               title='The form data is invalid.',
                               error='The form data is invalid. This is a bug')
    args = request.form.to_dict()
    paperid = args.get('paperid')
    version = args.get('version', Version.CANDIDATE.value)
    accepted = args.get('accepted', '')
    submitted = args.get('submitted', '')
    hotcrp = args.get('hotcrp', '')
    hotcrp_id = args.get('hotcrp_id', '')
    task_key = paper_key(paperid, version)
    now = datetime.datetime.now()
    if task_queue.get(task_key):
        log_event(db, paperid, 'Attempt to resubmit while compiling')
        msg = 'Already running {}:{}'.format(form.paperid.data,
                                             form.version.data)
        logging.warning(msg)
        return render_template('message.html',
                               title='Another one is running',
                               error='At most one compilation may be queued on each paper.')
    # Ensure that the journal, volume, and issue exist.
    journal_id = args.get('journal')
    journal = db.session.execute(select(Journal).filter_by(hotcrp_key=journal_id)).scalar_one_or_none()
    if not journal:
        return render_template('message.html',
                               title='Unknown journal {}'.format(journal_id),
                               error='Unknown journal {}'.format(journal_id))
    volume = db.session.execute(select(Volume).filter_by(name=args.get('volume'),
                                                         journal_id=journal.id)).scalar_one_or_none()
    if not volume:
        # First time we see the volume, so create it.
        volume = Volume(name=args.get('volume'),
                        journal_id=journal.id)
        db.session.add(volume)
        db.session.commit()
    issue = db.session.execute(select(Issue).filter_by(name=args.get('issue'),
                                                       volume_id=volume.id)).scalar_one_or_none()
    if not issue:
        issue = Issue(name=args.get('issue'),
                      hotcrp=args.get('hotcrp'),
                      volume_id=volume.id)
        db.session.add(issue)
        db.session.commit()
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    paper_dir.mkdir(parents=True, exist_ok=True)
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    # send_mail keeps track of whether we should send an email to the author. This only
    # happens on the first upload of each version.
    send_mail = False
    pubtype = PubType.from_str(form.pubtype.data)
    if not paper_status:
        papernum = db.session.execute(select(func.max(PaperStatus.paperno)).where(PaperStatus.issue_id==issue.id)).scalar_one_or_none()
        if papernum is None:
            papernum = 1
        else:
            papernum += 1
        paper_status = PaperStatus(paperid=paperid,
                                   hotcrp=hotcrp,
                                   hotcrp_id=hotcrp_id,
                                   email=args.get('email'),
                                   submitted=submitted,
                                   accepted=accepted,
                                   pubtype=pubtype,
                                   journal_key=args.get('journal'),
                                   volume_key=args.get('volume'),
                                   issue_key=args.get('issue'),
                                   issue_id=issue.id,
                                   paperno=papernum,
                                   status=PaperStatusEnum.PENDING.value)
        db.session.add(paper_status)
        db.session.commit()
        send_mail = True
    # check that submission is allowed.
    if paper_status.status == PaperStatusEnum.EDIT_PENDING:
        return render_template('message.html',
                               title='Paper was sent to copy editor',
                               error='Paper may not be updated while it is in the hands of the copy editor')
    if paper_status.status == PaperStatusEnum.COPY_EDIT_ACCEPT:
        return render_template('message.html',
                               title='Paper is in final production steps',
                               error='Paper may not be updated after copy edit acceptance')
    if paper_status.status == PaperStatusEnum.PUBLISHED:
        return render_template('message.html',
                               title='Paper is already published',
                               error='Paper may not be updated after it is published')
    if paper_status.status == PaperStatusEnum.SUBMITTED:
        paper_status.status = PaperStatusEnum.PENDING
        paper_status.lastmodified = datetime.datetime.now()
        db.session.add(paper_status)
        db.session.commit()
    if (paper_status.status == PaperStatusEnum.EDIT_FINISHED or
        paper_status.status == PaperStatusEnum.FINAL_SUBMITTED):
        # TODO: check that discussion items are finished
        send_mail = True
        version = Version.FINAL.value
    log_event(db, paperid, 'Upload of zip file for {}'.format(version))
    version_dir = paper_dir / Path(version)
    # This blows everything away for the version.
    if version_dir.is_dir():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True)
    # Unzip the zip file into submitted_dir
    zip_path = version_dir / Path('all.zip')
    tmpzip_path = version_dir / Path('tmp.zip')
    try:
        request.files['zipfile'].save(tmpzip_path)
    except Exception as e:
        logging.error('Unable to save zip file: {}'.format(str(e)))
        form.zipfile.errors.append('unable to save zip file')
        return render_template('submit.html', form=form)
    try:
        allzip= zipfile.ZipFile(zip_path, 'w')
        with zipfile.ZipFile(tmpzip_path, 'r') as tmpzip:
            for item in tmpzip.infolist():
                buffer = tmpzip.read(item.filename)
                filename = str(item.filename)
                # remove __MACOSX and .DS_Store detritus created from an apple filesystem.
                if not (filename.startswith('__MACOSX') or filename.startswith('.DS_Store')):
                    allzip.writestr(item, buffer)
        allzip.close()
        tmpzip_path.unlink()
    except Exception as e:
        logging.error('Unable to remove __MACOSX from zip file')
        form.zipfile.errors.append('Unable to remove __MACOSX from zip file. Please rezip without this')
        return render_template('submit.html', form=form)
    input_dir = version_dir / Path('input')
    try:
        zip_file = zipfile.ZipFile(zip_path)
        zip_file.extractall(input_dir)
    except Exception as e:
        logging.error('Unable to extract from zip file: {}'.format(str(e)))
        log_event(db, paperid, 'Zip file could not be unzipped')
        form.zipfile.errors.append('Unable to extract from zip file: {}'.format(str(e)))
        return render_template('submit.html', form=form)
    tex_file = input_dir / Path('main.tex')
    if not tex_file.is_file():
        log_event(db, paperid, 'Zip file did not have main.tex at top level')
        form.zipfile.errors.append('Your zip file should contain main.tex at the top level')
        # then no sense trying to compile
        return render_template('submit.html', form=form)
    # Check that none of the latex files use \begin{thebibliography}, because that would
    # bypass our bibliography style. The LaTeX runner will automatically remove main.bbl
    # later on.
    for f in input_dir.rglob('*'):
        if f.is_file() and f.name.endswith('.tex'):
            txt = f.read_text(encoding='utf-8', errors='replace')
            if '\\begin{thebibliography}' in txt:
                log_event(db, paperid, 'LaTeX file with thebibligraphy in it')
                form.zipfile.errors.append('Your Latex files may not contain \\begin{thebibliography} in them. Please use bibtex or biblatex and upload your bibtex files.')
                return render_template('submit.html', form=form)
    command = ENGINES.get(args.get('engine'))
    compilation_data = {'paperid': paperid,
                        'status': CompileStatus.COMPILING,
                        'email': args.get('email'),
                        'venue': args.get('journal'),
                        'submitted': submitted,
                        'accepted': accepted,
                        'pubtype': pubtype.name,
                        'errata_doi': form.errata_doi.data,
                        'compiled': now,
                        'engine': args.get('engine'),
                        'command': command,
                        'error_log': [],
                        'warning_log': [],
                        'zipfilename': request.files['zipfile'].filename}
    compilation = Compilation(**compilation_data)
    sql = select(CompileRecord).filter_by(paperid=paperid).filter_by(version=version)
    comprec = db.session.execute(sql).scalar_one_or_none()
    if not comprec:
        comprec = CompileRecord(paperid=paperid,version=version)
    comprec.task_status = TaskStatus.PENDING
    comprec.started = now
    compstr = compilation.model_dump_json(indent=2, exclude_none=True)
    comprec.result = compstr
    db.session.add(comprec)
    db.session.commit()
    compilation_file = version_dir / Path('compilation.json')
    compilation_file.write_text(compstr, encoding='UTF-8')
    receivedDate = datetime.datetime.strptime(submitted[:10],'%Y-%m-%d')
    acceptedDate = datetime.datetime.strptime(accepted[:10],'%Y-%m-%d')
    publishedDate = datetime.date.today().strftime('%Y-%m-%d')
    doi = get_doi(journal.DOI_PREFIX, paperid)
    metadata = '\\def\\IACR@DOI{' + doi + '}\n'
    if journal.EISSN:
        metadata += '\\def\\IACR@EISSN{' + journal.EISSN + '}\n'
    metadata += '\\def\\IACR@Received{' + receivedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Accepted{' + acceptedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Published{' + publishedDate + '}\n'
    if paper_status.issue:
        metadata += '\\def\\IACR@vol{' + str(paper_status.issue.volume.name) + '}\n'
        metadata += '\\def\\IACR@no{' + str(paper_status.issue.name) + '}\n'
    metadata += '\\def\\IACR@CROSSMARKURL{https://crossmark.crossref.org/dialog/?doi=' + doi + r'\&domain=pdf\&date\_stamp=' + publishedDate + '}\n'
    metadata_file = input_dir / Path('main.iacrmetadata')
    metadata_file.write_text(metadata)
    output_dir = version_dir / Path('output')
    # Remove output from any previous run.
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    # fire off a separate task to compile. We wrap run_latex_task so it
    # can have the flask context to use sqlalchemy on the database.
    task_queue[task_key] = executor.submit(context_wrap(run_latex_task),
                                           app.root_path,
                                           command,
                                           str(version_dir.absolute()),
                                           paperid,
                                           doi,
                                           version,
                                           task_key)
    paper_url = url_for('home_bp.view_results',
                        paperid=paperid,
                        version=version,
                        auth=create_hmac([paperid, version]),
                        _external=True)
    if send_mail:
        msg = Message('Paper {} was submitted'.format(paperid),
                      sender=app.config['EDITOR_EMAILS'],
                      recipients=['iacrcc@digicrime.com']) # for testing
        msg.body = 'This is just a test message for now.\n\nYour paper will be viewable at {}'.format(paper_url)
        mail.send(msg)
    status_url = paper_url.replace('/view/', '/tasks/')
    data = {'title': 'Compiling your LaTeX',
            'status_url': status_url,
            'headline': 'Compiling your paper'}
    return render_template('running.html', **data)

def _register_hotcrp_upload(paperid: str):
    """We make a post to submit.iacr.org, and validate the paperid, hotcrp version."""
    status = db.session.execute(select(PaperStatus).where(PaperStatus.paperid==paperid)).scalar_one_or_none()
    if not status:
        logging.critical('Unable to report upload to hotcrp: {}'.format(paperid))
        return
    if status.hotcrp == NO_HOTCRP:
        return
    args = [status.hotcrp, status.hotcrp_id, status.email]
    auth = hmac.new(app.config['HOTCRP_API_KEY'].encode('utf-8'),
                    (''.join(args)).encode('utf-8'), hashlib.sha256).hexdigest()
    payload = {'auth': auth,
               'action': 'finalPaper',
               'paperId': status.hotcrp_id,
               'email': status.email}
    url = 'https://submit.iacr.org/{}/iacr/api/updatePaper.php'.format(status.hotcrp)
    r = requests.post(url, data=payload)
    if r.status_code != 200:
        logging.critical('Unable to update hotcrp with final paper status {}:{}'.format(status.hotcrp,
                                                                                        status.hotcrp_id))

# When an author sends for copy editing, we set the status to SUBMITTED and
# compile it with line numbers to produce the COPYEDIT version. After
# the compilation finishes, set the status to EDIT_PENDING and an email is
# sent to the copy editor(s) to notify them that a paper is ready for copy editing.
# TODO: This is a simplified version of the flow described in the README.md,
# where the editor would assign a copy editor from a list. We might also allow
# papers in the FINAL_SUBMITTED status to be sent again for copy editing if
# the copy editor finds more things to complain about.
@home_bp.route('/compile_for_copyedit', methods=['POST'])
def compile_for_copyedit():
    form = CompileForCopyEditForm()
    if not form.validate_on_submit():
        logging.error('copyedit Validation failed {}:{}:{}'.format(form.paperid.data,
                                                                   form.version.data,
                                                                   form.auth.data))
        form.auth.errors.append('Validation failed')
        return render_template('message.html',
                               title='Please go back and try again',
                               error='Validation failed. This is a bug')
    paperid = form.paperid.data
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    if not paper_dir.is_dir():
        return render_template('message.html',
                               title='Paper does not exist',
                               error='Paper directory does not exist. This is a bug')
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if not paper_status:
        return render_template('message.html',
                               title='Missing status',
                               error='Paper status does not exist. This is a bug')
    if (paper_status.status != PaperStatusEnum.PENDING and
        paper_status.status != PaperStatusEnum.EDIT_REVISED):
        return render_template('message.html',
                               title='Paper was already sent to copy editor',
                               error = 'Paper was already sent for copy editing.')
    task_key = paper_key(paperid, Version.COPYEDIT.value)
    if task_queue.get(task_key):
        log_event(db, paperid, 'Attempt to resubmit while compiling')
        msg = 'Already running {}:{}'.format(form.paperid.data,
                                             Version.COPYEDIT.value)
        logging.warning(msg)
        return render_template('message.html',
                               title='Another one is running',
                               error='At most one compilation may be queued on each paper.')
    sql = select(CompileRecord).filter_by(paperid=paperid, version=form.version.data)
    version_comprec = db.session.execute(sql).scalar_one_or_none()
    if not version_comprec:
        return render_template('message.html',
                               title='Compilation not found',
                               error='Compilation record was not found. This is a bug')
    # Change the status to submitted, so that it cannot be updated by the author.
    version_compilation = version_comprec.result
    if not version_compilation:
        return render_template('message.html',
                               title='version_compilation not found',
                               error='version_compilation was not found. This is a bug')
    version_compilation = Compilation.model_validate_json(version_compilation)
    # TODO: if we switch to having the editor assign a copy editor, then
    # the status will be set to PaperStatusEnum.SUBMITTED. For now we set it
    # to EDIT_PENDING, assuming that the assignment of copy editor is automatic.
    paper_status.status = PaperStatusEnum.EDIT_PENDING
    paper_status.lastmodified = datetime.datetime.now()
    db.session.add(paper_status)
    db.session.commit()
    log_event(db, paperid, 'Submitted for copy edit'.format(paperid))
    copyedit_dir = paper_dir / Path(Version.COPYEDIT.value)
    if copyedit_dir.is_dir():
        shutil.rmtree(copyedit_dir)
    copyedit_dir.mkdir(parents=True)
    version_dir = paper_dir / Path(form.version.data)
    version_input_dir = version_dir / Path('input')
    copyedit_input_dir = copyedit_dir / Path('input')
    shutil.copytree(version_input_dir,
                    copyedit_input_dir)
    copyedit_file = copyedit_input_dir / Path('main.copyedit')
    copyedit_file.touch() # this iacrcc.cls to add line numbers.
    sql = select(CompileRecord).filter_by(paperid=paperid, version=Version.COPYEDIT.value)
    copyedit_comprec = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: copyedit_comprec = CompileRecord.query.filter_by(paperid=paperid,version=Version.COPYEDIT.value).first()
    if not copyedit_comprec:
        copyedit_comprec = CompileRecord(paperid=paperid,version=Version.COPYEDIT.value)
    copyedit_comprec.task_status = TaskStatus.PENDING
    now = datetime.datetime.now()
    copyedit_comprec.started = now
    copyedit_comprec.task_status = TaskStatus.PENDING
    compilation = Compilation(**{'paperid': paperid,
                                 'venue': paper_status.journal_key,
                                 'status': CompileStatus.COMPILING,
                                 'version': Version.COPYEDIT.value,
                                 'email': version_compilation.email,
                                 'submitted': version_compilation.submitted,
                                 'accepted': version_compilation.accepted,
                                 'pubtype': version_compilation.pubtype,
                                 'errata_doi': version_compilation.errata_doi,
                                 'compiled': now,
                                 'engine': version_compilation.engine,
                                 'command': version_compilation.command,
                                 'error_log': [],
                                 'warning_log': [],
                                 'zipfilename': version_compilation.zipfilename})
    command = version_compilation.command
    compstr = compilation.model_dump_json(indent=2, exclude_none=True)
    copyedit_comprec.result = compstr
    db.session.add(copyedit_comprec)
    db.session.commit()
    compilation_file = copyedit_dir / Path('compilation.json')
    compilation_file.write_text(compstr, encoding='UTF-8')
    output_dir = copyedit_dir / Path('output')
    # Remove output from any previous run.
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    # fire off a separate task to compile. We wrap run_latex_task so it
    # can have the flask context to use sqlalchemy on the database.
    task_queue[task_key] = executor.submit(context_wrap(run_latex_task),
                                           app.root_path,
                                           command,
                                           str(copyedit_dir.absolute()),
                                           paperid,
                                           version_compilation.meta.DOI,
                                           Version.COPYEDIT.value,
                                           task_key)
    status_url = url_for('home_bp.get_status',
                         paperid=paperid,
                         version=Version.COPYEDIT.value,
                         auth=create_hmac([paperid, Version.COPYEDIT.value]),
                         _external=True)
    _register_hotcrp_upload(paperid)
    # Notify the copy editor.
    msg = Message('Paper {} is ready for copy editing'.format(paperid),
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=[app.config['COPYEDITOR_EMAILS']]) # for testing
    copyedit_url = url_for('admin_file.copyedit', paperid=paperid, _external=True)
    msg.body = 'A paper for CiC is being compiled for copy editing.\n\nYou can view it at {}'.format(copyedit_url)
    mail.send(msg)
    if app.config['TESTING']:
        print(msg.body)
    data = {'title': 'Compiling your LaTeX for copy editor',
            'status_url': status_url,
            'headline': 'Recompiling your paper with line numbers for the copy editor'}
    return render_template('running.html', **data)


@home_bp.route('/final_review', methods=['POST'])
def final_review():
    form = NotifyFinalForm()
    if not form.validate_on_submit():
        logging.error('final review validation failed {}:{}:{}'.format(form.paperid.data,
                                                                       form.version.data,
                                                                       form.auth.data))
        form.auth.errors.append('Validation failed')
        return render_template('message.html',
                               title='Please go back and try again',
                               error='Final review validation failed. This is a bug')
    paperid = form.paperid.data
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if not paper_status:
        return render_template('message.html',
                               title='Missing status',
                               error='Paper status does not exist. This is a bug')
    paper_status.status = PaperStatusEnum.FINAL_SUBMITTED
    paper_status.lastmodified = datetime.datetime.now()
    db.session.add(paper_status)
    db.session.commit()
    # Notify the copy editor.
    msg = Message('Paper {} is ready for final review'.format(paperid),
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=[app.config['COPYEDITOR_EMAILS']]) # for testing
    final_review_url = url_for('admin_file.final_review', paperid=paperid, _external=True)
    msg.body = 'A paper for CiC needs final review.\n\nYou can view it at {}'.format(final_review_url)
    mail.send(msg)
    if app.config['TESTING']:
        print(msg.body)
    return render_template('message.html',
                           title='Your paper will be reviewed',
                           message='You will receive an email when the final review of your paper is completed.')


@home_bp.route('/copyedit/<paperid>/<auth>', methods=['GET'])
def view_copyedit(paperid, auth):
    """View the feedback from the copyeditor."""
    if not validate_hmac([paperid, Version.COPYEDIT.value], auth):
        return render_template('message.html',
                               title='Invalid request',
                               error='Your authentication cannot be verified')
    sql = select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if paper_status:
        if (paper_status.status == PaperStatusEnum.EDIT_PENDING.value or
            paper_status.status == PaperStatusEnum.EDIT_REVISED.value):
            return render_template('message.html',
                                   title='Your copy edit was submitted',
                                   message='You will receive an email when the copy editor finishes with your paper')
        elif paper_status.status == PaperStatusEnum.EDIT_FINISHED.value:
            sql = select(Discussion).where(and_(Discussion.paperid == paperid,
                                                Discussion.archived == None)).order_by(Discussion.created.desc())
            items = [item.as_dict() for item in db.session.execute(sql).scalars().all()]
            responded_count = 0
            for item in items:
                item['token'] = create_hmac([paperid, item['text'], str(item['id'])])
                if item['status']['name'] != DiscussionStatus.PENDING.name:
                    responded_count += 1
            archived_sql = select(Discussion).where(and_(Discussion.paperid == paperid,
                                                         Discussion.archived != None)).order_by(Discussion.created.desc())
            archived_items = db.session.execute(archived_sql).scalars().all()
            data = {'paperid': paperid,
                    'status_values': {s.name: s.value for s in DiscussionStatus},
                    'pdf_auth': create_hmac([paperid, 'copyedit']),
                    'items': items,
                    'archived_items': archived_items,
                    'source_auth': auth,
                    'version': Version.COPYEDIT.value,
                    'upload': ''}
            if responded_count == len(items):
                data['upload'] = url_for('home_bp.submit_version',
                                         paperid=paperid,
                                         version=Version.FINAL.value,
                                         issue=paper_status.issue_key,
                                         hotcrp_id=paper_status.hotcrp_id,
                                         hotcrp=paper_status.hotcrp,
                                         volume=paper_status.volume_key,
                                         submitted=paper_status.submitted,
                                         accepted=paper_status.accepted,
                                         email=paper_status.email,
                                         journal=paper_status.journal_key,
                                         auth=create_hmac([paperid, # TODO: authenticate other fields
                                                           paper_status.hotcrp,
                                                           paper_status.hotcrp_id,
                                                           Version.FINAL.value,
                                                           paper_status.submitted,
                                                           paper_status.accepted,
                                                           paper_status.journal_key,
                                                           paper_status.volume_key,
                                                           paper_status.issue_key,
                                                           paper_status.pubtype.name]))

            paper_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.COPYEDIT.value)
            if not paper_path.is_dir():
                return render_template('message.html',
                                       title='Unknown paper',
                                       error='Unknown paper. Try resubmitting.')
            try:
                json_file = paper_path / Path('compilation.json')
                comp = Compilation.model_validate_json(json_file.read_text(encoding='UTF-8'))
                data['comp'] = comp
                if comp.bibtex:
                    data['marked_bibtex'] = mark_bibtex(comp.bibtex)
                log_file = paper_path / Path('output/main.log')
                data['loglines'] = log_file.read_text(encoding='UTF-8').splitlines()
                bibtex_logfile = paper_path / Path('output/main.blg')
                if bibtex_logfile.is_file():
                    data['bibtex_log'] = bibtex_logfile.read_text(encoding='UTF-8').splitlines()
                else:
                    data['bibtex_log'] = ['No bibtex log']
            except Exception as e:
                logging.error('Unable to parse compilation')
                return render_template('message.html',
                                       title='An error has occurred',
                                       error='An error has occurred reading data. Please contact the admin.')
            return render_template('view_copyedit.html', **data)
        else:
            # TODO: handle the other cases like SUBMITTED or PENDING.
            return render_template('message.html',
                                   title='Error in paper status',
                                   message='Your paper has status {}. This should not happen.'.format(paper_status.status))
    else:
        return render_template('message.html',
                               title='Unknown paper',
                               error='Unknown paper')

@home_bp.route('/respond_to_comment/<paperid>/<itemid>/<auth>', methods=['POST'])
def respond_to_comment(paperid, itemid, auth):
    """Handle an ajax post of a response to a comment."""
    data = request.json
    try:
        sql = select(Discussion).filter_by(id=itemid)
        item = db.session.execute(sql).scalar_one_or_none()
        if not item:
            return jsonify({'error': 'Unknown item'})
        # If the text has changed, it means someone edited it but the author
        # has seen an old version.
        if not validate_hmac([paperid, item.text, str(itemid)], auth):
            return jsonify({'error': 'Text has changed. Please reload'})
        item.reply = data['reply']
        item.status = data['status']
        db.session.add(item)
        db.session.commit()
        response = item.as_dict()
        response['confirm'] = True
        sql = select(func.count()).select_from(Discussion).filter_by(paperid=paperid).filter_by(status=DiscussionStatus.PENDING.name)
        count = db.session.scalar(sql)
        if not count:
            sql = select(PaperStatus).filter_by(paperid=paperid)
            paper_status = db.session.execute(sql).scalar_one_or_none()
            response['upload'] = url_for('home_bp.submit_version',
                                         paperid=paperid,
                                         version=Version.FINAL.value,
                                         issue=paper_status.issue_key,
                                         hotcrp_id=paper_status.hotcrp_id,
                                         hotcrp=paper_status.hotcrp,
                                         volume=paper_status.volume_key,                                         
                                         submitted=paper_status.submitted,
                                         accepted=paper_status.accepted,
                                         email=paper_status.email,
                                         journal=paper_status.journal_key,
                                         auth=create_hmac([paperid, # TODO: authenticate other fields
                                                           paper_status.hotcrp,
                                                           paper_status.hotcrp_id,
                                                           Version.FINAL.value,
                                                           paper_status.submitted,
                                                           paper_status.accepted,
                                                           paper_status.journal_key,
                                                           paper_status.volume_key,
                                                           paper_status.issue_key,
                                                           paper_status.pubtype.name]))
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)})

@home_bp.route('/tasks/<paperid>/<version>/<auth>', methods=['GET'])
def get_status(paperid, version, auth):
    """Check on the current status of a compilation via ajax.
    This returns a json object with 'url', 'status', and 'msg', and the user will
    be redirected to url when the compilation is completed.
    """
    args = request.args.to_dict()
    if not validate_hmac([paperid, version], auth):
        return jsonify({'status': TaskStatus.ERROR,
                        'msg': 'hmac is invalid'})
    if 'request_more' in args: # This means that it's an admin recompile for EDIT_REVISED.
        paper_url = url_for('admin_file.copyedit', paperid=paperid)
    elif version == Version.COPYEDIT.value:
        paper_url = url_for('home_bp.view_copyedit',
                            paperid=paperid,
                            auth=create_hmac([paperid, version]))
    else:
        paper_url = url_for('home_bp.view_results',
                            paperid=paperid,
                            version=version,
                            auth=create_hmac([paperid, version]))
    if not validate_paperid(paperid):
        return jsonify({'url': paper_url,
                        'status': TaskStatus.ERROR,
                        'msg': 'Invalid paperid'})
    if not validate_version(version):
        return jsonify({'url': paper_url,
                        'status': TaskStatus.ERROR,
                        'msg': 'Unknown version'}), 200
    status = TaskStatus.PENDING
    msg = 'Unknown status'
    # is the task in the queue or running?
    task_key = paper_key(paperid, version)
    future = task_queue.get(task_key, None)
    if future:
        if future.cancelled():
            status = TaskStatus.CANCELLED
            msg = 'Compilation was cancelled'
        elif future.running():
            status = TaskStatus.RUNNING
            msg = 'Compilation is running'
        elif future._exception:
            status = TaskStatus.FAILED_EXCEPTION
            msg = 'An exception occurred: {}'.format(str(future._exception))
        elif future.done(): # must have returned a result
            # Tasks that are done should remove themselves from task_queue, so this
            # shouldn't happen
            status = TaskStatus.FINISHED
            if future.result.get('errors'):
                msg = 'Finished with errors'
            else:
                msg = 'Compilation finished running'
        else: # it's enqueued
            status = TaskStatus.COMPILING
            try:
                position = tuple(task_queue.keys()).index(paperid)
                size = len(task_queue)
                msg = 'Pending (position {} out of {})'.format(position, size)
            except Exception:
                msg = 'Unknown position'
    else: # The task would normally remove itself from the task_queue.
        sql = select(CompileRecord).filter_by(paperid=paperid, version=version)
        record = db.session.execute(sql).scalar_one_or_none()
        # Legacy API: record = CompileRecord.query.filter_by(paperid=paperid, version=version).first()
        if not record:
            status = TaskStatus.ERROR
            msg = 'No record of compilation'
        else:
            status = record.task_status
            msg = 'Compilation {}'.format(status.value)
    if (status == TaskStatus.FINISHED or
        status == TaskStatus.CANCELLED or
        status == TaskStatus.FAILED_EXCEPTION):
        task_queue.pop(task_key, None)
    if 'next' in args: # this allows us to override the redirect target.
        paper_url = args.get('next')
    return jsonify({'url': paper_url,
                    'status': status.value,
                    'msg': msg}), 200

@home_bp.route('/view/<paperid>/<version>/<auth>/main.pdf', methods=['GET'])
def show_pdf(paperid,version, auth):
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    if not validate_version(version):
        msg = 'Invalid version {}'.format(version)
        return render_template('message.html',
                               title=msg,
                               error=msg)
    if not validate_hmac([paperid, version], auth):
        return render_template('message.html',
                               title = 'Invalid hmac',
                               error = 'Invalid hmac')
    pdf_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(version) / Path('output/main.pdf')
    if pdf_path.is_file():
        return send_file(str(pdf_path.absolute()), mimetype='application/pdf', max_age=0, etag=str(int(time.time())))
    return render_template('message.html',
                           title='Unable to retrieve file {}'.format(str(pdf_path.absolute())),
                           error='Unknown file. This is a bug')
    
"""
View the results of a compilation. We use a different template for iacrcc.cls,
because this provides better tracking in the log for which file is currently
being processed.
"""
@home_bp.route('/view/<paperid>/<version>/<auth>', methods=['GET'])
def view_results(paperid, version, auth):
    """Note: in this view, auth is computed from paperid, version, '', ''."""
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    if not validate_version(version):
        return render_template('message.html',
                               title='Invalid version',
                               error='Invalid version')
    if not validate_hmac([paperid, version], auth):
        return render_template('message.html',
                               title = 'Invalid hmac',
                               error = 'Invalid hmac')
    paper_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(version)
    if not paper_path.is_dir():
        return render_template('message.html',
                               title='Unknown paper',
                               error='Unknown paper. Try resubmitting.')
    data = {'title': 'Results from compilation',
            'paperid': paperid,
            'version': version,
            'source_auth': auth}
    try:
        json_file = paper_path / Path('compilation.json')
        comp = Compilation.model_validate_json(json_file.read_text(encoding='UTF-8'))
        data['comp'] = comp
        data['auth'] = create_hmac([paperid, version, comp.submitted, comp.accepted])
    except Exception as e:
        return render_template('message.html',
                               title='Unable to parse compilation',
                               error='Unable to parse compilation: {}'.format(str(e)))
    output_path = paper_path / Path('output')
    if not output_path.is_dir():
        # TODO: there is apparently a bug that causes this to happen.
        # See https://github.com/IACR/latex-submit/issues/12
        return render_template('message.html',
                               title='Paper was not compiled',
                               error='Paper was not compiled: no directory {}. This is a bug that should not exist any more.'.format(str(output_path)))
    output_dir = paper_path / Path('output')
    comp.output_files = sorted([str(p.relative_to(str(output_dir))) for p in output_dir.rglob('*') if p.is_file() and p.name != 'main.pdf'])
    pdf_file = output_path / Path('main.pdf')
    log_file = output_path / Path('main.log')
    if pdf_file.is_file():
        data['pdf'] = get_pdf_url(paperid, version)
    else:
        data['pdf'] = ''
    if log_file.is_file():
        try:
            data['latexlog'] = log_file.read_text(encoding='UTF-8', errors='replace')
        except Exception as e:
            logging.error('Unable to read log file as UTF-8: {}'.format(paperid))
            # If pdflatex is used, then it can sometimes create a log file that is not
            # readable as UTF-8 (in spite of the _input_ encoding being set to UTF-8).
            # see https://github.com/IACR/latex-submit/issues/26
            data['latexlog'] = log_file.read_text(encoding='iso-8859-1', errors='replace')
    else:
        data['latexlog'] = ''
    data['loglines'] = data['latexlog'].splitlines()
    bibtex_log = output_path / Path('main.blg')
    if bibtex_log.is_file():
        data['bibtex_log'] = bibtex_log.read_text(encoding='UTF-8', errors='replace').splitlines()
    else:
        data['bibtex_log'] = ['No bibtex log']
    if comp.bibtex:
        data['marked_bibtex'] = mark_bibtex(comp.bibtex)
    pstatus = db.session.execute(select(PaperStatus).where(PaperStatus.paperid==paperid)).scalar_one_or_none()
    data['paper'] = pstatus
    data['submit_url'] = url_for('home_bp.show_submit_version',
                                 paperid=paperid,
                                 version=version,
                                 hotcrp=pstatus.hotcrp,
                                 hotcrp_id=pstatus.hotcrp_id,
                                 journal=pstatus.journal_key,
                                 volume=pstatus.volume_key,
                                 issue=pstatus.issue_key,
                                 submitted=pstatus.submitted,
                                 accepted=pstatus.accepted,
                                 auth=create_hmac([paperid,
                                                   pstatus.hotcrp,
                                                   pstatus.hotcrp_id,
                                                   version,
                                                   comp.submitted,
                                                   comp.accepted,
                                                   pstatus.journal_key,
                                                   pstatus.volume_key,
                                                   pstatus.issue_key,
                                                   pstatus.pubtype.name]),
                                 email=pstatus.email,
                                 engine=comp.engine)
    if comp.exit_code != 0 or comp.status != CompileStatus.COMPILATION_SUCCESS or comp.error_log:
        return render_template('view.html', **data)
    if comp.venue == 'cic': # special handling for this journal.
        if version == Version.CANDIDATE.value:
            formdata = MultiDict({'email': comp.email,
                                  'version': Version.CANDIDATE.value,
                                  'paperid': comp.paperid,
                                  'auth': create_hmac([comp.paperid, version, comp.email])})
            form = CompileForCopyEditForm(formdata=formdata)
            data['form'] = form
            data['next_action'] = 'copy editing'
        else: # version == Version.FINAL.value
            formdata = MultiDict({'paperid': comp.paperid,
                                  'email': comp.email,
                                  'auth': create_hmac([comp.paperid,
                                                       Version.FINAL.value,
                                                       comp.email])})
            form = NotifyFinalForm(formdata=formdata)
            data['form'] = form
            data['next_action'] = 'final review'
    else: # these do not go through peer review yet.
        formdata = MultiDict({'paperid': comp.paperid,
                              'email': comp.email,
                              'auth': create_hmac([comp.paperid,
                                                   Version.FINAL.value,
                                                   comp.email])})
        form = NotifyFinalForm(formdata=formdata)
        data['form'] = form
        data['next_action'] = 'final publication'
    return render_template('view.html', **data)

"""
This provides an HTML fragment showing the source file with line numbers.
"""
@home_bp.route('/source/<paperid>/<version>/<auth>', methods=['GET'])
def view_source(paperid, version, auth):
    """Note: in this view, auth is computed from paperid, version, '', ''."""
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    if not validate_version(version):
        return render_template('message.html',
                               title='Invalid version',
                               error='Invalid version')
    if not validate_hmac([paperid, version], auth):
        return render_template('message.html',
                               title = 'Invalid hmac',
                               error = 'Invalid hmac')
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid) / Path(version)
    output_dir = paper_dir / Path('output')
    output_files = sorted([str(p.relative_to(str(output_dir))) for p in output_dir.rglob('*') if p.is_file()])
    filename = request.args.to_dict().get('filename')
    if not filename:
        data = {'input_files': output_files}
    else:
        source_file = output_dir / Path(filename)
        if not source_file.is_file():
            return render_template('message.html',
                                   title='Missing filename',
                                   error='Missing filename parameter')
        else:
            if source_file.stat().st_size > 10000000:
                data = {'input_files': output_files,
                        'message': 'File is too large to view'}
                return render_template('view_source.html', **data)
            try:
                data = {'lines': source_file.read_text(encoding='UTF-8', errors='replace').splitlines()}
            except Exception as e:
                return render_template('message.html',
                                       title='Unable to display file',
                                       error='Unable to display file: ' + str(e))
    return render_template('view_source.html', **data)

# TODO: add /<hmac> to the end
@home_bp.route('/output/<paperid>/<version>', methods=['GET'])
def download_output_zipfile(version, paperid):
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    if not validate_version(version):
        return render_template('message.html',
                               title='Invalid version',
                               error='Invalid version')
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid) / Path(version)
    output_dir =  paper_dir / Path('output')
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                archive_path = os.path.relpath(file_path, output_dir)
                zf.write(file_path, archive_path)
    memory_file.seek(0)
    return send_file(memory_file, download_name='output.zip', as_attachment=True)

@home_bp.route('/iacrcc', methods=['GET'])
def iacrcc_homepage():
    return render_template('iacrcc.html', title='iacrcc document class')

@home_bp.route('/iacrcc/convertllncs', methods=['GET'])
def iacrcc_convertllncs():
    md_file = Path(app.root_path) / Path('metadata/latex/iacrcc/convertllncs.md')
    md = md_file.read_text(encoding='UTF-8')
    html5 = markdown.markdown(md, extensions=['fenced_code'], output_format='html5')
    return render_template('embed_html.html',
                           title='Converting llncs to iacrcc',
                           html = html5)

@home_bp.route('/iacrcc/convertiacrtrans', methods=['GET'])
def iacrcc_convertiacrtrans():
    md_file = Path(app.root_path) / Path('metadata/latex/iacrcc/convertiacrtrans.md')
    md = md_file.read_text(encoding='UTF-8')
    html5 = markdown.markdown(md, extensions=['fenced_code'], output_format='html5')
    return render_template('embed_html.html',
                           title='Converting iacrtrans to iacrcc',
                           html = html5)
    
@home_bp.route('/iacrcc/convertieeetran', methods=['GET'])
def iacrcc_convertieeetran():
    md_file = Path(app.root_path) / Path('metadata/latex/iacrcc/convertieeetran.md')
    md = md_file.read_text(encoding='UTF-8')
    html5 = markdown.markdown(md, extensions=['fenced_code'], output_format='html5')
    return render_template('embed_html.html',
                           title='Converting ieeetran to iacrcc',
                           html = html5)
    
@home_bp.route('/iacrcc/iacrdoc.pdf', methods=['GET'])
def iacrdoc_pdf():
    pdf_path = Path(os.path.dirname(os.path.abspath(__file__))) / Path('metadata/latex/iacrcc/iacrdoc.pdf')
    if pdf_path.is_file():
        return send_file(str(pdf_path.absolute()), mimetype='application/pdf')

@home_bp.route('/iacrcc.zip', methods=['GET'])
def download_iacrcc_zipfile():
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        iacrcc_dir = Path(os.path.dirname(os.path.abspath(__file__))) / Path('metadata/latex/iacrcc')
        for file in iacrcc_dir.iterdir():
            if file.name in ['iacrcc.cls', 'iacrcc.bst', 'iacrdoc.tex', 'template.tex', 'template.bib', 'biblio.bib']:
                zf.write(file, arcname=('iacrcc/' + file.name))
    memory_file.seek(0)
    return send_file(memory_file, download_name='iacrcc.zip', as_attachment=True)

@home_bp.route('/funding')
def show_funding():
    data = {'title': 'Funding and affiliation data',
            'countries': countries,
            'search_url': app.config['FUNDING_SEARCH_URL']}
    return render_template('funding.html', **data)

@home_bp.route('/funding/view/<id>')
def view_funder(id):
    try:
        r = requests.get(app.config['FUNDING_SEARCH_URL'], params={'textq': 'id:'+ id})
        if r.status_code == 200:
            results = r.json().get('results')
            if len(results) > 0:
                result = {'item': results[0]}
            else:
                result = {'error': 'No such item'}
        else:
            result = {'error': 'No search response'}
    except Exception as e:
        result = {'error': 'Exception while fetching: ' + str(e)}
    result['search_url'] = app.config['FUNDING_SEARCH_URL']
    result['countries'] = countries
    return render_template('funding.html', **result)

@home_bp.route('/cryptobib')
def show_cryptobib():
    return render_template('cryptobib.html',
                           title='Search on cryptobib',
                           search_url=app.config['FUNDING_SEARCH_URL'])

@home_bp.route('/about', methods=['GET'])
def about():
    return render_template('about.html', title='About this site')
