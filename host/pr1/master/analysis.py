import comserde
import uuid
from abc import ABC, abstractmethod
from dataclasses import KW_ONLY, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Literal, Optional, TypeVar

from ..analysis import BaseAnalysis, DiagnosticAnalysis
from ..error import Diagnostic, DiagnosticReference
from ..util.misc import Exportable


T_Exportable = TypeVar('T_Exportable', bound=Exportable)


@comserde.serializable
@dataclass(kw_only=True)
class Effect(ABC, Exportable):
  author_path: list[int]
  references: list[DiagnosticReference] = field(default_factory=list)
  time: float

  @abstractmethod
  def export(self) -> Any:
    return {
      "references": [ref.export() for ref in self.references]
    }

@comserde.serializable
@dataclass
class FileCreatedEffect(Effect):
  path: Path

@comserde.serializable
@dataclass
class GenericEffect(Effect):
  message: str

  def export(self):
    return {
      **super().export(),
      "message": self.message
    }


@comserde.serializable
@dataclass(kw_only=True)
class TimedDiagnostic(Diagnostic):
  time: float

  def export(self):
    return {
      **super().export(),
      "type": "timed",
      "date": (self.time * 1000)
    }

@comserde.serializable
@dataclass
class RuntimeMasterAnalysisItem(Generic[T_Exportable]):
  value: T_Exportable
  _: KW_ONLY
  author_path: list[int]
  event_index: int

  def export(self):
    return {
      "authorPath": self.author_path,
      "eventIndex": self.event_index,
      "value": self.value.export()
    }


@comserde.serializable
@dataclass(kw_only=True)
class RuntimeAnalysis(DiagnosticAnalysis):
  effects: list[Effect] = field(default_factory=list)

  def _add(self, other: DiagnosticAnalysis, /):
    super()._add(other)

    if isinstance(other, RuntimeAnalysis):
      self.effects += other.effects


@comserde.serializable
@dataclass(kw_only=True)
class MasterAnalysis(BaseAnalysis):
  effects: list[RuntimeMasterAnalysisItem[Effect]] = field(default_factory=list)
  errors: list[RuntimeMasterAnalysisItem[Diagnostic]] = field(default_factory=list)
  warnings: list[RuntimeMasterAnalysisItem[Diagnostic]] = field(default_factory=list)

  def add_runtime(self, other: RuntimeAnalysis, /, author_path: list[int], event_index: int):
    def add_items(items: list[T_Exportable]):
      return [RuntimeMasterAnalysisItem(item, author_path=author_path, event_index=event_index) for item in items]

    self.effects += add_items(other.effects)
    self.errors += add_items(other.errors)
    self.warnings += add_items(other.warnings)

  def _add(self, other: 'MasterAnalysis', /):
    super()._add(other)

    self.errors += other.errors
    self.effects += other.effects
    self.warnings += other.warnings

  def export(self):
    return {
      "effects": [effect.export() for effect in self.effects],
      "errors": [error.export() for error in self.errors],
      "warnings": [warning.export() for warning in self.warnings]
    }


__all__ = [
  'Effect',
  'FileCreatedEffect',
  'GenericEffect',
  'MasterAnalysis',
  'RuntimeAnalysis'
]
