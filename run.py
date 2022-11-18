from webapp import create_app
from webapp import conf

config = conf.DebugConfig()
app = create_app(config)
app.run(host='0.0.0.0')
