from importlib.resources import files

from pr1.units.base import Metadata, MetadataIcon, logger as parent_logger


namespace = "devices"
version = 0

metadata = Metadata(
  description="This unit provides a list of devices.",
  icon=MetadataIcon(kind='icon', value="settings_input_hdmi"),
  title="Devices",
  version="1.1"
)

client_path = files(__name__ + '.client')
logger = parent_logger.getChild(namespace)

from .executor import Executor
from .parser import Parser
from .runner import Runner
