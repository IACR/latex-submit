import datetime
from io import BytesIO
from flask import json, Blueprint, render_template, request, jsonify, send_file, redirect, url_for
from flask import current_app as app
from flask_mail import Message
import hmac
import os
from pathlib import Path
from . import executor, mail, task_queue, get_json_path, get_pdf_url, validate_hmac, create_hmac, paper_key, db, admin
import shutil
import string
from .db_models import CompileRecord, validate_version, TaskStatus, PaperStatus, Version, log_event
import zipfile
from .metadata.compilation import Compilation, CompileStatus, PaperStatusEnum, VenueEnum, FileTree
from .metadata import validate_paperid, get_doi
from .tasks import run_latex_task
from .fundreg.search_lib import search
from .forms import SubmitForm, CompileForCopyEditForm
from werkzeug.datastructures import MultiDict
import logging

ENGINES = {'lualatex': 'latexmk -g -pdflua -lualatex="lualatex --disable-write18 --nosocket --no-shell-escape" main',
           'pdflatex': 'latexmk -g -pdf -pdflatex="pdflatex -interaction=nonstopmode -disable-write18 -no-shell-escape" main',
           'xelatex': 'latexmk -g -pdfxe -xelatex="xelatex -interaction=nonstopmode -file-line-error -no-shell-escape" main'}

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
    form = SubmitForm(formdata=request.args)
    # We only perform partial validation on the GET request to make sure that
    # the auth token is valid.
    if not form.check_auth():
        if app.config['TESTING']:
            logging.warning('TESTING MODE ONLY')
            # go ahead and send a clean form anyway.
            form = SubmitForm(formdata=request.args)
        else:
            logging.warning('{}:{}:{} form not authenticated'.format(form.paperid.data,
                                                                     form.version.data,
                                                                     form.auth.data))
            return render_template('message.html',
                                   title='This submission is not authorized.',
                                   error='The token for this request is invalid')
    paperid = form.paperid.data
    # Submission form is only shown for papers that have no status or have status
    # of PENDING or EDIT_FINISHED. The latter is when the author is submitting
    # their final version.
    sql = db.select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    # legacy API: paper_status = PaperStatus.query.filter_by(paperid=paperid).first()
    if paper_status:
        if (paper_status.status != PaperStatusEnum.PENDING.value and
            paper_status.status != PaperStatusEnum.EDIT_FINISHED.value):
            return render_template('message.html',
                                   title='This submission is not authorized.',
                                   error='The paper should not be in this state: {}'.format(paper_status.status.value))
        elif (paper_status.status == PaperStatusEnum.EDIT_FINISHED.value and
              form.version.data != Version.FINAL.value):
            return render_template('message.html',
                                   title='Wrong version',
                                   error='Version should be FINAL. This is a bug')
    return render_template('submit.html', form=form)

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
    args = request.form.to_dict()
    paperid = args.get('paperid')
    version = args.get('version', Version.CANDIDATE.value)
    accepted = args.get('accepted', '')
    submitted = args.get('submitted', '')
    task_key = paper_key(paperid, version)
    now = datetime.datetime.now()
    form = SubmitForm()
    if task_queue.get(task_key):
        log_event(paperid, 'Attempt to resubmit while compiling')
        msg = 'Already running {}:{}'.format(form.paperid.data,
                                             form.version.data)
        logging.warning(msg)
        return render_template('message.html',
                               title='Another one is running',
                               error='At most one compilation may be queued on each paper.')
    if not form.validate_on_submit():
        logging.error('Validation failed {}:{}:{}'.format(form.paperid.data,
                                                          form.version.data,
                                                          form.auth.data))
        form.auth.errors.append('Validation failed')
        return render_template('submit.html', form=form)
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    paper_dir.mkdir(parents=True, exist_ok=True)
    sql = db.select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    # legacy API: paper_status = PaperStatus.query.filter_by(paperid=paperid).first()
    if not paper_status:
        paper_status = PaperStatus(paperid=paperid,
                                   venue=args.get('venue'),
                                   email=args.get('email'),
                                   submitted=submitted,
                                   accepted=accepted,
                                   status=PaperStatusEnum.PENDING.value)
        db.session.add(paper_status)
        db.session.commit()
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
        db.session.add(paper_status)
        db.session.commit()
    if (paper_status.status == PaperStatusEnum.EDIT_FINISHED or
        paper_status.status == PaperStatusEnum.FINAL_SUBMITTED):
        # TODO: check that discussion items are finished
        version = Version.FINAL.value
    log_event(paperid, 'Upload of zip file for {}'.format(version))
    version_dir = paper_dir / Path(version)
    # This blows everything away for the version.
    if version_dir.is_dir():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True)
    # Unzip the zip file into submitted_dir
    zip_path = version_dir / Path('all.zip')
    try:
        request.files['zipfile'].save(zip_path)
    except Exception as e:
        logging.error('Unable to save zip file: {}'.format(str(e)))
        form.zipfile.errors.append('unable to save zip file')
        return render_template('submit.html', form=form)
    input_dir = version_dir / Path('input')
    try:
        zip_file = zipfile.ZipFile(zip_path)
        zip_file.extractall(input_dir)
    except Exception as e:
        logging.error('Unable to extract from zip file: {}'.format(str(e)))
        log_event(paperid, 'Zip file could not be unzipped')
        form.zipfile.errors.append('Unable to extract from zip file: {}'.format(str(e)))
        return render_template('submit.html', form=form)
    tex_file = input_dir / Path('main.tex')
    if not tex_file.is_file():
        log_event(paperid, 'Zip file did not have main.tex at top level')
        form.zipfile.errors.append('Your zip file should contain main.tex at the top level')
        # then no sense trying to compile
        return render_template('submit.html', form=form)
    command = ENGINES.get(args.get('engine'))
    compilation_data = {'paperid': paperid,
                        'status': CompileStatus.COMPILING,
                        'email': args.get('email'),
                        'venue': args.get('venue'),
                        'submitted': submitted,
                        'accepted': accepted,
                        'compiled': now,
                        'command': command,
                        'error_log': [],
                        'warning_log': [],
                        'zipfilename': request.files['zipfile'].filename}
    compilation = Compilation(**compilation_data)
    sql = db.select(CompileRecord).filter_by(paperid=paperid).filter_by(version=version)
    comprec = db.session.execute(sql).scalar_one_or_none()
    # legacy API: comprec = CompileRecord.query.filter_by(paperid=paperid,version=version).first()
    if not comprec:
        comprec = CompileRecord(paperid=paperid,version=version)
    comprec.task_status = TaskStatus.PENDING
    comprec.started = now
    compstr = compilation.json(indent=2, exclude_none=True)
    comprec.result = compstr
    db.session.add(comprec)
    db.session.commit()
    compilation_file = version_dir / Path('compilation.json')
    compilation_file.write_text(compstr, encoding='UTF-8')
    receivedDate = datetime.datetime.strptime(submitted[:10],'%Y-%m-%d')
    acceptedDate = datetime.datetime.strptime(accepted[:10],'%Y-%m-%d')
    publishedDate = datetime.date.today().strftime('%Y-%m-%d')
    metadata = '\\def\\IACR@DOI{' + get_doi(paperid) + '}\n'
    metadata += '\\def\\IACR@Received{' + receivedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Accepted{' + acceptedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Published{' + publishedDate + '}\n'
    metadata_file = input_dir / Path('main.iacrmetadata')
    metadata_file.write_text(metadata)
    output_dir = version_dir / Path('output')
    # Remove output from any previous run.
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    # fire off a separate task to compile. We wrap run_latex_task so it
    # can have the flask context to use sqlalchemy on the database.
    task_queue[task_key] = executor.submit(context_wrap(run_latex_task),
                                           command,
                                           str(version_dir.absolute()),
                                           paperid,
                                           version,
                                           task_key)
    msg = Message('Paper {} was submitted'.format(paperid),
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=['iacrcc@digicrime.com']) # for testing
    paper_url = url_for('home_bp.view_results',
                        paperid=paperid,
                        version=version,
                        auth=create_hmac(paperid, version, '', ''),
                        _external=True)
    msg.body = 'This is just a test message for now.\n\nYour paper will be viewable at {}'.format(paper_url)
    mail.send(msg)
    status_url = paper_url.replace('/view/', '/tasks/')
    data = {'title': 'Compiling your LaTeX',
            'status_url': status_url,
            'headline': 'Compiling your paper'}
    return render_template('running.html', **data)

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
    sql = db.select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: paper_status = PaperStatus.query.filter_by(paperid=paperid).first()
    if not paper_status:
        return render_template('message.html',
                               title='Missing status',
                               error='Paper status does not exist. This is a bug')
    # TODO: enable generating copy edit version from other states.
    if paper_status.status != PaperStatusEnum.PENDING:
        return render_template('message.html',
                               title='Paper was already sent to copy editor',
                               error = 'Paper was already sent for copy editing.')
    task_key = paper_key(paperid, Version.COPYEDIT.value)
    if task_queue.get(task_key):
        log_event(paperid, 'Attempt to resubmit while compiling')
        msg = 'Already running {}:{}'.format(form.paperid.data,
                                             Version.COPYEDIT.value)
        logging.warning(msg)
        return render_template('message.html',
                               title='Another one is running',
                               error='At most one compilation may be queued on each paper.')
    sql = db.select(CompileRecord).filter_by(paperid=paperid, version=form.version.data)
    version_comprec = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: version_comprec = CompileRecord.query.filter_by(paperid=paperid,version=form.version.data).first()
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
    version_compilation = Compilation.parse_raw(version_compilation)
    # TODO: if we switch to having the editor assign a copy editor, then
    # the status will be set to PaperStatusEnum.SUBMITTED. For now we set it
    # to EDIT_PENDING, assuming that the assignment of copy editor is automatic.
    paper_status.status = PaperStatusEnum.EDIT_PENDING
    db.session.add(paper_status)
    db.session.commit()
    log_event(paperid, 'Paper {} submitted for copy edit'.format(paperid))
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
    sql = db.select(CompileRecord).filter_by(paperid=paperid, version=Version.COPYEDIT.value)
    copyedit_comprec = db.session.execute(sql).scalar_one_or_none()
    # Legacy API: copyedit_comprec = CompileRecord.query.filter_by(paperid=paperid,version=Version.COPYEDIT.value).first()
    if not copyedit_comprec:
        copyedit_comprec = CompileRecord(paperid=paperid,version=Version.COPYEDIT.value)
    copyedit_comprec.task_status = TaskStatus.PENDING
    now = datetime.datetime.now()
    copyedit_comprec.started = now
    copyedit_comprec.task_status = TaskStatus.PENDING
    compilation = Compilation(**{'paperid': paperid,
                                 'status': CompileStatus.COMPILING,
                                 'version': Version.COPYEDIT.value,
                                 'email': version_compilation.email,
                                 'venue': version_compilation.venue,
                                 'submitted': version_compilation.submitted,
                                 'accepted': version_compilation.accepted,
                                 'compiled': now,
                                 'command': version_compilation.command,
                                 'error_log': [],
                                 'warning_log': [],
                                 'zipfilename': version_compilation.zipfilename})
    command = version_compilation.command
    compstr = compilation.json(indent=2, exclude_none=True)
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
                                           command,
                                           str(copyedit_dir.absolute()),
                                           paperid,
                                           Version.COPYEDIT.value,
                                           task_key)
    status_url = url_for('home_bp.get_status',
                         paperid=paperid,
                         version=Version.COPYEDIT.value,
                         auth=create_hmac(paperid, Version.COPYEDIT.value, '', ''),
                         _external=True)
    # Notify the copy editor.
    msg = Message('Paper {} is ready for copy editing'.format(paperid),
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=[app.config['COPYEDITOR_EMAILS']]) # for testing
    copyedit_url = url_for('admin_file.copyedit', paperid=paperid, _external=True)
    msg.body = 'A paper for CiC needs copy editing.\n\nYou can view it at {}'.format(copyedit_url)
    mail.send(msg)
    if 'TESTING' in app.config:
        print(msg.body)
    data = {'title': 'Compiling your LaTeX for copy editor',
            'status_url': status_url,
            'headline': 'Recompiling your paper with line numbers for the copy editor'}
    return render_template('running.html', **data)


