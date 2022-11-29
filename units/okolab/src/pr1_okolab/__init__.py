from importlib.resources import files
from pathlib import Path

from pr1.units.base import Metadata, MetadataIcon, logger as parent_logger


namespace = "okolab"
version = 0

metadata = Metadata(
  description="Okolab",
  icon=MetadataIcon(kind='icon', value="description"),
  title="Okolab",
  version="1.0"
)

client_path = files(__name__ + '.client')
logger = parent_logger.getChild(namespace)

from .executor import Executor
from .parser import Parser
from .runner import Runner
