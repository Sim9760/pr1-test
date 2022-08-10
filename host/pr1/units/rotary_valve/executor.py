import asyncio
import time
from threading import Thread
import uuid

from serial import Serial

from ...util import schema as sc
from ..base import BaseExecutor
from . import namespace


schema = sc.Schema({
  # 'address': sc.Optional(sc.Use(lambda x: ('0' <= x <= '9') or ('A' <= x <= 'F'), "Invalid address")), # To be fixed
  # 'address': sc.Optional(str),
  # 'fast': sc.Optional(sc.Transform(bool, str)),
  'port': sc.Optional(str)
})

class Executor(BaseExecutor):
  def __init__(self, conf, *, host):
    self._conf = schema.transform(conf)
    self._host = host

    self._driver = Driver(address=self._conf['port']) if 'port' in self._conf else MockDriver()

  async def initialize(self):
    await self._driver.initialize()

  async def destroy(self):
    await self._driver.destroy()

  async def rotate(self, valve):
    await self._driver.rotate(valve)
    self._host.update_callback()

  def export(self):
    return {
      "valve": self._driver.valve,
      "valveCount": self._driver.valve_count
    }


class MockDriver:
  def __init__(self):
    self._valve = 1

  @property
  def valve(self):
    return self._valve

  @property
  def valve_count(self):
    return 12

  async def initialize(self):
    await self.home()

  async def destroy(self):
    pass

  async def rotate(self, valve):
    await asyncio.sleep(1)
    self._valve = valve

  async def get_unique_id(self):
    return str(uuid.uuid4()).upper()

  async def get_valve(self):
    return self._valve

  async def get_valve_count(self):
    return 12

  async def home(self):
    await asyncio.sleep(0.3)


class Driver:
  def __init__(self, *, address, channel = "_"):
    self._address = address
    self._channel = channel

    self._busy = False
    self._shutdown = False
    self._serial = None

    self._valve = None
    self._valve_count = None

    self._query_future = None
    self._task_future = None

    loop = asyncio.get_event_loop()

    def thread():
      while not self._shutdown:
        if self._query_future or self._task_future:
          data = self._serial.readline()

          if data:
            was_busy = self._busy
            is_busy = self._is_busy(data)

            if self._task_future and was_busy and (not is_busy):
              loop.call_soon_threadsafe(self._task_future.set_result, data)
              self._task_future = None
            else:
              loop.call_soon_threadsafe(self._query_future.set_result, data)
              self._query_future = None

    self._thread = Thread(target=thread)

  @property
  def valve(self):
    return self._valve

  @property
  def valve_count(self):
    return self._valve_count

  async def initialize(self):
    self._serial = Serial(self._address, timeout=0.05)
    self._thread.start()

    await self._query("!502")
    await self.home()

    self._valve = await self.get_valve()
    self._valve_count = await self.get_valve_count()

  async def destroy(self):
    self._shutdown = True
    self._thread.join()


  async def execute(self, sequence):
    done = False
    # prev_rotation_count = 0

    # available = 0
    # future = None

    # class Iterator:
    #   async def __anext__(self):
    #     nonlocal future

    #     if available > 0:
    #       available -= 1
    #     else:
    #       future = asyncio.Future()
    #       await future
    #       future = None

    async def observe():
      while not done:
        await asyncio.sleep(0.1)
        rotation_count = await self._query("?17", dtype=int)
        print(rotation_count)

    async def run():
      nonlocal done

      await self._run("".join([f"b{value}" if (index % 2) < 1 else f"M{value}" for index, value in enumerate(sequence)]) + "R")
      done = True

    await asyncio.gather(observe(), run())

  async def get_unique_id(self):
    return await self._query("?9000")

  async def get_valve(self):
    return await self._query("?6", dtype=int)

  async def get_valve_count(self):
    return await self._query("?801", dtype=int)

  async def home(self):
    await self._run("ZR")

  async def rotate(self, valve):
    await self._run(f"b{valve}R")
    self._valve = await self.get_valve()


  async def _query(self, command, *, dtype = None):
    while self._query_future:
      await self._query_future

    self._send(command)
    self._query_future = asyncio.Future()
    return self._process(await self._query_future, dtype=dtype)

  def _is_busy(self, data):
    return (data[2] & (1 << 5)) < 1

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

    self._busy = busy

    return result

  async def _run(self, command):
    while self._task_future:
      await self._task_future

    await self._query(command)

    self._task_future = asyncio.Future()
    self._process(await self._task_future)

  def _send(self, command):
    print(f"Command: /{self._channel}{command}")
    self._serial.write(f"/{self._channel}{command}\r".encode("utf-8"))


if __name__ == "__main__":
  ex = Executor({
    'port': '/dev/tty.usbserial-P201_O00001273'
  }, host=None)

  async def main():
    try:
      await ex.initialize()

      dr = ex._driver

      # print(await asyncio.gather(
      #   dr.get_unique_id(),
      #   dr.get_unique_id(),
      #   dr.get_unique_id()
      # ))

      # await dr.home()

      print("Over")
    except KeyboardInterrupt:
      pass
    finally:
      await ex.destroy()

  loop = asyncio.get_event_loop()
  loop.run_until_complete(main())
