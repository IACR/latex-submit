"""
This is used to manage the submission of final papers. Authors enter the site via
an authenticated URL with a paper ID from hotcrp. When a paper is submitted, it
receives an upload of a zip file with at least one tex file. We start a docker instance
in a separate task to compile the output.
"""

from collections import OrderedDict
from flask import Flask, request, render_template, current_app
from flask_mail import Mail
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import os
import sys

# Make sure we aren't running on an old python.
assert sys.version_info >= (3, 7)

class StrEnum(str, Enum):
    @classmethod
    def from_str(cls, val):
        """Convert string to enum value."""
        for e in cls:
            if e.value == val:
                return e
        return None

class TaskStatus(StrEnum):
    """Status of a paper."""
    PENDING = 'PENDING'
    CANCELLED = 'CANCELLED'
    RUNNING = 'RUNNING'
    FAILED_EXCEPTION = 'FAILED_EXCEPTION'
    FAILED_COMPILE = 'FAILED_COMPILE'
    COMPILED = 'COMPILED'
    UNKNOWN = 'UNKNOWN'

# Globally accessible SMTP client. This can be used in unit tests as well.
mail = Mail()

# Used to keep track of compilations by paperid. When a task is
# submitted, then the paperid key is added to this with a value of the Future
# that will run the compilation.. When a task is finished it removes the paperid
# from the task_queue. This allows us to keep track of which
# papers are queued for processing so that we don't enqueue a paper
# twice and monitor the status of the queue in the admin interface.
task_queue = OrderedDict()

executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='compiler')
#executor.add_default_done_callback(_default_future_callback)

def create_app(config):
    app = Flask('webapp', static_folder='static/', static_url_path='/')
    app.config.from_object(config)

    mail.init_app(app)
    #executor.init_app(app)
    with app.app_context():
        from . import admin
        from . import routes
        app.register_blueprint(routes.home_bp)
        app.register_blueprint(admin.admin_bp)
        return app


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
