from __future__ import annotations

import functools
import uuid
import gc
import inspect
import json
import operator
import sys
from dataclasses import field, dataclass
from types import FunctionType
from typing import Optional, List, TextIO

from observer.inclusion import should_include_module
from observer.protocols import CodeProtocol, FrameProtocol
from observer.slugify import slugify

class NotIncludedError(BaseException):
    pass


def get_caller_name(argument) -> Optional[str]:
    if hasattr(argument, '__qualname__') and getattr(argument, '__qualname__') is not None:
        return argument.__qualname__
    elif hasattr(argument, '__name__') and getattr(argument, '__name__') is not None:
        return argument.__name__
    if hasattr(argument, '__class__'):
        if hasattr(argument.__class__, '__qualname__') and getattr(argument.__class__, '__qualname__') is not None:
            return argument.__class__.__qualname__
        elif hasattr(argument.__class__, '__name__') and getattr(argument.__class__, '__name__') is not None:
            return argument.__class__.__name__

@dataclass
class StackElement:
    description: CodeProtocol
    module: str
    parent: Optional[StackElement] = field(default=None)
    signature: Optional[str] = field(default=None)
    argument_values: dict[str, str] = field(default_factory=dict)
    tracked_argument_ids: dict[str, str] = field(default_factory=dict)
    caller_name: Optional[str] = field(default=None)
    readable_caller_name: Optional[str] = field(default=None)
    caller_docs: Optional[str] = field(default=None)
    children: List[StackElement] = field(default_factory=list)
    _hash: Optional[int] = field(default=None)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def _json_repr(self) -> dict:
        try:
            source = inspect.getsource(self.description)
        except BaseException:
            source = None
        return {
            "arguments": self.argument_values,
            "tracked_argument_ids": self.tracked_argument_ids,
            "signature": f"def {self.description.co_name}{self.signature}" if self.signature is not None else "",
            "caller_name": self.readable_caller_name,
            "caller_docs": self.caller_docs,
            "source": source
        }

    def dumps(self, file: TextIO) -> None:
        json.dump(self._json_repr(), file)

    def name(self) -> str:
        if self.caller_name is not None:
            return slugify(f"{self.caller_name}.{self.description.co_name}")
        else:
            return slugify(f"{self.module}.{self.description.co_name}")

    def __hash__(self) -> int:
        if self._hash is not None:
            return self._hash
        self._hash = hash(self.description) + functools.reduce(
            operator.add, map(hash, self.children), 0
        )
        return hash(self)

    def add_child(self, child: StackElement) -> None:
        self.children.append(child)

    def __str__(self) -> str:
        return f"{self.module}.{self.description.co_name}"

    @staticmethod
    @functools.lru_cache(maxsize=2**8)
    def from_frame(frame: FrameProtocol) -> StackElement:
        module = inspect.getmodule(frame.f_code)
        if not should_include_module(module.__name__ if hasattr(module, '__name__') else None):
            raise NotIncludedError
        if frame.f_back is not None:
            parent = StackElement.from_frame(frame.f_back)
        else:
            parent = None

        possible_argument_names = frame.f_code.co_varnames
        argument_values = {}
        tracked_argument_ids = {}
        readable_caller_name = None
        caller_name = None
        caller_docs = None
        signature = None
        for argument_name in possible_argument_names:
            if argument_name in frame.f_locals:
                argument_value = frame.f_locals[argument_name]
                # Present after track_class is called on the class.
                try:
                    if (tracked_argument_id := getattr(argument_value, '__observer_class_name__', None)) is not None:
                        tracked_argument_ids[argument_name] = tracked_argument_id
                except RecursionError:
                    try:
                        if (tracked_argument_id := argument_value.get('__observer_class_name__', None)) is not None:
                            tracked_argument_ids[argument_name] = tracked_argument_id
                    except BaseException:
                        continue
                if argument_name in ['self', 'cls']:
                    try:
                        if hasattr(argument_value, '__qualname__'):
                            caller_name = argument_value.__qualname__
                        elif hasattr(argument_value, '__name__'):
                            caller_name = argument_value.__name__
                        if readable_caller_name is None:
                            readable_caller_name = get_caller_name(argument_value)                        
                        if hasattr(argument_value, '__doc__') and getattr(argument_value, '__doc__') is not None:
                            caller_docs = argument_value.__doc__
                    except BaseException:
                        pass
                if sys.getsizeof(argument_value) < 512:
                    try:
                        argument_values[argument_name] = str(argument_value)
                    except BaseException:
                        pass
        if 'self' in argument_values or 'cls' in argument_values:
            referents = list(gc.get_referrers(frame.f_code))
            if len(referents) > 0:
                initial_referent = next(iter(referents))
                if isinstance(initial_referent, FunctionType):
                    signature = inspect.signature(initial_referent)
                    argument_values =  {
                        k: v.default if v.default is not inspect.Parameter.empty else None
                        for k, v in signature.parameters.items()
                        if v.default is not inspect.Parameter.empty
                    } | argument_values

        return StackElement(
            description=frame.f_code,
            module=module.__name__ if module is not None else "UnknownModule",
            parent=parent,
            signature=signature,
            argument_values=argument_values,
            tracked_argument_ids={k: str(v) for (k, v) in tracked_argument_ids.items()},
            caller_name=caller_name,
            readable_caller_name=readable_caller_name,
            caller_docs=caller_docs,
        )
