import builtins
import copy
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import KW_ONLY, dataclass, field
from io import BytesIO, FileIO, IOBase, TextIOBase
from logging import Logger
from os import PathLike
from pathlib import Path
import re
from tokenize import TokenError
from types import EllipsisType
from typing import (TYPE_CHECKING, Any, Callable, Generic, Literal, Optional,
                    Protocol, TypeVar, cast)

import numpy as np
import pint
from pint import Quantity, Unit

from ..langservice import *
from ..error import Diagnostic, Diagnostic, DiagnosticDocumentReference, Trace
from ..reader import (LocatedDict, LocatedError, LocatedList, LocatedString,
                      LocatedValue, LocatedValueContainer, LocationArea,
                      LocationRange, PossiblyLocatedValue, ReliableLocatedDict, ReliableLocatedList, UnlocatedValue)
from ..ureg import ureg
from ..util.misc import Exportable, create_datainstance
from ..util.parser import is_identifier
from ..fiber.expr import (Evaluable, PythonExpr, PythonExprKind, PythonExprObject,
                   ValueAsPythonExpr)

if TYPE_CHECKING:
  from ..fiber.parser import AnalysisContext


class AmbiguousKeyError(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(
      f"Ambiguous key '{target}'",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class DuplicateKeyError(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(
      f"Duplicate key '{target}'",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class ExtraneousKeyError(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(
      f"Unrecognized key '{target}'",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class MissingKeyError(Diagnostic):
  def __init__(self, target: LocatedValue, /, key: str):
    super().__init__(
      f"Missing key '{key}'",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class InvalidIdentifierError(Diagnostic):
  def __init__(self, target: LocatedValue):
    super().__init__(
      "Invalid identifier",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class InvalidEnumValueError(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(f"Invalid enum value", references=[DiagnosticDocumentReference.from_value(target)])

class MissingAttributeError(Diagnostic):
  def __init__(self, target: LocatedValue, attribute: str, /):
    super().__init__(f"Missing attribute '{attribute}'", references=[DiagnosticDocumentReference.from_value(target)])

class InvalidDataTypeError(Diagnostic):
  def __init__(self, target: LocatedValue, /, message: str):
    super().__init__(f"Invalid data type: {message}", references=[DiagnosticDocumentReference.from_value(target)])

class InvalidIntegerError(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(f"Invalid integer", references=[DiagnosticDocumentReference.from_value(target)])


class Type(Protocol):
  def analyze(self, obj: LocatedValue, /, context: 'AnalysisContext') -> tuple[LanguageServiceAnalysis, Any | EllipsisType]:
    ...

CompletionKind = Literal['class', 'constant', 'enum', 'field', 'property']

class Attribute:
  def __init__(
    self,
    type: Type,
    *,
    decisive: bool = False,
    default: Any | EllipsisType = Ellipsis,
    deprecated: bool = False,
    description: Optional[str] = None,
    documentation: Optional[list[str]] = None,
    kind: CompletionKind = 'field',
    label: Optional[str] = None,
    optional: bool = False,
    signature: Optional[str] = None
  ):
    """
    Creates an `Attribute` instance.

    Parameters
      type: The attribute's type.
      decisive: Whether the parent dictionary's analysis should fail when this attribute is itself missing. Always `True` for required attributes, otherwise defaults to `False`.
      default: The attribute's default value. Defaults to no default value.
      deprecated: Whether the attribute is deprecated. Defaults to `False`.
      description: The attribute's description. Optional.
      documentation: Additional information on the attribute. Optional.
      kind: The attribute's completion kind, which determines which icon to display when completing with this attributes. See [the Monaco Editor's documentation](https://microsoft.github.io/monaco-editor/docs.html#enums/languages.CompletionItemKind.html) for the full list. Defaults to `field`.
      label: The attribute's label. Defaults to the attribute's name in uppercase.
      optional: Whether the attribute is optional. Defaults to `False`.
      signature: The attribute's signature, displayed with a monospace font. Optional.
    """

    self._optional = optional or not isinstance(default, EllipsisType)

    self._decisive = (not self._optional) or decisive
    self._default = default
    self._deprecated = deprecated
    self._description = description
    self._documentation = documentation
    self._kind = kind
    self._label = label
    self._signature = signature
    self._type = type

  @property
  def type(self):
    return self._type

  def analyze(self, obj: Any, key: LocatedString, context: 'AnalysisContext'):
    analysis = LanguageServiceAnalysis()
    key_range = key.area.single_range()

    if self._description or self._documentation or self._label:
      analysis.hovers.append(LanguageServiceHover(
        contents=([f"#### {self._label or key.upper()}"] + ([self._description] if self._description else list()) + (self._documentation or list())),
        range=key_range
      ))

    if self._deprecated:
      analysis.markers.append(LanguageServiceMarker("Deprecated attribute", DiagnosticDocumentReference.from_value(key), kind='deprecated'))

    value_analysis, value = self._type.analyze(obj, context)

    return (analysis + value_analysis), value


# @deprecated
class CompositeDict:
  _native_namespace = "_"
  _separator = "/"

  def __init__(self, attrs: dict[str, Attribute | Type] = dict(), /, *, foldable: bool = True, strict: bool = False):
    self._foldable = foldable
    self._strict = strict

    self._attributes = {
      attr_name: { self._native_namespace: attr if isinstance(attr, Attribute) else Attribute(cast(Type, attr)) } for attr_name, attr in attrs.items()
    }

    self._namespaces = {self._native_namespace}

  @property
  def completion_items(self):
    completion_items = list[LanguageServiceCompletionItem]()

    for attr_name, attr_entries in self._attributes.items():
      ambiguous = (len(attr_entries) > 1)

      for namespace, attr in attr_entries.items():
        native = (namespace == self._native_namespace)

        completion_items.append(LanguageServiceCompletionItem(
          documentation=attr._description,
          kind=attr._kind,
          label=attr_name,
          namespace=(namespace if not native else None),
          signature=(attr._signature or (f"{attr_name}: <value>" if attr._description else None)),
          sublabel=attr._label,
          text=(f"{namespace}{self._separator}{attr_name}" if ambiguous and (not native) else attr_name)
        ))

    return completion_items

  def add(self, attrs, *, namespace):
    self._namespaces.add(namespace)

    for attr_name, attr in attrs.items():
      if not attr_name in self._attributes:
        self._attributes[attr_name] = dict()

      self._attributes[attr_name][namespace] = attr

  def get_attr(self, attr_name):
    segments = attr_name.split(self._separator)

    if len(segments) > 1:
      namespace = segments[0]
      attr_name = self._separator.join(segments[1:])
    else:
      namespace = None

    attr_entries = self._attributes.get(attr_name)

    return namespace, attr_name, attr_entries

  def analyze(self, obj, context) -> tuple[LanguageServiceAnalysis, LocatedDict | EllipsisType]:
    analysis = LanguageServiceAnalysis()
    strict_failed = False

    primitive_analysis, obj = PrimitiveType(dict).analyze(obj, context)
    analysis += primitive_analysis

    if isinstance(obj, EllipsisType):
      return analysis, obj

    assert isinstance(obj, ReliableLocatedDict)

    if self._foldable:
      analysis.folds.append(LanguageServiceFoldingRange(obj.fold_range))

    analysis.selections.append(LanguageServiceSelection(obj.full_area.enclosing_range()))

    attr_values = { namespace: dict() for namespace in self._namespaces }

    for obj_key, obj_value in obj.items():
      namespace, attr_name, attr_entries = self.get_attr(obj_key)

      # e.g. 'invalid/bar'
      if namespace and not (namespace in self._namespaces):
        analysis.errors.append(ExtraneousKeyError(namespace))
        continue

      # e.g. 'foo/invalid' or 'invalid'
      if not attr_entries:
        analysis.errors.append(ExtraneousKeyError(obj_key))
        continue

      if not namespace:
        # e.g. 'bar' where '_/bar' exists
        if self._native_namespace in attr_entries:
          namespace = self._native_namespace
        # e.g. 'bar' where only 'a/bar' exists
        elif len(attr_entries) == 1:
          namespace = next(iter(attr_entries.keys()))
        # e.g. 'bar' where 'a/bar' and 'b/bar' both exist, but not '_/bar'
        else:
          analysis.errors.append(AmbiguousKeyError(obj_key))
          continue
      # e.g. 'foo/bar'
      else:
        pass

      if attr_name in attr_values[namespace]:
        analysis.errors.append(DuplicateKeyError(obj_key))
        continue

      attr = attr_entries[namespace]
      attr_analysis, attr_value = attr.analyze(obj_value, obj_key, context)

      if not (isinstance(attr_value, EllipsisType) and self._strict and attr._optional):
        attr_values[namespace][attr_name] = attr_value

        if isinstance(attr_value, EllipsisType):
          strict_failed = True

      analysis += attr_analysis

    for attr_name, attr_entries in self._attributes.items():
      for namespace, attr in attr_entries.items():
        if (not attr._optional) and not (attr_name in attr_values[namespace]):
          analysis.errors.append(MissingKeyError(obj, (f"{namespace}{self._separator}" if namespace != self._native_namespace else str()) + attr_name))
          strict_failed = True

    analysis.completions.append(LanguageServiceCompletion(
      items=self.completion_items,
      ranges=[
        *[obj_key.area.single_range() for obj_key in obj.keys()],
        *obj.completion_ranges
      ]
    ))

    return analysis, LocatedDict(attr_values, obj.area) if not (self._strict and strict_failed) else Ellipsis

  def merge(self, attr_values1, attr_values2):
    return {
      namespace: attr_values1[namespace] | attr_values2[namespace] for namespace in attr_values1.keys()
    }


# @deprecated
class SimpleDict(CompositeDict):
  def __init__(self, attrs: dict[str, Attribute | Type], /, *, foldable = False, strict = False):
    super().__init__(attrs, foldable=foldable, strict=strict)

  def analyze(self, obj, context):
    analysis, output = super().analyze(obj, context)

    return analysis, LocatedDict(output[self._native_namespace], obj.area) if not isinstance(output, EllipsisType) else Ellipsis

# @deprecated
class DictType(SimpleDict):
  def __init__(self, attrs, *, foldable = False):
    super().__init__(attrs, foldable=foldable, strict=True)


T = TypeVar('T')

class DivisibleCompositeDictType(Type, Generic[T]):
  def __init__(self, *, foldable: bool = True, separator: str = "/"):
    self._attributes_by_key = dict[T, dict[str, Attribute]]()
    self._attributes_by_name = dict[str, tuple[bool, Optional[T]]]()
    self._attributes_by_unique_name = dict[str, tuple[T, str]]()

    # [_/1]
    # [_/1], a/1
    # [a/1]
    # a/1, b/1

    self._foldable = foldable
    self._separator = separator

  @property
  def completion_items(self):
    completion_items = list[LanguageServiceCompletionItem]()

    for namespace, attrs in self._attributes_by_key.items():
      for attr_name, attr in attrs.items():
        completion_items.append(LanguageServiceCompletionItem(
          documentation=attr._description,
          kind=attr._kind,
          label=attr_name,
          namespace=None,
          signature=(attr._signature or (f"{attr_name}: <value>" if attr._description else None)),
          sublabel=attr._label,
          text=(attr_name)
        ))

    return completion_items

  def add(self, attrs: dict[str, Attribute | Type] | dict[str, Attribute], /, key: T, prefix: Optional[str] = None, *, optional: bool = False):
    assert not (key in self._attributes_by_key)
    assert key is not None

    self._attributes_by_key[key] = dict()

    for attr_name, raw_attr in attrs.items():
      if isinstance(raw_attr, Attribute):
        attr = raw_attr
      else:
        attr = Attribute(cast(Type, raw_attr))

      if optional:
        attr._optional = True

      if prefix:
        attr = copy.copy(attr)
        unique_name = f"{prefix}{self._separator}{attr_name}"

        assert not (unique_name in self._attributes_by_unique_name)
        self._attributes_by_unique_name[unique_name] = (key, attr_name)

      self._attributes_by_key[key][attr_name] = attr

      native = not prefix

      match (native, self._attributes_by_name.get(attr_name)):
        case (_, None) | (True, (False, _)):
          self._attributes_by_name[attr_name] = (native, key)
        case (False, (False, _)):
          self._attributes_by_name[attr_name] = (True, None)
        case (True, (True, _)):
          raise ValueError("Duplicate name")

  def analyze(self, obj, /, context):
    analysis, primitive_result = PrimitiveType(dict).analyze(obj, context)

    if isinstance(primitive_result, EllipsisType):
      return analysis, Ellipsis

    assert isinstance(obj, LocatedDict)

    if isinstance(obj, ReliableLocatedDict) and self._foldable:
      if self._foldable:
        analysis.folds.append(LanguageServiceFoldingRange(obj.fold_range))

      analysis.completions.append(LanguageServiceCompletion(
        items=self.completion_items,
        ranges=[
          *[obj_key.area.single_range() for obj_key in obj.keys()],
          *obj.completion_ranges
        ]
      ))

    analysis.selections.append(LanguageServiceSelection(obj.full_area.enclosing_range()))

    attr_values = { key: dict[LocatedString, Any]() for key in self._attributes_by_key.keys() }

    for obj_key, obj_value in obj.items():
      unique_attr = self._attributes_by_unique_name.get(obj_key)

      # e.g. 'foo/bar'
      if unique_attr:
        key, attr_name = unique_attr

      # e.g. 'foobar'
      elif (unprefixed_attr := self._attributes_by_name.get(obj_key)):
        _, unprefixed_key = unprefixed_attr

        # e.g. 'bar' where '_/bar' exists
        # e.g. 'bar' where only 'a/bar' exists
        if unprefixed_key is not None:
          key = unprefixed_key
          attr_name = obj_key.value
        # e.g. 'bar' where 'a/bar' and 'b/bar' both exist, but not '_/bar'
        else:
          analysis.errors.append(AmbiguousKeyError(obj_key))
          continue

      # e.g. 'foo/invalid' or 'invalid'
      else:
        analysis.errors.append(ExtraneousKeyError(obj_key))
        continue

      if attr_name in attr_values[key]:
        analysis.errors.append(DuplicateKeyError(obj_key))
        continue

      attr_values[key][LocatedString(attr_name, absolute=False, area=obj_key.area)] = obj_value

    failure = False

    for prefix, attrs in self._attributes_by_key.items():
      for attr_name, attr in attrs.items():
        if (not attr._optional) and not (attr_name in attr_values[prefix]):
          analysis.errors.append(MissingKeyError(obj, attr_name))
          failure = True

    return analysis, (attr_values if not failure else Ellipsis)

  def analyze_namespace(self, attr_values: dict[T, dict[LocatedString, Any]], /, context: 'AnalysisContext', *, key: T):
    analysis = LanguageServiceAnalysis()
    failure = False
    result = dict[PossiblyLocatedValue[str], Any]()

    for attr_name, attr_value in attr_values[key].items():
      attr = self._attributes_by_key[key][attr_name]
      attr_result = analysis.add(attr.analyze(attr_value, attr_name, context))

      if not isinstance(attr_result, EllipsisType):
        result[attr_name] = attr_result
      elif attr._decisive:
        failure = True

    if failure:
      return analysis, Ellipsis

    for attr_name, attr in self._attributes_by_key[key].items():
      if not (attr_name in attr_values[key]) and not isinstance(attr._default, EllipsisType):
        result[UnlocatedValue(attr_name)] = ValueAsPythonExpr.new(UnlocatedValue(attr._default), depth=context.eval_depth)

    return analysis, result

  def copy(self):
    output = DivisibleCompositeDictType.__new__(self.__class__)

    output._attributes_by_key = self._attributes_by_key.copy()
    output._attributes_by_name = self._attributes_by_name.copy()
    output._attributes_by_unique_name = self._attributes_by_unique_name.copy()

    output._foldable = self._foldable
    output._separator = self._separator

    return output


class RecordType(DivisibleCompositeDictType):
  def __init__(self, attrs: dict[str, Attribute | Type]):
    super().__init__()
    self.add(attrs, key=0)

  def analyze(self, obj, /, context) -> tuple[LanguageServiceAnalysis, Any | EllipsisType]:
    analysis, global_result = super().analyze(obj, context)

    if isinstance(global_result, EllipsisType):
      return analysis, Ellipsis

    result = analysis.add(super().analyze_namespace(global_result, context, key=0))

    if isinstance(result, EllipsisType):
      return analysis, Ellipsis

    # located_result = obj.transform(result) if isinstance(obj, ReliableLocatedDict) else LocatedDict(result, obj.area)

    return analysis, EvaluableRecordType.new(LocatedValue(result, obj.area), depth=context.eval_depth)

class EvaluableRecordType(Evaluable):
  def __init__(self, value: LocatedValue[dict[PossiblyLocatedValue[str], Evaluable[PossiblyLocatedValue[Any]]]], /, *, depth: int):
    self._depth = depth
    self._value = value

  def __getitem__(self, key: str, /):
    return self._value.value[key] # type: ignore

  def evaluate(self, context):
    analysis = LanguageServiceAnalysis()
    result = dict[PossiblyLocatedValue[str], Any]()

    for key, value in self._value.value.items():
      item_result = analysis.add(value.evaluate(context))

      # TODO: Same as lists
      if isinstance(item_result, EllipsisType):
        return analysis, Ellipsis

      result[key] = item_result

    return analysis, self.new(LocatedValue(result, self._value.area), depth=(self._depth - 1))

  def export(self):
    raise NotImplementedError

  def __repr__(self):
    return f"{self.__class__.__name__}({self._value!r}, depth={self._depth})"

  @classmethod
  def new(cls, value: LocatedValue[dict[PossiblyLocatedValue[str], Any]], /, *, depth: int):
    return cls(value, depth=depth) if depth > 0 else LocatedValue(create_datainstance({ item_key.value: item_value for item_key, item_value in value.value.items() }), value.area)


class InvalidPrimitiveError(Diagnostic):
  def __init__(self, target: LocatedValue, primitive: Callable):
    super().__init__(
      f"Invalid primitive, expected {primitive.__name__}",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class MissingUnitError(Diagnostic):
  def __init__(self, target: LocatedValue, /, unit: Unit):
    super().__init__(
      f"Missing unit, expected {unit:~P}",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class InvalidUnitError(Diagnostic):
  def __init__(self, target: LocatedValue, /, unit: Unit):
    super().__init__(
      f"Invalid unit, expected {unit:P}",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class UnknownUnitError(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(
      "Unknown unit",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class InvalidExpr(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(
      "Invalid value, expected expression",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class InvalidExprKind(Diagnostic):
  def __init__(self, target: LocatedValue, /):
    super().__init__(
      "Invalid expression kind",
      references=[DiagnosticDocumentReference.from_value(target)]
    )

class OutOfBoundsQuantityError(Diagnostic):
  def __init__(self, target: LocatedValue, /, min: Optional[Quantity], max: Optional[Quantity]):
    super().__init__(
      "Out of bounds value",
      references=[DiagnosticDocumentReference.from_value(target)]
    )


class AnyType(Type):
  def __init__(self):
    pass

  def analyze(self, obj, /, context):
    return LanguageServiceAnalysis(), ValueAsPythonExpr.new(obj, depth=context.eval_depth)

class PrimitiveType(Type):
  def __init__(self, primitive: Any, /):
    self._primitive = primitive

  def _analyze(self, obj, /, context):
    match self._primitive:
      case builtins.int if isinstance(obj, str):
        assert isinstance(obj, LocatedString)

        if match := re.compile(r"^0x([0-9a-f]+)$").match(obj.value):
          value = int(match[1], 16)
        elif match := re.compile(r"^0b([01]+)$").match(obj.value):
          value = int(match[1], 2)
        elif re.compile(r"^-?[0-9]+$").match(obj.value):
          value = int(obj.value)
        else:
          return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(obj, self._primitive)]), Ellipsis

        return LanguageServiceAnalysis(), LocatedValue.new(value, area=obj.area)
      case builtins.float if isinstance(obj, str):
        assert isinstance(obj, LocatedString)

        try:
          value = float(obj.value)
        except (TypeError, ValueError):
          return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(obj, self._primitive)]), Ellipsis
        else:
          return LanguageServiceAnalysis(), LocatedValue.new(value, area=obj.area)
      case builtins.bool if isinstance(obj, str):
        assert isinstance(obj, LocatedString)

        if obj.value in ("true", "false"):
          return LanguageServiceAnalysis(), LocatedValue.new((obj.value == "true"), area=obj.area)
        else:
          return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(obj, self._primitive)]), Ellipsis
      case _ if not isinstance(obj.value, self._primitive):
        return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(obj, self._primitive)]), Ellipsis
      case builtins.int if isinstance(obj.value, int): # Convert booleans to ints
        return LanguageServiceAnalysis(), LocatedValue.new(int(obj.value), obj.area)
      case _:
        return LanguageServiceAnalysis(), obj

  def analyze(self, obj, /, context):
    analysis, result = self._analyze(obj, context)
    return analysis, (ValueAsPythonExpr.new(result, depth=context.eval_depth) if (not isinstance(result, EllipsisType)) else Ellipsis)

class TransformType(Type):
  def __init__(self, parent_type: Type, transformer: Callable, /):
    self._type = parent_type
    self._transformer = transformer

  def analyze(self, obj, context):
    analysis, value = self._type.analyze(obj, context)
    return analysis, self._transformer(value) if not isinstance(value, EllipsisType) else Ellipsis

class ListType(Type):
  def __init__(self, item_type: Type, /, *, foldable: bool = True):
    self._foldable = foldable
    self._item_type = item_type

  def analyze(self, obj, /, context):
    analysis, primitive_result = PrimitiveType(list).analyze(obj, context)

    if isinstance(primitive_result, EllipsisType):
      return analysis, Ellipsis

    assert isinstance(obj, LocatedList)

    if isinstance(obj, ReliableLocatedList) and self._foldable:
      analysis.folds.append(LanguageServiceFoldingRange(obj.fold_range))

    analysis.selections.append(LanguageServiceSelection(obj.full_area.enclosing_range()))

    result = list()

    for item in obj:
      item_analysis, item_result = self._item_type.analyze(item, context)

      analysis += item_analysis

      if not isinstance(item_result, EllipsisType):
        result.append(item_result)

    if isinstance(obj, ReliableLocatedList) and isinstance(self._item_type, DivisibleCompositeDictType):
      analysis += self.create_completion(obj, self._item_type)

    located_result = obj.transform(result) if isinstance(obj, ReliableLocatedList) else LocatedList(result, obj.area)
    return analysis, ListAsPythonExpr.new(located_result, depth=context.eval_depth)

  def create_completion(self, obj, item_type: DivisibleCompositeDictType, /):
    completion_ranges = list(obj.completion_ranges)

    for item in obj:
      if isinstance(item, LocatedString):
        completion_ranges.append(item.area.single_range())

    analysis = LanguageServiceAnalysis()

    if completion_ranges:
      analysis.completions.append(LanguageServiceCompletion(
        items=item_type.completion_items,
        ranges=completion_ranges
      ))

    return analysis


S = TypeVar('S', bound=LocatedValue)

class ListAsPythonExpr(Evaluable[LocatedList[S]], Generic[S]):
  def __init__(self, value: LocatedList[Evaluable[S]], /, *, depth: int):
    self._depth = depth
    self._value = value

  def evaluate(self, context):
    analysis = LanguageServiceAnalysis()
    result = list[Any]()

    for item in self._value:
      item_result = analysis.add(item.evaluate(context))

      if isinstance(item_result, EllipsisType):
        return analysis, Ellipsis # TODO: Improve that using a flag to disable during dynamic evaluation

      result.append(item_result)

    return analysis, self.new(LocatedList(result, self._value.area), depth=(self._depth - 1))

  def export(self):
    raise NotImplementedError

  def __repr__(self):
    return f"{self.__class__.__name__}({self._value!r}, depth={self._depth})"

  @classmethod
  def new(cls, value: LocatedList, /, *, depth: int):
    return cls(value, depth=depth) if depth > 0 else value


class LiteralOrExprType(Type):
  def __init__(self, obj_type: Optional[Type] = None, /, *, dynamic: bool = False, expr_type: Optional[Type] = None, field: bool = False, static: bool = False, _force_expr: bool = False):
    self._kinds = set[PythonExprKind]()
    self._force_expr = _force_expr
    self._type = obj_type or cast(Type, super())
    self._expr_type = expr_type or self._type

    if dynamic:
      self._kinds.add(PythonExprKind.Dynamic)
    if field:
      self._kinds.add(PythonExprKind.Field)
    if static:
      self._kinds.add(PythonExprKind.Static)

  def analyze(self, obj, context):
    if isinstance(obj, str):
      assert isinstance(obj, LocatedString)
      result = PythonExpr.parse(obj)

      if result:
        analysis, expr = result

        if isinstance(expr, EllipsisType):
          return analysis, Ellipsis

        if not (expr.kind in self._kinds):
          analysis.errors.append(InvalidExprKind(obj))
          return analysis, Ellipsis

        return analysis, LocatedValue.new(expr, area=obj.area)
      elif self._force_expr:
        return LanguageServiceAnalysis(errors=[InvalidExpr(obj)]), Ellipsis

    return self._type.analyze(obj, context)

class PotentialExprType(Type):
  def __init__(self, obj_type: Type, /, *, dynamic: Optional[bool] = None, literal: bool = True, static: Optional[bool] = None):
    self._type = obj_type

    both = (dynamic is None) and (static is None)
    assert dynamic or static or both

    self._dynamic = dynamic or both
    self._literal = literal
    self._static = static or both

  def analyze(self, obj, /, context):
    eval_depth = max(context.eval_depth, (2 if self._dynamic else 0), (1 if self._static else 0)) if not context.symbolic else 0

    if isinstance(obj, str) and (not context.symbolic):
      assert isinstance(obj, LocatedString)
      expr_result = PythonExpr.parse(obj)

      if expr_result:
        analysis, expr = expr_result

        if isinstance(expr, EllipsisType):
          return analysis, Ellipsis

        match expr.kind:
          case PythonExprKind.Dynamic if self._dynamic:
            before_depth = 1
          case PythonExprKind.Static if self._static:
            before_depth = 0
          case _:
            analysis.errors.append(InvalidExprKind(obj))
            return analysis, Ellipsis

        expr_object = PythonExprObject(expr, self._type, depth=(eval_depth - before_depth - 1), envs=context.envs_list[before_depth].copy())
        analysis += expr_object.analyze()
        return analysis, ValueAsPythonExpr.new(expr_object, depth=before_depth)

    if self._literal:
      return self._type.analyze(obj, context.update(eval_depth=eval_depth))
    else:
      return LanguageServiceAnalysis(errors=[InvalidExpr(obj)]), Ellipsis

class ExprType(LiteralOrExprType):
  def __init__(self, obj_type: Optional[Type] = None, /, *, dynamic: bool = False, expr_type: Optional[Type] = None, field: bool = False, static: bool = False):
    super().__init__(obj_type, dynamic=dynamic, expr_type=expr_type, field=field, static=static, _force_expr=True)

class QuantityType(Type):
  def __init__(
    self,
    unit: Optional[Unit | str],
    *,
    allow_inverse: bool = False,
    allow_nil: bool = False,
    min: Optional[Quantity] = None,
    max: Optional[Quantity] = None
  ):
    self._allow_inverse = allow_inverse # TODO: Add implementation
    self._allow_nil = allow_nil
    self._max = max
    self._min = min
    self._unit: Unit = ureg.Unit(unit)

  def analyze(self, obj, /, context):
    if self._allow_nil and (
      ((not context.symbolic) and (obj == "nil")) or
      (context.symbolic and (obj.value == None))
    ):
      result = LocatedValue.new(None, area=obj.area)
      return LanguageServiceAnalysis(), ValueAsPythonExpr.new(result, depth=context.eval_depth)

    if isinstance(obj.value, str): # and (not context.symbolic):
      assert isinstance(obj, LocatedString)

      try:
        value = ureg.Quantity(obj.value)
      except pint.errors.UndefinedUnitError:
        return LanguageServiceAnalysis(errors=[UnknownUnitError(obj)]), Ellipsis
      except (pint.PintError, TokenError):
        return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(obj, Quantity)]), Ellipsis
      except Exception:
        return LanguageServiceAnalysis(errors=[UnknownUnitError(obj)]), Ellipsis
    elif isinstance(obj.value, (float, int)):
      value = ureg.Quantity(obj.value)
    else:
      value = obj.value

    analysis, result = self.check(value, self._unit, target=obj)

    if isinstance(result, EllipsisType):
      return analysis, Ellipsis

    if ((self._min is not None) and (result.value < self._min)) or \
      ((self._max is not None) and (result.value > self._max)):
      analysis.errors.append(OutOfBoundsQuantityError(result, self._min, self._max))
      return analysis, Ellipsis

    return analysis, ValueAsPythonExpr.new(result, depth=context.eval_depth)

  @staticmethod
  def check(value: Quantity, unit: Unit, *, target: LocatedValue):
    match value:
      case Quantity() if value.check(unit): # type: ignore
        return LanguageServiceAnalysis(), LocatedValue.new(value.to(unit), area=target.area)
      case Quantity(dimensionless=True):
        return LanguageServiceAnalysis(errors=[MissingUnitError(target, unit)]), Ellipsis
      case Quantity():
        return LanguageServiceAnalysis(errors=[InvalidUnitError(target, unit)]), Ellipsis
      case _:
        return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(target, Quantity)]), Ellipsis

class ArbitraryQuantityType:
  def analyze(self, obj, context):
    try:
      quantity = ureg.Quantity(obj.value)
    except pint.errors.UndefinedUnitError:
      return LanguageServiceAnalysis(errors=[UnknownUnitError(obj)]), Ellipsis
    except pint.PintError:
      return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(obj, pint.Quantity)]), Ellipsis

    return LanguageServiceAnalysis(), LocatedValue.new(quantity, area=obj.area)


class BoolType(PrimitiveType):
  def __init__(self):
    super().__init__(bool)

class IntType(Type):
  def __init__(self, *, mode: Literal['any', 'positive', 'positive_or_null'] = 'any'):
    self._mode = mode

  def analyze(self, obj, /, context):
    analysis, raw_result = PrimitiveType(int).analyze(obj, context.update(eval_depth=0))

    if isinstance(raw_result, EllipsisType):
      return analysis, Ellipsis

    result = cast(LocatedValue[int], raw_result)

    if (result.value < 0) and (self._mode != 'any'):
      return LanguageServiceAnalysis(errors=[InvalidIntegerError(obj)]), Ellipsis
    elif (result.value == 0) and (self._mode == 'positive'):
      return LanguageServiceAnalysis(errors=[InvalidIntegerError(obj)]), Ellipsis
    else:
      return LanguageServiceAnalysis(), ValueAsPythonExpr.new(result, depth=context.eval_depth)

class StrType(PrimitiveType):
  def __init__(self):
    super().__init__(str)

class IdentifierType(Type):
  def __init__(self, *, allow_leading_digit: bool = False):
    super().__init__()

    self._allow_leading_digit = allow_leading_digit

  def analyze(self, obj, /, context):
    analysis, obj_new = StrType().analyze(obj, context)

    if isinstance(obj_new, EllipsisType):
      return analysis, Ellipsis

    try:
      is_identifier(obj_new, allow_leading_digit=self._allow_leading_digit)
    except LocatedError:
      analysis.errors.append(InvalidIdentifierError(obj))
      return analysis, Ellipsis

    return analysis, obj_new

class EnumType(Type):
  def __init__(self, *variants: int | str):
    is_int = [isinstance(variant, int) for variant in variants]

    self._all_int = all(is_int)
    self._any_int = any(is_int)
    self._variants = variants

  def analyze(self, obj, /, context):
    analysis = LanguageServiceAnalysis()

    if not obj.value in self._variants:
      if self._any_int:
        int_analysis, int_result = PrimitiveType(int).analyze(obj, context.update(eval_depth=0))

        if not isinstance(int_result, EllipsisType) and (int_result.value in self._variants):
          return (analysis + int_analysis), ValueAsPythonExpr.new(int_result, depth=context.eval_depth)
        elif self._all_int:
          analysis += int_analysis

      analysis.errors.append(InvalidEnumValueError(obj))
      return analysis, Ellipsis
    else:
      return analysis, ValueAsPythonExpr.new(obj, depth=context.eval_depth)


class UnionType(Type):
  def __init__(self, variant: Type, /, *variants: Type):
    self._variants = [variant, *variants]

  def analyze(self, obj, context):
    analysis = LanguageServiceAnalysis()

    for variant in self._variants:
      analysis, result = variant.analyze(obj, context)

      if not isinstance(result, EllipsisType):
        return analysis, result

    return analysis, Ellipsis



# class PathInDirType(Type):
#   def __init__(self, dir_path: Path):
#     self._dir_path = dir_path

#   def analyze(self, obj, /, context):
#     analysis, result = PathType().analyze(obj, context)

#     if isinstance(result, EllipsisType):
#       return analysis, Ellipsis

#     new_path = self._dir_path / result.value

#     if not new_path.is_relative_to(self._dir_path):
#       analysis.errors.append(PathOutsideDirError(result, self._dir_path))
#       return analysis, Ellipsis

#     return analysis, LocatedValueContainer(new_path, result.area)


# class WritableDataRefType(Type):
#   def __init__(self, *, text: Optional[bool] = None):
#     self._type = UnionType(
#       BindingType(),
#       FileRefType(text=text)
#     )


class BindingType(Type):
  def analyze(self, obj, /, context):
    from ..fiber.binding import Binding

    if not isinstance(obj, str):
      return LanguageServiceAnalysis(errors=[InvalidPrimitiveError(obj, str)]), Ellipsis

    assert isinstance(obj, LocatedString)
    expr_result = PythonExpr.parse(obj)

    if not expr_result:
      return LanguageServiceAnalysis(errors=[InvalidExpr(obj)]), Ellipsis

    analysis, expr = expr_result

    if isinstance(expr, EllipsisType):
      return analysis, Ellipsis

    if expr.kind != PythonExprKind.Binding:
      analysis.errors.append(InvalidExprKind(obj))
      return analysis, Ellipsis

    binding_analysis, binding = Binding.parse(expr.contents, expr.tree, envs=context.envs_list[1], write_env=context.envs_list[0][0])
    analysis += binding_analysis

    if isinstance(binding, EllipsisType):
      return analysis, Ellipsis

    return analysis, ValueAsPythonExpr.new(binding, depth=1)
    # return analysis, ValueAsPythonExpr.new(LocatedValue.new(binding, area=obj.area), depth=1)

class KVDictType(Type):
  def __init__(self, key_type: Type, value_type: Optional[Type] = None, /):
    self._key_type = key_type if value_type else StrType()
    self._value_type = value_type or key_type

  def analyze(self, obj, /, context):
    analysis, result = PrimitiveType(dict).analyze(obj, context)

    if isinstance(result, EllipsisType):
      return analysis, Ellipsis

    assert isinstance(obj, LocatedDict)

    if isinstance(obj, ReliableLocatedDict):
      analysis.folds.append(LanguageServiceFoldingRange(obj.fold_range))
      analysis.selections.append(LanguageServiceSelection(obj.full_area.enclosing_range()))

    result = dict()

    for key, value in obj.items():
      key_analysis, key_result = self._key_type.analyze(key, context)
      value_analysis, value_result = self._value_type.analyze(value, context)

      if not (isinstance(key_result, EllipsisType) or isinstance(value_result, EllipsisType)):
        result[key_result] = value_result

      analysis += key_analysis
      analysis += value_analysis

    located_result = obj.transform(result) if isinstance(obj, ReliableLocatedDict) else LocatedDict(result, obj.area)
    return analysis, KVDictValueAsPythonExpr.new(located_result, depth=context.eval_depth)

K = TypeVar('K', bound=LocatedValue)
V = TypeVar('V', bound=LocatedValue)

class KVDictValueAsPythonExpr(Evaluable[LocatedDict[K, V]], Generic[K, V]):
  def __init__(self, value: LocatedDict[Evaluable[K], Evaluable[V]], /, *, depth: int):
    self._depth = depth
    self._value = value

  def evaluate(self, stack):
    analysis = LanguageServiceAnalysis()
    failure = False
    result = dict[Evaluable[K] | K, Evaluable[V] | V]()

    # TODO: Same as lists
    for key, value in self._value.items():
      key_analysis, key_result = key.evaluate(stack)
      value_analysis, value_result = value.evaluate(stack)

      analysis += key_analysis
      analysis += value_analysis

      if not isinstance(key_result, EllipsisType) and not isinstance(value_result, EllipsisType):
        result[key_result] = value_result
      else:
        failure = True

    return analysis, self.new(LocatedDict(result, self._value.area), depth=(self._depth - 1)) if not failure else Ellipsis

  def __repr__(self):
    return f"{self.__class__.__name__}({self._value!r}, depth={self._depth})"

  @classmethod
  def new(cls, value: LocatedDict, /, *, depth: int):
    return cls(value, depth=depth) if depth > 0 else value

class EvaluableContainerType(Type):
  def __init__(self, obj_type: Type, /, depth: int):
    self._depth = depth
    self._type = obj_type

  def analyze(self, obj, /, context):
    return self._type.analyze(obj, context.update(eval_depth=self._depth))

class DeferredAnalysisType(Type):
  def __init__(self, obj_type: Type, /, *, depth: int):
    self._depth = depth
    self._type = obj_type

  def analyze(self, obj, /, context):
    return (LanguageServiceAnalysis(), ValueAsPythonExpr.new(DeferredAnalysisValueAsPythonExpr(obj, self._type, depth=(context.eval_depth - self._depth)), depth=self._depth)) if self._depth > 0 else self._type.analyze(obj, context)

class DeferredAnalysisValueAsPythonExpr(Evaluable):
  def __init__(self, obj: LocatedValue, obj_type: Type, /, *, depth: int):
    self._depth = depth
    self._type = obj_type
    self._obj = obj

  def evaluate(self, context):
    from ..fiber.parser import AnalysisContext
    return self._type.analyze(self._obj, AnalysisContext(eval_context=context, eval_depth=self._depth, symbolic=True))

class HasAttrType(Type):
  def __init__(self, attribute: str, /):
    self._attribute = attribute

  def analyze(self, obj, /, context):
    analysis, result = PrimitiveType(object).analyze(obj, context)

    if isinstance(result, EllipsisType):
      return analysis, Ellipsis

    if not hasattr(result, self._attribute):
      analysis.errors.append(MissingAttributeError(obj, self._attribute))
      return analysis, Ellipsis

    return analysis, result

class DataTypeType(Type):
  def analyze(self, obj, /, context):
    if isinstance(obj.value, np.dtype):
      return LanguageServiceAnalysis(), obj

    analysis, str_result = StrType().analyze(obj, context.update(eval_depth=0))

    if isinstance(str_result, EllipsisType):
      return analysis, Ellipsis

    try:
      value = np.dtype(obj.value)
    except TypeError as e:
      analysis.errors.append(InvalidDataTypeError(obj, e.args[0]))
      return analysis, Ellipsis
    else:
      return analysis, ValueAsPythonExpr.new(LocatedValue.new(value, obj.area), depth=context.eval_depth)


__all__ = [
  'AnyType',
  'Attribute',
  'BoolType',
  'DataTypeType',
  'DeferredAnalysisType',
  'DictType',
  'EllipsisType',
  'EvaluableContainerType',
  'HasAttrType',
  'IntType',
  'KVDictType',
  'ListType',
  'PotentialExprType',
  'PrimitiveType',
  'RecordType',
  'StrType',
  'Type',
]