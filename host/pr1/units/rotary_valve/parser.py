from . import namespace
from ..base import BaseParser
from ...util import schema as sc


class Parser(BaseParser):
  def __init__(self, parent):
    self._parent = parent
    print(parent)

  def parse_block(self, data_block):
    if 'rotate_valve' in data_block:
      return { 'role': 'process' }

  def handle_segment(self, data_segment):
    if 'rotate_valve' in data_segment:
      valve, _ = data_segment['rotate_valve']
      valve = sc.ParseType(int).transform(valve)

      return {
        namespace: { 'valve': valve }
      }

  def export_segment(data):
    return {
      "valve": data['valve']
    }
