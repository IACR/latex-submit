# NOTE: this doesn't work yet.

import sys
sys.path.insert(0, '/var/www/submit')

from config import DebugConfig
from webapp import create_app

config = DebugConfig()
application = create_app(config)
