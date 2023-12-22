# NOTE: this doesn't work yet.

import sys
sys.path.insert(0, '/var/www/wsgi/latex-submit/search')

from searchapp import config
from searchapp import create_app

config = config.ProdConfig()
application = create_app(config)
