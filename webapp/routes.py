import datetime
from io import BytesIO
from flask import json, Blueprint, render_template, request, jsonify, send_file, redirect, url_for
from flask import current_app as app
from flask_mail import Message
import os
from pathlib import Path
from . import executor, mail, task_queue, TaskStatus
import shutil
import string
import zipfile
from .metadata.compilation import Compilation, CompileStatus, PaperStatusEnum, PaperStatus, LogEvent, VenueEnum
from .metadata import validate_paperid, get_doi, validate_version
from webapp.tasks import run_latex_task
from .fundreg.search_lib import search

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

def _validate_post(args, files):
    """args should contain paperid and email. files should contain zipfile."""
    if 'paperid' not in args:
        return 'Missing paperid'
    if 'email' not in args:
        return 'Missing author email'
    if 'submitted' not in args:
        return 'Missing submitted date'
    if 'accepted' not in args:
        return 'Missing accepted date'
    if 'venue' not in args:
        return 'Missing venue'
    # TODO: validate the hmac.
    if 'hmac' not in args:
        return 'Missing hmac'
    if 'zipfile' not in files:
        return 'Missing zip file'
    version = args.get('version')
    if not version:
        return 'Missing version'
    if not validate_version(version):
        return 'Invalid version:{}'.format(version)
    return None

@home_bp.route('/submit', methods=['GET'])
def submitform():
    # TODO: authenticate the auth argument and paperid.
    args = request.args.to_dict()
    version = args.get('version', 'candidate')
    if not validate_version(version):
        msg = 'Invalid version: {}'.format(version),
        return render_template('message.html',
                               title = msg,
                               error = msg)
    data = {'title': 'Test submit a paper',
            'version': version,
            'paperid': ''} # TODO: fix this. It is now supplied by javascript for testing.
    if 'paperid' in args:
        paperid = args.get('paperid')
        if not validate_paperid(paperid):
            return render_template('message.html',
                                   title='Invalid character in paperid',
                                   error='paperid is restricted to using characters -.a-z0-9')
        data['email'] = args.get('email', '')
        data['paperid'] = paperid
    return render_template('submit.html', **data)

