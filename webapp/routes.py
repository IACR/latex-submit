from flask import Blueprint, render_template, request, jsonify
from flask import current_app as app

from webapp.tasks import run_latex_task, celery_app
from celery.result import AsyncResult
from pathlib import Path
import zipfile

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
    paper_dir = Path(app.config['DATA_DIR']) / Path(paperid)
    if paper_dir.is_dir():
        # Empty the directory, removing previous attempt
        for entry in paper_dir.iterdir():
            entry.unlink()
    else:
        paper_dir.mkdir(parents=True)
    # Now unzip the zip file into paper_dir
    zip_path = paper_dir / Path('all.zip')
    request.files['zipfile'].save(zip_path)
    zip_file = zipfile.ZipFile(zip_path)
    zip_file.extractall(paper_dir)
    # We don't keep the zip_file since we have unzipped it.
    zip_path.unlink()
    # fire off a celery task
    taskid = run_latex_task.delay(paperid)
    return render_template('running.html',
                           title='Compiling your LaTeX',
                           taskid=taskid.id)

@home_bp.route('/tasks/<task_id>', methods=['GET'])
def get_status(task_id):
    print(celery_app.tasks.keys())
    task_result = celery_app.AsyncResult(task_id)
    result = {'task_id': task_id,
              'status': task_result.status,
              'result': task_result.result}
    return jsonify(result), 200
