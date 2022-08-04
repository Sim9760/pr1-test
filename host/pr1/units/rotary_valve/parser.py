from . import namespace
from ..base import BaseParser
from ...util import schema as sc


class Parser(BaseParser):
  def __init__(self, parent):
    self._parent = parent

  def parse_block(self, data_block):
    if 'rotate_valve' in data_block:
      return { 'role': 'process' }

  def handle_segment(self, data_segment):
    if 'rotate_valve' in data_segment:
      raw_valve, _ = data_segment['rotate_valve']
      valve = sc.ParseType(int).transform(raw_valve)

      if not (1 <= valve <= 12):
        raise raw_valve.error("Invalid valve")

      return {
        namespace: { 'valve': valve }
      }

  def export_segment(data):
    return {
      "valve": data['valve']
    }
