from webapp import create_app
from config import DebugConfig

config = DebugConfig()
app = create_app(config)
app.run(host='0.0.0.0')
