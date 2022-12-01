import datetime
from io import BytesIO
import json
from flask import Blueprint, render_template, request, jsonify, send_file
from flask import current_app as app
from flask_mail import Message
import os
from pathlib import Path
from . import executor, mail, task_queue, PaperStatus
import shutil
import string
import zipfile
from .metadata.compilation import Compilation, StatusEnum
from .metadata import validate_paperid, get_doi
from webapp.tasks import run_latex_task

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
    return None

@home_bp.route('/submit', methods=['GET'])
def submitform():
    # TODO: authenticate the auth argument and paperid.
    args = request.args.to_dict()
    data = {'title': 'Test submit a paper',
            'paperid': ''} # TODO: fix this. It is now supplied by javascript for testing.
    if 'paperid' in args:
        paperid = args.get('paperid')
        if not validate_paperid(paperid):
            return render_template('message.html',
                                   title='Invalid character in paperid',
                                   error='paperid is restricted to using characters -.a-z0-9')
        data['paperid'] = paperid
    return render_template('submit.html', **data)

@home_bp.route('/submit', methods=['POST'])
def runlatex():
    args = request.form.to_dict()
    msg = _validate_post(args, request.files)
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
    if paper_dir.is_dir():
        shutil.rmtree(paper_dir)
    paper_dir.mkdir(parents=True)
    # Save a json file with minimal metadata for debugging. This will
    # be updated at the end of the run.
    json_data = {'paperid': paperid,
                 'status': StatusEnum.PENDING,
                 'email': args.get('email'),
                 'venue': args.get('venue'),
                 'submitted': args.get('submitted'),
                 'accepted': args.get('accepted'),
                 'compiled': datetime.datetime.now(),
                 'error_log': []}
    compilation = Compilation(**json_data)
    json_file = paper_dir / Path('compilation.json')
    json_file.write_text(compilation.json(indent=2))
    # Unzip the zip file into paper_dir
    zip_path = paper_dir / Path('all.zip')
    request.files['zipfile'].save(zip_path)
    zip_file = zipfile.ZipFile(zip_path)
    input_dir = paper_dir / Path('input')
    try:
        zip_file.extractall(input_dir)
    except Exception as e:
        return render_template('message.html',
                               title='Unable to unzip zipfile',
                               error='Unable to unzip this zip file.')
    tex_file = input_dir / Path('main.tex')
    receivedDate = datetime.datetime.strptime(args.get('submitted')[:10],'%Y-%m-%d')
    acceptedDate = datetime.datetime.strptime(args.get('accepted')[:10],'%Y-%m-%d')
    publishedDate = datetime.date.today().strftime('%Y-%m-%d')
    metadata = '\\def\\IACR@DOI{' + get_doi(paperid) + '}\n'
    metadata += '\\def\\IACR@Received{' + receivedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Accepted{' + acceptedDate.strftime('%Y-%m-%d') + '}\n'
    metadata += '\\def\\IACR@Published{' + publishedDate + '}\n'
    metadata_file = input_dir / Path('main.iacrmetadata')
    metadata_file.write_text(metadata)
    if not tex_file.is_file():
        compilation.status = StatusEnum.MALFORMED_ZIP
        compilation.error_log.append('Zip file required to have main.tex at top level')
        json_file.write_text(compilation.json(indent=2))
        # then no sense trying to compile
        return render_template('message.html',
                               title='Missing main.tex',
                               error='Your zip file should contain main.tex at the top level.')
    output_dir = paper_dir / Path('output')
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
    msg.body = 'This is just a test message for now. See https://publish.iacr.org/view/{}'.format(paperid)
    mail.send(msg)
    data = {'title': 'Compiling your LaTeX',
            'paper_id': paperid}
    return render_template('running.html', **data)

