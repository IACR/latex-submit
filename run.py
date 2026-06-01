from pathlib import Path
from webapp import create_app
from webapp import config
config_file = Path('webapp/debug_config.json')
if config_file.is_file():
    conf = config.Config.model_validate_json(config_file.read_text(encoding='UTF-8'))
else: # in case the secrets are in the default file.
    conf = config.Config()
app = create_app(conf)
app.run(host='0.0.0.0', debug=True, use_reloader=True, exclude_patterns=['final.zip', 'all.zip', 'tmp.zip', '*.tex', 'latex.zip'])