@home_bp.route('/copyedit/<paperid>/<auth>', methods=['GET'])
def view_copyedit(paperid, auth):
    if not validate_hmac(paperid, '', '', '', auth):
        return render_template('message.html',
                               title='Invalid request',
                               error='Your authentication cannot be verified')
    sql = db.select(PaperStatus).filter_by(paperid=paperid)
    paper_status = db.session.execute(sql).scalar_one_or_none()
    if paper_status:
        if paper_status.status == PaperStatusEnum.EDIT_PENDING.value:
            return render_template('message.html',
                                   title='Your copy edit was submitted',
                                   message='You will receive an email when the copy editor finishes with your paper')
        elif paper_status.status == PaperStatusEnum.EDIT_FINISHED.value:
            # TODO: add template for responding to copy editing.
            return render_template('message.html',
                                   title='Respond to your copy edit',
                                   message='This will be for responding to the copy editing when it is finished. This is TBD.')
        else:
            # TODO: handle the other cases like SUBMITTED or PENDING.
            return render_template('message.html',
                                   title='Error in paper status',
                                   message='Your paper has status {}. This should not happen.'.format(paper_status.status))
    else:
        return render_template('message.html',
                               title='Unknown paper',
                               error='Unknown paper')

@home_bp.route('/tasks/<paperid>/<version>/<auth>', methods=['GET'])
def get_status(paperid, version, auth):
    """Check on the current status of a compilation via ajax.
    This returns a json object with 'url', 'status', and 'msg', and the user will
    be redirected to url when the compilation is completed.
    """
    if not validate_hmac(paperid, version, '', '', auth):
        return jsonify({'status': TaskStatus.ERROR,
                        'msg': 'hmac is invalid'})
    if version == Version.COPYEDIT.value:
        paper_url = url_for('home_bp.view_copyedit',
                            paperid=paperid,
                            auth=create_hmac(paperid, '', '', ''))
    else:
        paper_url = url_for('home_bp.view_results',
                            paperid=paperid,
                            version=version,
                            auth=create_hmac(paperid, version, '', ''))
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
        sql = db.select(CompileRecord).filter_by(paperid=paperid, version=version)
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
    if not validate_hmac(paperid, version, '', '', auth):
        return render_template('message.html',
                               title = 'Invalid hmac',
                               error = 'Invalid hmac')
    pdf_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(version) / Path('output/main.pdf')
    if pdf_path.is_file():
        return send_file(str(pdf_path.absolute()), mimetype='application/pdf')
    return render_template('message.html',
                           title='Unable to retrieve file {}'.format(str(pdf_path.absolute())),
                           error='Unknown file. This is a bug')
    
