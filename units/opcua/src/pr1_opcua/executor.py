import asyncio
import logging

from asyncua import Client, ua
from pr1.device import BooleanNode
from pr1.units.base import BaseExecutor
from pr1.util import schema as sc
from pr1.util.parser import Identifier

from . import logger, namespace


logging.getLogger("asyncua.client.client").setLevel(logging.WARNING)

variants_map = {
  'bool': ua.VariantType.Boolean,
  'i16': ua.VariantType.Int16,
  'i32': ua.VariantType.Int32,
  'i64': ua.VariantType.Int64,
  'u16': ua.VariantType.UInt16,
  'u32': ua.VariantType.UInt32,
  'u64': ua.VariantType.UInt64,
  'f32': ua.VariantType.Float,
  'f64': ua.VariantType.Double
}

conf_schema = sc.Schema({
  'devices': sc.Optional(sc.List({
    'address': str,
    'label': sc.Optional(str),
    'id': Identifier(),
    'nodes': sc.Noneable(sc.List({
      'id': str,
      'label': sc.Optional(str),
      'location': str,
      'type': sc.Or(*variants_map.keys())
    }))
  }))
})


class DeviceNode(BooleanNode):
  def __init__(self, *, id, label, node, type):
    self.id = id
    self.label = label
    self.type = type

    self.target_value = None
    self.value = None

    self.connected = False
    self.unwritable = False

    self._node = node
    self._variant = variants_map[type]

  @property
  def value_type(self):
    match self.type:
      case 'bool': return "boolean"
      case _: return "scalar"

  async def _connect(self):
    try:
      self.value = await self._node.get_value()
    except ua.uaerrors._auto.BadNodeIdUnknown:
      logger.error(f"Missing node '{self._node.nodeid}'")
    else:
      self.connected = True

      if self.target_value is None:
        self.target_value = self.value

      if self.target_value != self.value:
        await self.write(self.target_value)

  async def write(self, value):
    self.target_value = value

    if self.connected:
      match self.type:
        case 'i16' | 'i32' | 'i64' | 'u16' | 'u32' | 'u64': value = int(value)
        case 'f32' | 'f64': value = float(value)

      await self._node.write_value(ua.DataValue(ua.Variant(value, self._variant)))
      self.value = value


class Device:
  model = "Generic OPC-UA device"
  owner = namespace

  def __init__(self, id, *, label, address, nodes_conf, update_callback):
    self.connected = False
    self.id = id
    self.label = label

    self._address = address
    self._client = Client(address)
    self._update_callback = update_callback

    self._check_task = None
    self._reconnect_task = None

    self._node_ids = { node['id']: node_index for node_index, node in enumerate(nodes_conf) }
    self.nodes = [
      DeviceNode(
        id=node_conf['id'].value,
        label=node_conf.get('label'),
        node=self._client.get_node(node_conf['location'].value),
        type=node_conf['type']
      ) for node_conf in nodes_conf
    ]


  async def initialize(self):
    await self._connect()

    if not self.connected:
      logger.error(f"Failed connecting to '{self._address}'")
      self._reconnect()

  async def destroy(self):
    if self.connected:
      await self._client.disconnect()

    if self._check_task:
      self._check_task.cancel()

    if self._reconnect_task:
      self._reconnect_task.cancel()

  def get_node(self, id):
    node_index = self._node_ids.get(id)

    if node_index is None:
      return None

    return self.nodes[node_index]


  async def _connect(self):
    logger.debug(f"Connecting to '{self._address}'")

    try:
      await self._client.connect()
    # An OSError will occur if the computer is not connected to a network.
    except (ConnectionRefusedError, OSError, asyncio.TimeoutError):
      return

    logger.info(f"Connected to '{self._address}'")
    self.connected = True

    for node in self.nodes:
      await node._connect()

    server_state_node = self._client.get_node("ns=0;i=2259")

    async def check_loop():
      try:
        while True:
          await server_state_node.get_value()
          await asyncio.sleep(1)
      except (ConnectionError, asyncio.TimeoutError):
        logger.error(f"Lost connection to '{self._address}'")

        self.connected = False

        for node in self.nodes:
          node.connected = False

        self._reconnect()
        self._update_callback()
      except asyncio.CancelledError:
        pass
      finally:
        self._check_task = None

    self._check_task = asyncio.create_task(check_loop())


  def _reconnect(self, interval = 1):
    async def reconnect():
      try:
        while True:
          await self._connect()

          if self.connected:
            self._update_callback()
            return

          await asyncio.sleep(interval)
      except asyncio.CancelledError:
        pass
      finally:
        self._reconnect_task = None

    self._reconnect_task = asyncio.create_task(reconnect())


class Executor(BaseExecutor):
  def __init__(self, conf, *, host):
    conf = conf_schema.transform(conf)

    self._devices = dict()
    self._host = host

    for device_conf in conf.get('devices', list()):
      device_id = device_conf['id'].value

      if device_id in self._host.devices:
        raise device_id.error(f"Duplicate device id '{device_id}'")

      device = Device(
        address=device_conf['address'],
        id=device_id,
        label=device_conf.get('label'),
        nodes_conf=device_conf['nodes'],
        update_callback=self._host.update_callback
      )

      self._devices[device_id] = device
      self._host.devices[device_id] = device

  async def initialize(self):
    for device in self._devices.values():
      await device.initialize()

  async def destroy(self):
    for device in self._devices.values():
      await device.destroy()
      del self._host.devices[device.id]
