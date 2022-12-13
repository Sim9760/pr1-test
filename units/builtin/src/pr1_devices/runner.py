import asyncio
import traceback
from typing import Optional

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
    if namespace in segment:
      async def run():
        try:
          host = self._executor._host

          for device_id, node_id, value in segment[namespace]['assignments']:
            try:
              device = host.devices[device_id]
              node = next(node for node in device.nodes if node.id == node_id)
              await node.write(value)
            except Exception:
              traceback.print_exc()
        except Exception:
          traceback.print_exc()

      asyncio.create_task(run())

  def import_state(self, data_state):
    return dict()

  def serialize(self):
    return self._version,

  def unserialize(self, state):
    version, = state

    if version != self._version:
      raise UnsupportedChipRunnerError()
