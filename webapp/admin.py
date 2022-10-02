#NOTE: this isn't used yet, but we'll use it for admin blueprints

"""This has the views for the admin section under /admn. Everything is
protected with HTTP authentication in apache, but in development there is
no authentication."""

def admin_message(data):
    return app.jinja_env.get_template('admin/message.html').render(data)

admin_file = Blueprint('admin_file', __name__)

@admin_file.route('/admin')
def show_admin_home():
    return render_template('admin/admin_home.html', TITLE='IACR CC Upload Admin Home')
    
