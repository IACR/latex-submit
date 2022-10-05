"""This defines the celery tasks that will be run by the worker.
"""
from celery import Celery
import json
import os
from pathlib import Path
import time
from .compiler import runner

# TODO: how should we store this password?
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD',
                                'go35HyTzf0rnowpl3ase')
celery_app = Celery(__name__)
celery_app.conf.broker_url = os.environ.get("CELERY_BROKER_URL",
                                        f'redis://:{REDIS_PASSWORD}@localhost:6379/0')                                                                     
celery_app.conf.result_backend = f'redis://:{REDIS_PASSWORD}@localhost:6379/0'
celery_app.set_current()

@celery_app.task(name="run_latex_task")
def run_latex_task(input_path, output_path, paperid):
    """Execute latex on input_path contents, writing into output_path.
    args:
       input_path: complete string path to input directory
       output_path: complete string path to output directory
       paperid: string paperid
    """
    try:
        start_time = time.time()
        output = runner.run_latex(input_path, output_path)
        end_time = time.time()
        json_file = Path(output_path).parents[0] / Path('meta.json')
        if json_file.is_file():
            jstr = json_file.read_text(encoding='UTF-8')
            data = json.loads(jstr)
            data['execution_time'] = end_time - start_time
            data['log'] = output['log']
            data['code'] = output['code']
            json_file.write_text(json.dumps(data, indent=2), encoding='UTF-8')
        else:
            output['error'] = 'Missing json file.'
        return json.dumps(output, indent=2)
    except Exception as e:
        return 'Exception running latex: ' + str(e)

