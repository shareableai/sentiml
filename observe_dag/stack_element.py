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

from observe_dag.inclusion import should_include_module
from observe_dag.protocols import CodeProtocol, FrameProtocol
from observe_dag.slugify import slugify

class NotIncludedError(BaseException):
    pass

@dataclass
class StackElement:
    description: CodeProtocol
    module: str
    parent: Optional[StackElement] = field(default=None)
    arguments: dict[str, str] = field(default_factory=dict)
    caller_name: Optional[str] = field(default=None)
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

        argument_names = frame.f_code.co_varnames
        arguments = {}
        caller_name = None
        caller_docs = None
        for argument_name in argument_names:
            if argument_name in frame.f_locals:
                argument = frame.f_locals[argument_name]
                if argument_name in ['self', 'cls']:
                    try:
                        if hasattr(argument, '__qualname__'):
                            caller_name = argument.__qualname__
                        elif hasattr(argument, '__name__'):
                            caller_name = argument.__name__
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
                    # TODO: Still missing lots of default args for things like the Preprocessing fn in DETR.
                    signature = inspect.signature(initial_referent)
                    arguments = {
                        k: v.default
                        for k, v in signature.parameters.items()
                        if v.default is not inspect.Parameter.empty
                    } | arguments

        return StackElement(
            frame.f_code,
            module.__name__ if module is not None else "UnknownModule",
            parent,
            arguments,
            caller_name,
            caller_docs,
            list(),
        )
