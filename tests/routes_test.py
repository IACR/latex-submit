"""Test for individual web transactions."""

from webapp.metadata.db_models import Version, PubType
from webapp import create_hmac
from urllib.parse import urlencode
from bs4 import BeautifulSoup

def test_home_page(client):
    """Check that home page can be fetched without authentication."""
    response = client.get('/')
    assert response.status_code == 200

def test_about(client):
    """Check that 'about' page can be fetched without authentication."""
    response = client.get('/about')
    assert response.status_code == 200

# Check for SubmitForm to be populated when following a link
# from hotcrp.
def test_submit_form(app, client):
    args = {'paperid': 'testid',
            'hotcrp': 'cictest',
            'hotcrp_id': '5',
            'version': Version.CANDIDATE.value,
            'submitted': '2024-02-29 14:22:05',
            'accepted': '2024-01-02 08:05:59',
            'revised': '2025-03-02 00:02:34',
            'journal': 'cic',
            'volume': '5',
            'issue': '3',
            'pubtype': PubType.ERRATA.value}
    key = app.config['HOTCRP_POST_KEY'].encode('utf-8')
    args['auth'] = create_hmac([args['paperid'],
                                args['hotcrp'],
                                args['hotcrp_id'],
                                args['version'],
                                args['submitted'],
                                args['accepted'],
                                args['revised'],
                                args['journal'],
                                args['volume'],
                                args['issue'],
                                args['pubtype']],
                               key=key)
    args['errata_doi'] = '10.1729/feebar'
    url = '/submit?' + urlencode(args)
    response = client.get(url)
    assert response.status_code == 200
    resp = response.data.decode('utf-8')
    start = resp.find('<form')
    end = resp.find('</form')
    assert start > 0
    assert end > 0
    print(resp[start:end])
    soup = BeautifulSoup(resp, features='lxml')
    paperid_input = soup.body.find('input', id='paperid')
    assert paperid_input.attrs.get('value') == 'testid'
    hotcrp_input = soup.body.find('input', id='hotcrp')
    assert hotcrp_input.attrs.get('value') == 'cictest'
    hotcrp_input = soup.body.find('input', id='hotcrp_id')
    assert hotcrp_input.attrs.get('value') == '5'
    auth_input = soup.body.find('input', id='auth')
    assert auth_input.attrs.get('value') == args['auth']
    version_input = soup.body.find('input', id='version')
    assert version_input.attrs.get('value') == 'candidate'
    submitted_input = soup.body.find('input', id='submitted')
    assert submitted_input.attrs.get('value') == '2024-02-29 14:22:05'
    accepted_input = soup.body.find('input', id='accepted')
    assert accepted_input.attrs.get('value') == '2024-01-02 08:05:59'
    revised_input = soup.body.find('input', id='revised')
    assert revised_input.attrs.get('value') == '2025-03-02 00:02:34'
    volume_input = soup.body.find('input', id='volume')
    assert volume_input.attrs.get('value') == '5'
    issue_input = soup.body.find('input', id='issue')
    assert issue_input.attrs.get('value') == '3'
    pubtype_input = soup.body.find('input', id='pubtype')
    assert pubtype_input.attrs.get('value') == 'ERRATA'
    doi_input = soup.body.find('input', id='errata_doi')
    assert doi_input.attrs.get('value') == '10.1729/feebar'
