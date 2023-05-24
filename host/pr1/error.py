from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, Any, Optional
import uuid

from .util.misc import Exportable

if TYPE_CHECKING:
  from .reader import LocatedValue, LocationArea


@dataclass(kw_only=True)
class DiagnosticReference(Exportable):
  id: str
  label: Optional[str] = None

  def export(self):
    return {
      "id": self.id,
      "label": self.label
    }

@dataclass(kw_only=True)
class DiagnosticDocumentReference(DiagnosticReference, Exportable):
  area: 'Optional[LocationArea]'
  document_id: str

  def export(self):
    return {
      **super().export(),
      "type": "document",
      "documentId": self.document_id,
      "ranges": [(range.start, range.end) for range in self.area.ranges] if self.area else list()
    }

  @classmethod
  def from_area(cls, area: 'LocationArea', *, id: str = 'target'):
    from .document import Document

    assert area.source

    document = area.source.origin
    assert isinstance(document, Document)

    return cls(
      area=area,
      document_id=document.id,
      id=id
    )

  @classmethod
  def from_value(cls, value: 'LocatedValue', *, id: str = 'target'):
    return cls.from_area(value.area, id=id)

@dataclass(kw_only=True)
class ErrorFileReference(DiagnosticReference):
  path: str

  def export(self):
    return {
      **super().export(),
      "type": "file",
      "path": self.path
    }

Trace = list[DiagnosticReference]

@dataclass
class Diagnostic(Exportable):
  message: str
  _: KW_ONLY
  description: list[str] = field(default_factory=list)
  id: Optional[str] = None
  name: str = 'unknown'
  references: list[DiagnosticReference] = field(default_factory=list)
  trace: Optional[Trace] = None

  def as_master(self, *, time: Optional[float] = None):
    from .master.analysis import MasterError

    return MasterError(
      description=self.description,
      message=self.message,
      name=self.name,
      id=(self.id or str(uuid.uuid4())),
      references=self.references,
      time=time
    )

  def export(self):
    return {
      "description": self.description,
      "id": self.id,
      "message": self.message,
      "name": self.name,
      "references": [ref.export() for ref in self.references],
      "trace": [ref.export() for ref in self.trace] if (self.trace is not None) else None
    }
