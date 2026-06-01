"""Test for individual web transactions."""
from werkzeug.datastructures import MultiDict

def test_noauth(app, client, auth, admin_user):
    """Make sure that all admin rules require login."""
    conf = app.config
    with app.app_context():
        bp = app.blueprints['admin_file']
        assert len(app.blueprints) == 4
        rules = list(app.url_map.iter_rules())
        assert len(rules) == 62
        getrules = 0
        for rule in rules:
            rstr = str(rule)
            print(rstr, rule.methods)
            if rstr.startswith('/admin') and 'GET' in rule.methods:
                getrules += 1
                print(rstr)
                response = client.get(rstr)
                # all should redirect.
                assert response.status_code == 302
                assert response.location.startswith('{}/login'.format(conf['SECURITY_URL_PREFIX']))
        assert getrules == 14
                
def test_editor(client, auth, editor_user):
    """Test that login works for /admin/ for editor_user"""
    auth.login(editor_user)
    response = client.get('/admin/')
    assert response.status_code == 200
    assert 'User management' not in str(response.data)
    assert 'Copy editing</a>' in str(response.data)

def test_nobody(client, auth, nobody_user):
    """Test that login works for /admin/ for nobody_user"""
    auth.login(nobody_user)
    response = client.get('/admin/')
    assert response.status_code == 200
    assert 'User management' not in str(response.data)
    # there should be no link for copy editing since they do not have a role for it.
    assert 'Copy editing</a>' not in str(response.data)

def test_admin(client, auth, admin_user):
    """Test that login works for /admin/."""
    response = client.get('/admin/')
    assert response.status_code == 302
    assert response.location == '/sec/login?next=/admin/'
    auth.login(admin_user)
    response = client.get('/admin/')
    assert response.status_code == 200
    assert 'Upload Admin Home' in str(response.data)
    assert 'User management' in str(response.data)
    assert 'Copy editing</a>' in str(response.data)
    response = client.get('/')
    assert response.status_code == 200
    assert 'Call for Papers' in str(response.data)
    auth.logout()
    response = client.get('/admin/')
    assert response.status_code == 302
    assert response.location == '/sec/login?next=/admin/'

def test_view_journal(debug_data, client, auth, admin_user):
    url = f"/admin/view_journal/1"
    auth.login(admin_user)
    response = client.get(url)
    assert response.status_code == 200
    assert 'IACR Communications in Cryptology</h1>' in str(response.data)
    assert 'Recently modified papers' in str(response.data)

def test_create_user(client, auth, admin_user):
    """Create a user and set their roles."""
    newuser = MultiDict([('email', 'newuser@digicrime.com'),
                         ('name', 'Nigel New'),
                         ('password', 'JunkJank')])
    newuser.add('roles', ['editor_cic','copyeditor_tosc'])
    auth.login(admin_user)
    response = client.get('/admin/allusers')
    assert response.status_code == 200
    assert 'Nigel New' not in str(response.data)
    response = client.post('/admin/user', data=newuser, follow_redirects=True)
    assert 'Nigel New' in str(response.data)
        

    
