import asyncio
import time

from . import namespace
from ..base import BaseProcessRunner


class Runner(BaseProcessRunner):
  def __init__(self, chip, *, host):
    self._chip = chip
    self._executor = host.executors[namespace]

  def get_state(self):
    return dict()

  async def run_process(self, segment, seg_index, state):
    await self._executor._driver.rotate(segment[namespace]['valve'])

  def export_state(self, state):
    return { "progress": 0 }

  def command(self, command):
    loop = asyncio.get_event_loop()
    loop.create_task(self._executor.rotate(command['valve']))