@home_bp.route('/tasks/<paper_id>', methods=['GET'])
def get_status(paper_id):
    """Check on the current status of a compilation via ajax."""
    status = PaperStatus.UNKNOWN
    msg = 'Unknown status'
    # is the task in the queue or running?
    future = task_queue.get(paper_id, None)
    if future:
        if future.cancelled():
            status = PaperStatus.CANCELLED
            msg = 'Compilation was cancelled'
            task_queue.pop(paper_id, None)
        elif future.running():
            status = PaperStatus.RUNNING
            msg = 'Compilation is running'
        elif future._exception:
            status = PaperStatus.FAILED_EXCEPTION
            msg = 'An exception occurred: {}'.format(str(future._exception))
        elif future.done(): # must have returned a result
            status = PaperStatus.COMPILED
            msg = future.result()
            # Tasks that are done should remove themselves. Should not happen.
            task_queue.pop(paper_id, None)
        else: # it's enqueued
            status = PaperStatus.PENDING
            try:
                position = tuple(task_queue.keys()).index(paper_id)
                size = len(task_queue)
                msg = 'Pending (position {} out of {})'.format(position, size)
            except Exception:
                msg = 'Unknown position'
    else:
        # we rely upon the json file
        paper_path = Path(app.config['DATA_DIR']) / Path(paper_id)
        if not paper_path.is_dir():
            status = PaperStatus.UNKNOWN
        else:
            json_file = paper_path / Path('compilation.json')
            if not json_file.is_file():
                status = PaperStatus.UNKNOWN
                msg = 'Cannot find JSON file'
            else:
                comp = Compilation.parse_raw(json_file.read_text(encoding='UTF-8'))
                if comp.exit_code == -1: # default
                    status = PaperStatus.UNKNOWN
                    msg = 'Unknown status'
                elif comp.exit_code == 0:
                    status = PaperStatus.COMPILED
                    msg = 'Successfully compiled'
                else:
                    status = PaperStatus.FAILED_COMPILE
                    msg = 'Exit code from latexmk was {}'.format(comp.exit_code)
    return jsonify({'status': status.value, 'msg': msg}), 200

@home_bp.route('/pdf/<paperid>/main.pdf', methods=['GET'])
def show_pdf(paperid):
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    pdf_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path('output/main.pdf')
    if pdf_path.is_file():
        return send_file(str(pdf_path.absolute()), mimetype='application/pdf')
    return render_template('message.html',
                           title='Unable to retrieve file {}'.format(str(pdf_path.absolute())),
                           error='Unknown file. This is a bug')
    
def _expand_dir(path):
    node = []
    for dir in sorted(path.iterdir()):
        child = {'name': dir.name}
        if dir.is_dir():
            child['children'] = _expand_dir(dir)
        node.append(child)
    return node


@home_bp.route('/view/<paperid>', methods=['GET'])
def view_results(paperid):
    if not validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')

    paper_path = Path(app.config['DATA_DIR']) / Path(paperid)
    if not paper_path.is_dir():
        return render_template('message.html',
                               title='Unknown paper',
                               error='Unknown paper. Try resubmitting.')
    output_path = paper_path / Path('output')
    if not output_path.is_dir():
        return render_template('message.html',
                               title='Paper was not compiled',
                               error='Paper was not compiled')
    data = {'title': 'Results from compilation', 'paperid': paperid}
    try:
        json_file = paper_path / Path('compilation.json')
        comp = Compilation.parse_raw(json_file.read_text(encoding='UTF-8'))
        data['comp'] = comp
    except Exception as e:
        data['error_log'] = ['Unable to parse compilation: ' + str(e)]
    input_tree = []
    output_dir = paper_path / Path('output')
    data['output'] = _expand_dir(output_dir)
    pdf_file = output_path / Path('main.pdf')
    meta_file = output_path / Path('main.meta')
    if meta_file.is_file():
        data['metafile'] = meta_file.read_text(encoding='UTF-8')
    if pdf_file.is_file():
        data['pdf'] = True
    return render_template('view.html', **data)

@home_bp.route('/output/<paperid>', methods=['GET'])
def download_output_zipfile(paperid):
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
