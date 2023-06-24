from __future__ import annotations

import functools
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
    tracked_class_name: Optional[str] = field(default=None)
    signature: Optional[str] = field(default=None)
    arguments: dict[str, str] = field(default_factory=dict)
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
            "arguments": self.arguments,
            "tracked_class_name": self.tracked_class_name,
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
        arguments = {}
        readable_caller_name = None
        caller_name = None
        caller_docs = None
        signature = None
        tracked_class_name = None
        for argument_name in possible_argument_names:
            if argument_name in frame.f_locals:
                argument = frame.f_locals[argument_name]
                if argument_name in ['self', 'cls']:
                    try:
                        if hasattr(argument, '__observer_class_name__'):
                            tracked_class_name = argument.__observer_class_name__
                        if hasattr(argument, '__qualname__'):
                            caller_name = argument.__qualname__
                        elif hasattr(argument, '__name__'):
                            caller_name = argument.__name__
                        if readable_caller_name is None:
                            readable_caller_name = get_caller_name(argument)                        
                        if hasattr(argument, '__doc__') and getattr(argument, '__doc__') is not None:
                            caller_docs = argument.__doc__
                    except BaseException:
                        pass
                if sys.getsizeof(argument) < 512:
                    try:
                        arguments[argument_name] = str(argument)
                    except BaseException:
                        pass
        if 'self' in arguments or 'cls' in arguments:
            referents = list(gc.get_referrers(frame.f_code))
            if len(referents) > 0:
                initial_referent = next(iter(referents))
                if isinstance(initial_referent, FunctionType):
                    signature = inspect.signature(initial_referent)
                    arguments =  {
                        k: v.default if v.default is not inspect.Parameter.empty else None
                        for k, v in signature.parameters.items()
                        if v.default is not inspect.Parameter.empty
                    } | arguments

        return StackElement(
            frame.f_code,
            module.__name__ if module is not None else "UnknownModule",
            parent,
            tracked_class_name,
            signature,
            arguments,
            caller_name,
            readable_caller_name,
            caller_docs,
            list(),
        )
