import asyncio
from dataclasses import dataclass
from enum import IntEnum
import time
import traceback
from types import EllipsisType
from typing import Any, AsyncIterator, Generator, Optional, Protocol, Sequence

from ..util.iterators import CoupledStateIterator2
from ..util.ref import Ref
from ..host import logger
from .process import Process, ProgramExecEvent
from .langservice import Analysis
from .parser import BaseBlock, BaseTransform, BlockProgram, BlockState, Transforms
from ..devices.claim import ClaimSymbol
from ..draft import DraftDiagnostic, DraftGenericError
from ..reader import LocationArea
from ..util.decorators import debug
from ..util.misc import Exportable
from .master2 import Master


logger = logger.getChild("segment")


class RemainingTransformsError(Exception):
  def __init__(self, area: LocationArea):
    self.area = area

  def diagnostic(self):
    return DraftDiagnostic(f"Remaining transforms", ranges=self.area.ranges)


@dataclass
class SegmentProcessData:
  data: Exportable
  namespace: str

  def export(self):
    return {
      "data": self.data.export(),
      "namespace": self.namespace
    }

@debug
class SegmentTransform(BaseTransform):
  def __init__(self, namespace: str, process_data: Exportable):
    self._process = SegmentProcessData(process_data, namespace)

  def execute(self, state: BlockState, transforms: Transforms, *, origin_area: LocationArea) -> tuple[Analysis, BaseBlock | EllipsisType]:
    if transforms:
      return Analysis(errors=[RemainingTransformsError(origin_area)]), Ellipsis

    return Analysis(), SegmentBlock(
      process=self._process,
      state=state
    )


class SegmentProgramMode(IntEnum):
  Halted = 5
  Halting = 4
  Normal = 0
  PausingProcess = 1
  PausingState = 2
  Paused = 3

@dataclass(kw_only=True)
class SegmentProgramLocation:
  mode: SegmentProgramMode
  process: Any
  time: float
  state: Optional[Any] = None

  def export(self):
    return {
      "mode": self.mode,
      "process": self.process.export(),
      "state": self.state and self.state.export(),
      "time": self.time * 1000.0
    }

@dataclass(kw_only=True)
class SegmentProgramPoint:
  process: Optional[Any]

  # @classmethod
  # def import_value(cls, program: 'SegmentProgram'):
  #   program._block.Program.Point.import_value(program)
  #   return cls(process=)

class SegmentProgram(BlockProgram):
  Point = SegmentProgramPoint

  def __init__(self, block: 'SegmentBlock', master, parent):
    self._block = block
    self._master: Master = master
    self._parent = parent

    self._mode: SegmentProgramMode
    self._point: Optional[SegmentProgramPoint]
    self._process: Process

  def import_message(self, message: dict):
    match message["type"]:
      case "halt":
        self.halt()
        # @dataclass
        # class A:
        #   progress = 0.5

        # self.jump(SegmentProgramPoint(process=A()))
      case "pause":
        self.pause()
      case "resume":
        self.resume()

  def halt(self):
    assert self._mode in (SegmentProgramMode.Normal, SegmentProgramMode.Paused)

    self._mode = SegmentProgramMode.Halting
    self._process.halt()

  def jump(self, point: SegmentProgramPoint):
    assert self._mode == SegmentProgramMode.Normal

    if hasattr(self._process, 'jump'):
      self._process.jump(point.process)
    else:
      self._point = point
      self.halt()

  def pause(self):
    assert self._mode == SegmentProgramMode.Normal

    self._mode = SegmentProgramMode.PausingProcess
    self._process.pause()

  def resume(self):
    assert self._mode == SegmentProgramMode.Paused
    self._process.resume()

  async def run(self, initial_point: Optional[SegmentProgramPoint], symbol: ClaimSymbol):
    Process = self._master.chip.runners[self._block._process.namespace].Process
    self._point = initial_point or SegmentProgramPoint(process=None)

    async def run():
      while self._point:
        point = self._point
        self._mode = SegmentProgramMode.Normal
        self._point = None
        self._process = Process(self._block._process.data)

        async for event in self._process.run(point.process):
          yield event

    iterator = CoupledStateIterator2[ProgramExecEvent, Any](run())

    state_instance = self._master.create_instance(self._block.state, notify=iterator.notify, symbol=symbol)
    state_location = state_instance.apply(self._block.state, resume=False)
    iterator.notify(state_location)

    async for event, state_location in iterator:
      event_time = event.time or time.time()

      if (self._mode == SegmentProgramMode.PausingProcess) and event.stopped:
        self._mode = SegmentProgramMode.PausingState
        await state_instance.suspend()

      if (self._mode == SegmentProgramMode.Halting) and event.stopped:
        self._mode = SegmentProgramMode.Halted

      if self._mode == SegmentProgramMode.PausingState:
        self._mode = SegmentProgramMode.Paused

      if (self._mode == SegmentProgramMode.Paused) and (not event.stopped):
        self._mode = SegmentProgramMode.Normal
        state_location = state_instance.apply(self._block.state, resume=True)

      yield ProgramExecEvent(
        state=SegmentProgramLocation(
          mode=self._mode,
          process=event.state,
          state=state_location,
          time=event_time
        ),
        stopped=(self._mode in (SegmentProgramMode.Paused, SegmentProgramMode.Halted))
      )

    # TODO: Already suspended when doing Pause then Halt
    await state_instance.suspend()


@dataclass
class LinearSegment:
  process: SegmentProcessData
  state: BlockState

@debug
class SegmentBlock(BaseBlock):
  Program = SegmentProgram

  def __init__(self, process: SegmentProcessData, state: BlockState):
    self._process = process
    self.state: BlockState = state

  def linearize(self, context, parent_state):
    return Analysis(), [LinearSegment(self._process, parent_state | self.state)]

    # analysis = Analysis()
    # state = dict()

    # for namespace, unit_state in self._segment.state.items():
    #   if unit_state and hasattr(unit_state, 'assemble'):
    #     unit_analysis, unit_state_assembled = unit_state.assemble(context)
    #     analysis += unit_analysis

    #     if unit_state_assembled is Ellipsis:
    #       return analysis, Ellipsis

    #     state[namespace] = unit_state_assembled
    #   else:
    #     state[namespace] = unit_state

    # return analysis, [Segment(
    #   process_data=self._segment.process_data,
    #   process_namespace=self._segment.process_namespace,
    #   state=BlockState(state)
    # )]

  def export(self):
    return {
      "namespace": "segment",
      "process": self._process.export(),
      "state": self.state.export()
    }
