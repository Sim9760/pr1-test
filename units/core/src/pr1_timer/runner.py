import asyncio
from dataclasses import dataclass
import time
from typing import Any, Optional

from pr1.fiber.eval import EvalStack
from pr1.fiber.process import Process as ProcessIntf, ProcessExecEvent, ProcessFailureEvent, ProcessPauseEvent, ProcessTerminationEvent
from pr1.units.base import BaseProcessRunner

from . import namespace


@dataclass
class ProcessLocation:
  progress: float
  paused: bool = False

  def export(self):
    return {
      "paused": self.paused,
      "progress": self.progress
    }

@dataclass
class ProcessPoint:
  progress: float

  @classmethod
  def import_value(cls, value: Any):
    return cls(progress=value["progress"])

class Process(ProcessIntf):
  def __init__(self, data: Any, *, runner: 'Runner'):
    self._data = data

    self._progress: Optional[float] = None
    self._resume_future: Optional[asyncio.Future] = None
    self._task: Optional[asyncio.Task] = None

  def halt(self):
    if self._task:
      self._task.cancel()
    if self._resume_future:
      self._resume_future.cancel()
      self._resume_future = None

  def jump(self, point: ProcessPoint):
    self._progress = point.progress

    if self._task:
      self._task.cancel()

  def pause(self):
    assert self._task

    self._resume_future = asyncio.Future()
    self._task.cancel()

  def resume(self):
    assert self._resume_future

    self._resume_future.set_result(None)
    self._resume_future = None

  async def run(self, initial_point: Optional[ProcessPoint], *, stack: EvalStack):
    self._progress = initial_point.progress if initial_point else 0.0
    total_duration = self._data._value / 1000.0

    while True:
      progress = self._progress
      self._progress = None

      remaining_duration = total_duration * (1.0 - progress)
      task_time = time.time()

      yield ProcessExecEvent(
        duration=remaining_duration,
        location=ProcessLocation(progress),
        pausable=True,
        time=task_time
      )

      self._task = asyncio.create_task(asyncio.sleep(remaining_duration))

      try:
        await self._task
      except asyncio.CancelledError:
        if self._progress is None:
          self._task = None

          current_time = time.time()
          elapsed_time = current_time - task_time

          progress += elapsed_time / total_duration
          remaining_duration = total_duration * (1.0 - progress)
          self._progress = progress

          # yield ProcessExecEvent(location=ProcessLocation(self._progress, paused=True))
          # await asyncio.sleep(2)

          yield ProcessPauseEvent(
            duration=remaining_duration,
            location=ProcessLocation(progress, paused=True),
            time=current_time
          )

          if self._resume_future:
            try:
              await self._resume_future
            except asyncio.CancelledError:
              # The process is halting while being paused.

              yield ProcessTerminationEvent(
                location=ProcessLocation(progress, paused=True),
                time=current_time
              )

              return
          else:
            # The process is halting.
            return
      else:
        break
      finally:
        self._task = None

    yield ProcessTerminationEvent(
      location=ProcessLocation(1.0)
    )

class Runner(BaseProcessRunner):
  Process = Process

  def __init__(self, chip, *, host):
    self._chip = chip
    # self._executor = host.executors[namespace]
