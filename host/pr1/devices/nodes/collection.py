import asyncio
from typing import Awaitable, Callable
from .common import BaseNode, NodeId


class CollectionNode(BaseNode):
  def __init__(self):
    super().__init__()

    self.nodes: dict[NodeId, BaseNode]

  def export(self):
    return {
      **super().export(),
      "nodes": { node.id: node.export() for node in self.nodes.values() }
    }

  def iter_all(self):
    yield from super().iter_all()

    for node in self.nodes.values():
      yield from node.iter_all()

  def format(self, *, prefix: str = str()):
    output = super().format() + "\n"
    nodes = list(self.nodes.values())

    for index, node in enumerate(nodes):
      last = index == (len(nodes) - 1)
      output += prefix + ("└── " if last else "├── ") + node.format(prefix=(prefix + ("    " if last else "│   "))) + (str() if last else "\n")

    return output


class DeviceNode(CollectionNode):
  def __init__(self):
    super().__init__()
    self.owner: str

  def export(self):
    return {
      **super().export(),
      "owner": self.owner
    }
