from webapp import create_app
from webapp import config

conf = config.DebugConfig()
app = create_app(conf)
app.run(host='0.0.0.0', exclude_patterns=['final.zip', 'all.zip', 'tmp.zip', '*.tex'])
