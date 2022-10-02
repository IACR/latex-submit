"""This defines the celery tasks that will be run by the worker.
"""
from celery import Celery
import os
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
print(celery_app.backend)

@celery_app.task(name="run_latex_task")
def run_latex_task(arg1):
    try:
        # TODO: arg1 should provide the ID for where the tex zip file has been unzipped.
        return runner.run_latex('webapp/compiler/tests/passing', '/tmp/passing.tar')
    except Exception as e:
        return 'Exception running latex: ' + str(e)
    # TODO: figure out what to return here.
    return arg1 + ' is finished. Output is in /tmp/passing.tar'

