import json
from lxml import etree
import os
from pathlib import Path
import pymysql
import pytest
import re
import shutil
import sys
import tempfile
from urllib.parse import urlencode
from flask import g, request
import xml.etree.ElementTree as ET

sys.path.insert(0, '../../')
from webapp import create_app
from webapp.config import TestConfig
from webapp import create_hmac
from webapp.metadata.compilation import PubType
from webapp.metadata.db_models import Version

@pytest.fixture(scope='module')
def temp_dir(request):
    temp_dir = tempfile.mkdtemp()
    data_dir = os.path.join(temp_dir, 'data')

    def teardown():
        shutil.rmtree(temp_dir)
    request.addfinalizer(teardown)
    return temp_dir

@pytest.fixture(scope='module')
def test_client(temp_dir):
    TestConfig.DATA_DIR = temp_dir / Path('data')
    TestConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///{}/db.sqlite'.format(temp_dir)

    app = create_app(TestConfig)
    with app.test_client() as test_client:
        with app.app_context():
            yield test_client

# Very basic test to make sure the home page works.
def test_home_page(test_client):
    response = test_client.get('/')
    assert response.status_code == 200
    assert b"IACR Communications in Cryptology" in response.data

# Check for SubmitForm to be populated when following a link
# from hotcrp.
def test_submit_form(test_client):
    args = {'paperid': 'testid',
            'hotcrp': 'cictest',
            'hotcrp_id': '5',
            'version': Version.CANDIDATE.value,
            'submitted': '2024-02-29 14:22:05',
            'accepted': '2024-01-02 08:05:59',
            'journal': 'cic',
            'volume': '5',
            'issue': '3',
            'pubtype': PubType.ERRATA.value}
    key = TestConfig.HOTCRP_POST_KEY.encode('utf-8')
    args['auth'] = create_hmac([args['paperid'],
                                args['hotcrp'],
                                args['hotcrp_id'],
                                args['version'],
                                args['submitted'],
                                args['accepted'],
                                args['journal'],
                                args['volume'],
                                args['issue'],
                                args['pubtype']],
                               key=key)
    args['errata_doi'] = '10.1729/feebar'
    url = '/submit?' + urlencode(args)
    response = test_client.get(url)
    assert response.status_code == 200
    resp = response.data.decode('utf-8')
    start = resp.find('<form')
    end = resp.find('</form')
    assert start > 0
    assert end > 0
    resp = resp[start:end]
    print(resp)
    assert '<input class="form-control w-50" id="paperid" name="paperid" pattern="[-a-zA-Z0-9]{7,}" placeholder="paper ID" required type="hidden" value="testid">' in resp
    assert '<input id="hotcrp" name="hotcrp" required type="hidden" value="cictest">' in resp
    assert '<input id="hotcrp_id" name="hotcrp_id" required type="hidden" value="5">' in resp
    assert '<input id="auth" name="auth" required type="hidden" value="53453dafa6da953c0c3859bb57f2c1473632594b9c8bc20cece9f339c9bd7d16">' in resp
    assert '<input id="version" name="version" required type="hidden" value="candidate">' in resp
    assert '<input id="submitted" name="submitted" required type="hidden" value="2024-02-29 14:22:05">' in resp
    assert '<input id="accepted" name="accepted" required type="hidden" value="2024-01-02 08:05:59">' in resp
    assert '<input id="volume" name="volume" required type="hidden" value="5">' in resp
    assert '<input id="pubtype" name="pubtype" required type="hidden" value="ERRATA">' in resp
    assert '<input id="errata_doi" name="errata_doi" type="hidden" value="10.1729/feebar">' in resp
    assert '<input id="issue" name="issue" required type="hidden" value="3">' in resp

        
