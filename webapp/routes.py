import datetime
import json
from flask import Blueprint, render_template, request, jsonify
from flask import current_app as app
from celery.result import AsyncResult
from pathlib import Path
import zipfile

from webapp.tasks import run_latex_task, celery_app

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

def _validate_post(args, files):
    """args should contain paperid and email. files should contain zipfile."""
    if 'paperid' not in args:
        return 'Missing paperid'
    if 'email' not in args:
        return 'Missing author email'
    if 'zipfile' not in files:
        return 'Missing zip file'
    return None

@home_bp.route('/', methods=['POST'])
def runlatex():
    args = request.form.to_dict()
    msg = _validate_post(args, request.files)
    if msg:
        return render_template('message.html',
                               title='Invalid parameters',
                               error=msg)
    paperid = args.get('paperid')
    # TODO: make sure that paper id is safe to use as a path, so
    # we need to either base64 encode it or remove things like ../../../
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    if paper_dir.is_dir():
        # Empty the directory, removing previous attempt
        for entry in paper_dir.iterdir():
            entry.unlink()
    else:
        paper_dir.mkdir(parents=True)
    # Save a json file with minimal metadata for debugging.
    json_data = {'email': args.get('email'),
                 'paperid': paperid,
                 'ip_address': request.remote_addr,
                 'date': str(datetime.datetime.now())}
    json_file = paper_dir / Path('meta.json')
    json_file.write_text(json.dumps(json_data, indent=2))
    # Now unzip the zip file into paper_dir
    zip_path = paper_dir / Path('all.zip')
    request.files['zipfile'].save(zip_path)
    zip_file = zipfile.ZipFile(zip_path)
    input_dir = paper_dir / Path('input')
    zip_file.extractall(input_dir)
    output_dir = paper_dir / Path('output')
    if output_dir.is_dir():
        for entry in output_dir.iterdir():
            entry.unlink()
    else:
        output_dir.mkdir()
    # fire off a celery task
    taskid = run_latex_task.delay(str(input_dir.absolute()), str(output_dir.absolute()))
    print(taskid)
    return render_template('running.html',
                           title='Compiling your LaTeX',
                           taskid=taskid.id)

@home_bp.route('/tasks/<task_id>', methods=['GET'])
def get_status(task_id):
    task_result = celery_app.AsyncResult(task_id)
    result = {'task_id': task_id,
              'status': task_result.status,
              'result': task_result.result}
    return jsonify(result), 200