# when a paper fails to compile or has nonempty error_log, show just
# the error log compile_error.html
# if iacrcc, then show iacrcc_success.html
# if not iacrcc then show a generic one without metadata. generic_success.html

# We decide whether to show the "submit final" button based on whether
# exit_code ==0 and compilation.error_log is empty.
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
    if not validate_hmac(paperid, version, '', '', auth):
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
            'version': version}
    try:
        json_file = paper_path / Path('compilation.json')
        comp = Compilation.parse_raw(json_file.read_text(encoding='UTF-8'))
        data['comp'] = comp
        data['auth'] = create_hmac(paperid, version, comp.submitted, comp.accepted)
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
    comp.output_tree = FileTree.from_path(output_dir)
    pdf_file = output_path / Path('main.pdf')
    meta_file = output_path / Path('main.meta')
    log_file = output_path / Path('main.log')
    if meta_file.is_file():
        data['metafile'] = meta_file.read_text(encoding='UTF-8')
    if pdf_file.is_file():
        data['pdf'] = get_pdf_url(paperid, version)
    if log_file.is_file():
        try:
            data['latexlog'] = log_file.read_text(encoding='UTF-8')
        except Exception as e:
            logging.error('Unable to read log file as UTF-8: {}'.format(paperid))
            # If pdflatex is used, then it can sometimes create a log file that is not
            # readable as UTF-8 (in spite of the _input_ encoding being set to UTF-8).
            # see https://github.com/IACR/latex-submit/issues/26
            data['latexlog'] = log_file.read_text(encoding='iso-8859-1', errors='replace')
    if comp.exit_code != 0 or comp.status != CompileStatus.COMPILATION_SUCCESS or comp.error_log:
        return render_template('compile_fail.html', **data)
    if comp.venue == VenueEnum.IACRCC and version == Version.CANDIDATE.value:
        formdata = MultiDict({'email': comp.email,
                              'version': Version.CANDIDATE.value,
                              'paperid': comp.paperid,
                              'auth': create_hmac(comp.paperid, version, '', comp.email)})
        form = CompileForCopyEditForm(formdata=formdata)
        data['form'] = form
        return render_template('view_iacrcc.html', **data)
    return render_template('view_generic.html', **data)

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
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    output_dir =  paper_dir / Path('output')
    subdir_offset = len(str(paper_dir)) + 1
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for f in output_dir.glob('**/*'):
            zf.write(f, arcname=str(f)[subdir_offset:])
    memory_file.seek(0)
    return send_file(memory_file, download_name='output.zip', as_attachment=True)

@home_bp.route('/iacrcc', methods=['GET'])
def iacrcc_homepage():
    return render_template('iacrcc.html', title='iacrcc document class')

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
    return render_template('funding.html', title='Funding and affiliation data')

@home_bp.route('/funding/view/<id>')
def view_funder(id):
    result = search(app.config['XAPIAN_DB_PATH'],
                    offset=0,
                    textq='id:' + id,
                    locationq=None,
                    app=app)
    if len(result.get('results')) > 0:
        result = {'item': result.get('results')[0]}
    else:
        result = {'error': 'no such item'}
    return render_template('funding.html', **result)

@home_bp.route('/funding/search', methods=['GET'])
def get_results():
    args = request.args.to_dict()
    if 'textq' not in args and 'locationq' not in args:
        return json.jsonify({'error': 'missing queries'})
    return json.jsonify(search(app.config['XAPIAN_DB_PATH'],
                               offset=args.get('offset', 0),
                               textq=args.get('textq'),
                               locationq=args.get('locationq'),
                               source=args.get('source'),
                               app=app))
