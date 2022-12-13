from typing import Any, Optional
import uuid

from okolab import OkolabDevice, OkolabDeviceDisconnectedError
from pr1.units.base import BaseExecutor
from pr1.util import schema as sc
from pr1.util.parser import Identifier

from . import logger


conf_schema = sc.Schema({
  'address': str,
  'type': sc.ParseType(int)
})

class Executor(BaseExecutor):
  def __init__(self, conf, *, host):
    self._conf: Any = conf_schema.transform(conf)
    self._device: Optional[OkolabDevice] = None
    self._host = host

  async def get_device(self):
    if not self._device:
      try:
        self._device = OkolabDevice(address=self._conf['address'])
        await self._device.set_device1(None)
      except OkolabDeviceDisconnectedError:
        logger.error("Disconnected device")

    return self._device

  async def initialize(self):
    await self.get_device()
