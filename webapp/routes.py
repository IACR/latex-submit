import datetime
import json
from flask import Blueprint, render_template, request, jsonify, send_file
from flask import current_app as app
from pathlib import Path
from . import executor, task_queue, PaperStatus
import shutil
import string
import zipfile

from webapp.tasks import run_latex_task

home_bp = Blueprint('home_bp',
                    __name__,
                    template_folder='templates',
                    static_folder='static')

@home_bp.route('/', methods=['GET'])
def home():
    if app.testing:
        return render_template('index.html')
    else:
        return render_template('message.html',
                               title='Debug is not enabled',
                               error='Debug is not enabled')

def _validate_paperid(paperid):
    accepted_chars = string.digits + string.ascii_lowercase + string.ascii_uppercase + '-_'
    return all(c in accepted_chars for c in paperid)

def _validate_post(args, files):
    """args should contain paperid and email. files should contain zipfile."""
    if 'paperid' not in args:
        return 'Missing paperid'
    if 'email' not in args:
        return 'Missing author email'
    if 'zipfile' not in files:
        return 'Missing zip file'
    return None

@home_bp.route('/submit', methods=['POST'])
def runlatex():
    args = request.form.to_dict()
    msg = _validate_post(args, request.files)
    if msg:
        return render_template('message.html',
                               title='Invalid parameters',
                               error=msg)
    paperid = args.get('paperid')
    if not _validate_paperid(paperid):
        return render_template('message.html',
                               title='Invalid character in paperid',
                               error='paperid is restricted to using characters {}'.format(accepted_chars))
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
    json_data = {'email': args.get('email'),
                 'paperid': paperid,
                 'ip_address': request.remote_addr,
                 'date': str(datetime.datetime.now())}
    json_file = paper_dir / Path('meta.json')
    json_file.write_text(json.dumps(json_data, indent=2), encoding='UTF-8')
    # Unzip the zip file into paper_dir
    zip_path = paper_dir / Path('all.zip')
    request.files['zipfile'].save(zip_path)
    zip_file = zipfile.ZipFile(zip_path)
    input_dir = paper_dir / Path('input')
    zip_file.extractall(input_dir)
    output_dir = paper_dir / Path('output')
    # Remove output from any previous run.
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    # fire off a separate task to compile
    task_queue[paperid] = executor.submit(run_latex_task, str(input_dir.absolute()),
                                                          str(output_dir.absolute()),
                                                          paperid)
    data = {'title': 'Compiling your LaTeX',
            'paper_id': paperid}
    return render_template('running.html', **data)

@home_bp.route('/tasks/<paper_id>', methods=['GET'])
def get_status(paper_id):
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
            status = PaperStatus.EXCEPTION
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
            json_file = paper_path / Path('meta.json')
            if not json_file.is_file():
                status = PaperStatus.UNKNOWN
                msg = 'Cannot find JSON file'
            else:
                meta = json.loads(json_file.read_text(encoding='UTF-8'))
                if 'code' not in meta:
                    status = PaperStatus.UNKNOWN
                    msg = 'Unknown status'
                elif meta['code'] == 0:
                    status = PaperStatus.COMPILED
                    msg = 'Successfully compiled'
                else:
                    status = PaperStatus.FAILED_COMPILE
                    msg = 'Exit code from latexmk was {}'.format(meta['code'])
    return jsonify({'status': status.value, 'msg': msg}), 200

@home_bp.route('/pdf/<paperid>/main.pdf', methods=['GET'])
def show_pdf(paperid):
    if not _validate_paperid(paperid):
        return render_template('message.html',
                               title='Unable to retrieve file',
                               error='paperid is invalid')
    pdf_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path('output/main.pdf')
    if pdf_path.is_file():
        return send_file(str(pdf_path.absolute()), mimetype='application/pdf')
    return render_template('message.html',
                           title='Unable to retrieve file {}'.format(str(pdf_path.absolute())),
                           error='Unknown file. This is a bug')
    
@home_bp.route('/view/<paperid>', methods=['GET'])
def view_results(paperid):
    if not _validate_paperid(paperid):
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
    json_file = paper_path / Path('meta.json')
    meta = json.loads(json_file.read_text(encoding='UTF-8'))
    meta['title'] = 'Results from compilation'
    pdf_file = output_path / Path('main.pdf')
    if pdf_file.is_file():
        meta['pdf'] = True
    return render_template('view.html', **meta)
