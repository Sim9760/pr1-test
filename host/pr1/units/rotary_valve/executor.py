import asyncio
from serial import Serial
import time

from . import namespace
from ..base import BaseExecutor
from ...util import schema as sc


schema = sc.Schema({
  # 'address': sc.Optional(sc.Use(lambda x: ('0' <= x <= '9') or ('A' <= x <= 'F'), "Invalid address")), # To be fixed
  'address': sc.Optional(str),
  'fast': sc.Optional(sc.Transform(bool, str)),
  'port': str,
  'valve_count': sc.Optional(sc.Transform(int, sc.Or('4', '6', '8', '10', '12')))
})

class Executor(BaseExecutor):
  def __init__(self, conf, *, host):
    self._conf = schema.transform(conf)
    self._host = host

    self._driver = Driver(self._conf)

  async def initialize(self):
    await self._driver.initialize()


class Driver:
  def __init__(self, conf):
    self._conf = conf
    self._serial = None

    self._query_active = False
    self._query_data = None

  @property
  def _channel(self):
    return self._conf.get('address', '1')

  async def initialize(self):
    self._serial = Serial(self._conf['port'], timeout=0.05)

    # await self.home()

  async def get_unique_id(self):
    self._send("?9000")
    return self._process(await self._accept(query=True))

  async def home(self):
    self._send("ZR")

    await self._accept(query=True)
    await self._accept(query=False)

  async def rotate(self, valve):
    self._send(f"b{valve}R")
    await self._accept(query=True)
    await self._accept(query=False)

  def _process(self, data, dtype = None):
    payload = data[2:-3]
    busy = (payload[0] & (1 << 5)) < 1
    response = payload[1:].decode("utf-8")

    if dtype is not None:
      if dtype == bool:
        result = (response == "1")
      if dtype == int:
        result = int(response)
    else:
      result = response

    return result

  def _send(self, command):
    print(f"Command: /{self._channel}{command}")
    self._serial.write(f"/{self._channel}{command}\r".encode("utf-8"))

  async def _accept(self, *, query):
    def func():
      while True:
        if query and self._query_data:
          return self._query_data

        data = self._serial.readline()

        if data:
          if (not query) and self._query_active:
            self._query_data = data

          return data

    self._query_active = query

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, func)

    if query:
      self._query_active = False

    return data


if __name__ == "__main__":
  ex = Executor({
    'port': '/dev/tty.usbserial-P201_O00001273'
  }, host=None)

  async def main():
    await ex.initialize()

    await ex._driver.rotate(4)
    await ex._driver.rotate(5)

  asyncio.run(main())
