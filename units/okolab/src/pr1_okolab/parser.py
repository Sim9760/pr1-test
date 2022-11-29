from typing import Any
from pr1.reader import LocatedValue
from pr1.units.base import BaseParser
from pr1.util import schema as sc
from pr1.util.parser import CompositeValue, Identifier, UnclassifiedExpr

from . import namespace


class Parser(BaseParser):
  def __init__(self, parent):
    self._executor = parent.host.executors[namespace]
    self._parent = parent

  def handle_segment(self, data_segment):
    if "temperature" in data_segment:
      raw_value = data_segment["temperature"][0]
      value = sc.ParseType(int).transform(raw_value)

      if not (25 <= value <= 60):
        raise raw_value.error(f"Invalid value")

      return { namespace: { 'value': value } }

    return None

  @staticmethod
  def export_segment(data: Any):
    return {
      "value": data['value']
    }
