import logging

logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s :: %(name)-18s :: %(message)s")

# for handler in logging.root.handlers:
#   handler.addFilter(logging.Filter("pr1"))

import time

if time.time() > 1661271061 + 3600 * 24 * 30:
  import sys
  sys.exit(1)


from . import main

main()
