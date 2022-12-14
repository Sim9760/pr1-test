from . import namespace
from ..base import BaseParser


class Parser(BaseParser):
  def __init__(self, master):
    self._master = master

  def parse_block(self, data_block):
    if 'confirm' in data_block:
      return {
        'role': 'process'
      }

  def handle_segment(self, data_action):
    if 'confirm' in data_action:
      message, _context = data_action['confirm']

      return {
        namespace: {
          'message': message
        }
      }

  def export_segment(data):
    return {
      "message": data['message']
    }
