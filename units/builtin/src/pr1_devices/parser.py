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

    self._properties = dict()

    for device in self._parent.host.devices.values():
      for node in device.nodes:
        self._properties[f"{device.id}.{node.id}"] = (device, node)

  def handle_segment(self, data_segment):
    assignments = list()

    for property, (device, node) in self._properties.items():
      if property in data_segment:
        value = sc.ParseType({ "boolean": bool, "scalar": float }[node.value_type]).transform(data_segment[property][0])

        assignments.append((device.id, node.id, value))

    return { namespace: { 'assignments': assignments } }

  @staticmethod
  def export_segment(data: Any):
    return {
      "assignments": data['assignments']
    }
