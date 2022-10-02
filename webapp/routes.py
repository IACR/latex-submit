from flask import Blueprint, render_template, request, jsonify
from flask import current_app as app

from webapp.tasks import run_latex_task, celery_app
from celery.result import AsyncResult

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

def _validate_post(args):
    """args should contain paperid and zipfile."""
    return None

@home_bp.route('/', methods=['POST'])
def runlatex():
    args = request.form.to_dict()
    msg = _validate_post(args)
    if msg:
        return render_template('message.html',
                               title='Invalid parameters',
                               error=msg)
    # fire off a celery task
    taskid = run_latex_task.delay(args.get('paperid'))
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
