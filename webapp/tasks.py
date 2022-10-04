"""This defines the celery tasks that will be run by the worker.
"""
from celery import Celery
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
def run_latex_task(input_path, output_path):
    try:
        return runner.run_latex(input_path, output_path)
    except Exception as e:
        return 'Exception running latex: ' + str(e)

