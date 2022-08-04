import logging

logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s :: %(name)-18s :: %(message)s")

# for handler in logging.root.handlers:
#   handler.addFilter(logging.Filter("pr1"))

import time

if time.time() > 1659515956 + 3600 * 24 * 4:
  import sys
  sys.exit(1)


from . import main

main()
