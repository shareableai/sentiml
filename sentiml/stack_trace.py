from __future__ import annotations

import inspect
import operator
import pathlib
from dataclasses import dataclass
from functools import reduce
from typing import Optional

from sentiml.default_libraries import (
    LIBS_THAT_ARENT_RELEVANT,
)
from sentiml.inclusion import should_include_module
from sentiml.protocols import CodeProtocol
from sentiml.stack_element import StackElement
from sentiml.trace_id import TraceID
from sentiml.tracking_type import TrackingType


class NodeStack:
    def __init__(self, stack_type: TrackingType, existing_node_ids: Optional[list[int]] = None, max_depth: int = 6):
        if existing_node_ids is None:
            self._existing_node_ids: list[int] = []
        else:
            self._existing_node_ids = existing_node_ids
        self._stack_type: TrackingType = stack_type
        self._nodes: list[StackElement] = list()
        self._node_lookup: dict[int, StackElement] = dict()  # Node Hash => Node
        self._max_node_depth = max_depth

    def _include_node(self, node: StackElement) -> bool:
        is_included = (
                node is not None
                and should_include_module(node.module)
                and node.description.co_name is not None
                and not any([lib in f"{node.module}.{node.description.co_name}" for lib in LIBS_THAT_ARENT_RELEVANT])
                and (
                        node.description.co_name in ["__init__", "__call__"]
                        or not node.description.co_name.startswith("__")
                )
                and NodeStack.node_depth(node) <= self._max_node_depth
        )
        return is_included

    @staticmethod
    def _node_depth(node: Optional[StackElement], depth: int = 0) -> int:
        if node is None:
            return depth
        return NodeStack._node_depth(node.parent, depth + 1)

    @staticmethod
    def node_depth(node: StackElement) -> int:
        return NodeStack._node_depth(node, 0)

    def add_node(self, node: StackElement) -> None:
        if not self._include_node(node):
            return None
        self._node_lookup[hash(node)] = node
        if node.parent is None:
            self._nodes.append(node)
        else:
            try:
                node_parent = self._node_lookup[hash(node.parent)]
                node_parent.add_child(node)
            except KeyError:
                while node.parent is not None and (not self._include_node(node.parent)):
                    # Keep searching up the tree until a valid parent is found.
                    node.parent = node.parent.parent
                self.add_node(node.parent)
                self.add_node(node)

    def _root_dir(self) -> pathlib.Path:
        root_dir = (
                TraceID.root_dir()
                / str(self._stack_type)
        )
        root_dir.mkdir(parents=True, exist_ok=True)
        return root_dir

    def _dump_node(self, node: StackElement) -> None:
        target_node = self._root_dir() / node.name()
        if not target_node.exists():
            with open(target_node, "w") as f:
                node.dumps(f)
        for child_node in node.children:
            self._dump_node(child_node)

    def dump(self) -> None:
        with open(self._root_dir() / 'trace.txt', 'w') as f:
            f.writelines(self._write_stack())
        for child_node in self._nodes:
            self._dump_node(child_node)
        # TODO: Save all libraries within tracked Nodes.

    def _write_node(self, node: StackElement, level: int = 0) -> list[str]:
        trace = []
        if level <= self._max_node_depth:
            trace.append(f"[{level}]" + "".join(["\t" * (level + 1)]) + f"{node}\n")
            previous_node = None
            for child_node in node.children:
                if child_node != previous_node:
                    trace = trace + self._write_node(child_node, level + 1)
                    previous_node = child_node
        return trace

    def _write_stack(self) -> list[str]:
        return reduce(operator.add, [self._write_node(n) for n in self._nodes], [])


@dataclass
class FnDescription:
    module: str
    name: str
    source: Optional[str]

    def __hash__(self):
        return hash(tuple([self.module, self.name, self.source]))

    @staticmethod
    def from_code(code: CodeProtocol) -> FnDescription:
        module = inspect.getmodule(code)
        try:
            src = inspect.getsource(code)
        except OSError:
            src = None
        return FnDescription(
            module.__name__ if module is not None else "UnknownModule",
            code.co_name,
            src,
        )
