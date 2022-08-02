import asyncio

from ..base import BaseRunner


class Runner(BaseRunner):
  def get_state(self):
    return dict()

  async def run_process(self, segment, seg_index, state):
    await asyncio.Future()

  def export_state(self, state):
    return { "progress": 0 }
