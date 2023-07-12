import asyncio
import time
from asyncio import Future
from dataclasses import dataclass
from typing import Literal, Optional

import automancer as am
from pr1.reader import LocatedValue, PossiblyLocatedValue
from quantops import Quantity

from . import logger


ProcessData = Quantity | Literal['forever']

@dataclass
class ProcessLocation:
  duration: Optional[float] # in seconds, None = wait forever
  progress: float
  time: Optional[float] = None

  def export(self):
    return {
      "date": (self.time * 1000) if (self.time is not None) else None,
      "duration": (self.duration * 1000) if (self.duration is not None) else None,
      "progress": self.progress
    }


@dataclass
class ProcessPoint(am.BaseProcessPoint):
  progress: float


class Process(am.BaseClassProcess[ProcessData, ProcessLocation, ProcessPoint]):
  name = "_"
  namespace = am.PluginName("timer")

  def duration(self, data: am.Evaluable[PossiblyLocatedValue[ProcessData]]):
    match data:
      case am.EvaluableConstantValue(LocatedValue('forever')):
        return am.DurationTerm.forever()
      case am.EvaluableConstantValue(LocatedValue(Quantity() as duration)):
        return am.DurationTerm((duration / am.ureg.second).magnitude)
      case _:
        return am.DurationTerm.unknown()

  def export_data(self, data: am.Evaluable[PossiblyLocatedValue[ProcessData]], /):
    return {
      "duration": data.export_inner(lambda value: (value / am.ureg.second).magnitude * 1000 if not isinstance(value, str) else None)
    }

  def import_point(self, raw_point, /):
    return ProcessPoint(progress=raw_point["progress"])

  async def __call__(self, context: am.ProcessContext[ProcessData, ProcessLocation, ProcessPoint]):
    total_duration = (context.data / am.ureg.sec).magnitude if not isinstance(context.data, str) else None

    context.pausable = True

    logger.debug("Starting")

    # Infinite duration
    if total_duration is None:
      context.send_term(am.DurationTerm.forever())
      context.send_location(ProcessLocation(duration=None, progress=0.0))

      while True:
        try:
          await context.wait(Future())
        except am.ProcessPauseRequest:
          await context.checkpoint()

    # Finite duration
    else:
      progress = context.point.progress if context.point else 0.0

      while True:
        start_time = time.time()
        remaining_duration = total_duration * (1.0 - progress)

        context.send_location(ProcessLocation(total_duration, progress, time=start_time))
        context.send_term(am.DatetimeTerm(start_time + remaining_duration))

        try:
          await context.wait(asyncio.sleep(remaining_duration))
        except am.ProcessJumpRequest as e:
          progress = context.cast(e).point.progress
        except am.ProcessPauseRequest:
          pause_time = time.time()
          progress += (pause_time - start_time) / total_duration

          context.send_term(am.DurationTerm(total_duration * (1.0 - progress)))
          context.send_location(ProcessLocation(total_duration, progress))

          while True:
            try:
              await context.checkpoint()
            except asyncio.CancelledError:
              context.send_location(ProcessLocation(total_duration, progress))
              raise
            except am.ProcessJumpRequest as e:
              progress = context.cast(e).point.progress

              context.send_term(am.DurationTerm(total_duration * (1.0 - progress)))
              context.send_location(ProcessLocation(total_duration, progress))
            else:
              break
        except asyncio.CancelledError:
          halt_time = time.time()
          progress += (halt_time - start_time) / total_duration

          context.send_location(ProcessLocation(total_duration, progress))
          raise
        else:
          break

      context.send_location(ProcessLocation(total_duration, 1.0))

process = Process()
