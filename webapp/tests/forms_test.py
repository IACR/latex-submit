import copy
import pytest
import sys
from flask import Flask
from werkzeug.datastructures import MultiDict, FileStorage

sys.path.insert(0, '../../')
from webapp.metadata.compilation import PubType
from webapp.config import TestConfig

def get_form_data():
    _form_data = {'paperid': 'testing',
                  'journal': 'cic',
                  'volume': '5',
                  'issue': '2',
                  'version': 'candidate',
                  'hotcrp': 'cictest3',
                  'hotcrp_id': 'cictest3_2',
                  'submitted': '2024-02-07 23:05:22',
                  'accepted': '2024-03-05 10:22:55',
                  'pubtype': 'RESEARCH',
                  'auth': 'foobar',
                  'email': 'testing@example.com'
                  }
    data = copy.deepcopy(_form_data)
    data['zipfile'] = FileStorage(name='zipfile',
                                  filename='test.zip',
                                  content_type='application/x-zip'),
    return data

def test_form():
    app = Flask(__name__)
    app.config.from_object(TestConfig)
    ctx = app.app_context()
    ctx.push()
    from webapp.forms import SubmitForm
    with ctx:
        data = get_form_data()
        form = SubmitForm(formdata=MultiDict(data))
        form.generate_auth()
        assert form.validate()

        data = get_form_data()
        form = SubmitForm(formdata=MultiDict(data))
        form.generate_auth()
        form.auth.data = form.auth.data[:10]
        assert not form.validate()

        data = get_form_data()
        data['pubtype'] = 'UNKNOWN'
        form = SubmitForm(formdata=MultiDict(data))
        form.generate_auth()
        assert not form.validate()

        data = get_form_data()
        data['submitted'] = '2024-02-07'
        form = SubmitForm(formdata=MultiDict(data))
        form.generate_auth()
        assert not form.validate()

        data = get_form_data()
        data['version'] = 'FINAL'
        form = SubmitForm(formdata=MultiDict(data))
        form.generate_auth()
        assert not form.validate()