@home_bp.route('/submit', methods=['POST'])
def runlatex():
    args = request.form.to_dict()
    msg = _validate_post(args, request.files)
    version = args.get('version')
    if msg:
        return render_template('message.html',
                               title='Invalid parameters',
                               error=msg)
    paperid = args.get('paperid')
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Invalid character in paperid',
                               error='paperid is restricted to using characters -.a-z0-9')
    if task_queue.get(paperid):
        return render_template('message.html',
                               title='Another one is running',
                               error='At most one compilation may be queued on each paper.')
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    paper_dir.mkdir(parents=True, exist_ok=True)
    json_file = paper_dir / Path('status.json')
    if json_file.is_file():
        paper_status = PaperStatus.parse_raw(json_file.read_text(encoding='utf-8'))
        paper_status.log.append(LogEvent(when=datetime.datetime.now(),
                                         action='Upload of zip file'))
    else:
        paper_status_data = {'paperid': paperid,
                             'status': PaperStatusEnum.PENDING,
                             'email': args.get('email'),
                             'venue': args.get('venue'),
                             'submitted': args.get('submitted'),
                             'accepted': args.get('accepted'),
                             'log': [{'when': datetime.datetime.now(),
                                      'action': 'Upload of zip file'}]}
        paper_status = PaperStatus(**paper_status_data)
    # Save a json file with minimal metadata for debugging. This will
    # be updated at the end of the run.
    json_file.write_text(paper_status.json(indent=2))
    # TODO: handle the upload of the 'final' version as well.
    candidate_dir = paper_dir / Path('candidate')
    # TODO: this blows away everything for candidate version.
    if candidate_dir.is_dir():
        shutil.rmtree(candidate_dir)
    candidate_dir.mkdir(parents=True)
    # Unzip the zip file into submitted_dir
    zip_path = candidate_dir / Path('all.zip')
    request.files['zipfile'].save(zip_path)
    input_dir = candidate_dir / Path('input')
    try:
        zip_file = zipfile.ZipFile(zip_path)
        zip_file.extractall(input_dir)
    except Exception as e:
        paper_status.log.append(LogEvent(when=datetime.datetime.now(),
                                         action='Zip file could not be unzipped'))
        json_file.write_text(paper_status.json(indent=2))
        return redirect(url_for('home_bp.view_results', paperid=paperid, version=version), 302)
    tex_file = input_dir / Path('main.tex')
    if not tex_file.is_file():
        paper_status.log.append(LogEvent(when=datetime.datetime.now(),
                                         action='Zip file did not have main.tex at top level'))
        json_file.write_text(paper_status.json(indent=2))
        # then no sense trying to compile
        return render_template('message.html',
                               title='Missing main.tex',
                               error='Your zip file should contain main.tex at the top level.')
    compilation_data = {'paperid': paperid,
                        'status': CompileStatus.COMPILING,
                        'email': args.get('email'),
                        'venue': args.get('venue'),
                        'submitted': args.get('submitted'),
                        'accepted': args.get('accepted'),
                        'compiled': datetime.datetime.now(),
                        'error_log': [],
                        'warning_log': [],
                        'zipfilename': request.files['zipfile'].filename}
    compilation = Compilation(**compilation_data)
    compilation_file = candidate_dir / Path('compilation.json')
    compilation_file.write_text(compilation.json(indent=2))
    receivedDate = datetime.datetime.strptime(args.get('submitted')[:10],'%Y-%m-%d')
    acceptedDate = datetime.datetime.strptime(args.get('accepted')[:10],'%Y-%m-%d')
    publishedDate = datetime.date.today().strftime('%Y-%m-%d')
    metadata = '\\def\\IACR@DOI{' + get_doi(paperid) + '}\n'
    metadata += '\\def\\IACR@Received{' + receivedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Accepted{' + acceptedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Published{' + publishedDate + '}\n'
    metadata_file = input_dir / Path('main.iacrmetadata')
    metadata_file.write_text(metadata)
    output_dir = candidate_dir / Path('output')
    # Remove output from any previous run.
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    # fire off a separate task to compile
    task_queue[paperid] = executor.submit(run_latex_task, str(input_dir.absolute()),
                                                          str(output_dir.absolute()),
                                                          paperid)
    msg = Message('Paper {} was submitted'.format(paperid),
                  sender=app.config['EDITOR_EMAILS'],
                  recipients=['iacrcc@digicrime.com']) # for testing
    msg.body = 'This is just a test message for now. See https://publish.iacr.org/view/{}/{}'.format(paperid, version)
    mail.send(msg)
    data = {'title': 'Compiling your LaTeX',
            'paperid': paperid,
            'version': version}
    return render_template('running.html', **data)

@home_bp.route('/tasks/<paperid>/<version>', methods=['GET'])
def get_status(paperid, version):
    """Check on the current status of a compilation via ajax."""
    status = TaskStatus.UNKNOWN
    if not validate_paperid(paperid):
        return jsonify({'status': TaskStatus.UNKNOWN, 'msg': 'Invalid paperid'})
    if not validate_version(version):
        return jsonify({'status': TaskStatus.UNKNOWN, 'msg': 'Unknown version'}), 200
    msg = 'Unknown status'
    # is the task in the queue or running?
    future = task_queue.get(paperid, None)
    if future:
        if future.cancelled():
            status = TaskStatus.CANCELLED
            msg = 'Compilation was cancelled'
            task_queue.pop(paperid, None)
        elif future.running():
            status = TaskStatus.RUNNING
            msg = 'Compilation is running'
        elif future._exception:
            status = TaskStatus.FAILED_EXCEPTION
            msg = 'An exception occurred: {}'.format(str(future._exception))
        elif future.done(): # must have returned a result
            status = TaskStatus.COMPILED
            msg = future.result()
            # Tasks that are done should remove themselves. Should not happen.
            task_queue.pop(paperid, None)
        else: # it's enqueued
            status = TaskStatus.COMPILING
            try:
                position = tuple(task_queue.keys()).index(paperid)
                size = len(task_queue)
                msg = 'Pending (position {} out of {})'.format(position, size)
            except Exception:
                msg = 'Unknown position'
    else:
        # we rely upon the json file
        paper_path = Path(app.config['DATA_DIR']) / Path(paperid)
        if not paper_path.is_dir():
            status = TaskStatus.UNKNOWN
        else:
            json_file = paper_path / Path('compilation.json')
            if not json_file.is_file():
                status = TaskStatus.UNKNOWN
                msg = 'Cannot find JSON file'
            else:
                comp = Compilation.parse_raw(json_file.read_text(encoding='UTF-8'))
                if comp.exit_code == -1: # default
                    status = TaskStatus.UNKNOWN
                    msg = 'Unknown status'
                elif comp.exit_code == 0:
                    status = TaskStatus.COMPILED
                    msg = 'Successfully compiled'
                else:
                    status = TaskStatus.FAILED_COMPILE
                    msg = 'Exit code from latexmk was {}'.format(comp.exit_code)
    return jsonify({'status': status.value, 'msg': msg}), 200

@home_bp.route('/pdf/<paperid>/<version>/main.pdf', methods=['GET'])
def show_pdf(paperid,version):
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    if not validate_version(version):
        msg = 'Invalid version {}'.format(version)
        return render_template('message.html',
                               title=msg,
                               error=msg)
    pdf_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(version) / Path('output/main.pdf')
    if pdf_path.is_file():
        return send_file(str(pdf_path.absolute()), mimetype='application/pdf')
    return render_template('message.html',
                           title='Unable to retrieve file {}'.format(str(pdf_path.absolute())),
                           error='Unknown file. This is a bug')
    
def _expand_dir(path):
    """Return a file tree for a directory."""
    node = []
    for dir in sorted(path.iterdir()):
        child = {'name': dir.name}
        if dir.is_dir():
            child['children'] = _expand_dir(dir)
        node.append(child)
    return node


# when a paper fails to compile or has nonempty error_log, show just
# the error log compile_error.html
# if iacrcc, then show iacrcc_success.html
# if not iacrcc then show a generic one without metadata. generic_success.html

# We decide whether to show the "submit final" button based on whether
# exit_code ==0 and compilation.error_log is empty.
@home_bp.route('/view/<paperid>/<version>', methods=['GET'])
def view_results(paperid, version):
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    if not validate_version(version):
        return render_template('message.html',
                               title='Invalid version',
                               error='Invalid version')
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
                               error='Paper was not compiled: no directory {}'.format(str(output_path)))
    input_tree = []
    output_dir = paper_path / Path('output')
    data['output'] = _expand_dir(output_dir)
    pdf_file = output_path / Path('main.pdf')
    meta_file = output_path / Path('main.meta')
    if meta_file.is_file():
        data['metafile'] = meta_file.read_text(encoding='UTF-8')
    if pdf_file.is_file():
        data['pdf'] = True
    if comp.exit_code != 0 or comp.status != CompileStatus.COMPILATION_SUCCESS or comp.error_log:
        return render_template('compile_fail.html', **data)
    if comp.venue == VenueEnum.IACRCC:
        return render_template('view_iacrcc.html', **data)
    return render_template('view_generic.html', **data)

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
