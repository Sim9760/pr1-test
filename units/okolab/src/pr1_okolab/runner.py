import asyncio
import traceback

from okolab import OkolabDeviceDisconnectedError
from pr1.chip import UnsupportedChipRunnerError
from pr1.units.base import BaseRunner

from . import logger, namespace
from .executor import Executor


class Runner(BaseRunner):
  _version = 1

  def __init__(self, chip, *, host):
    self._chip = chip
    self._executor: Executor = host.executors[namespace]

  def enter_segment(self, segment, seg_index):
    async def run(value: float):
      try:
        device = await self._executor.get_device()

        if device:
          try:
            await device.set_temperature_setpoint1(value)
          except OkolabDeviceDisconnectedError:
            logger.error("Disconnected device")
      except Exception:
        traceback.print_exc()

    if namespace in segment:
      asyncio.create_task(run(segment[namespace]['value']))

  def import_state(self, data_state):
    return dict()

  def serialize(self):
    return self._version,

  def unserialize(self, state):
    version, = state

    if version != self._version:
      raise UnsupportedChipRunnerError()
