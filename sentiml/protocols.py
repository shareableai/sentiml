from __future__ import annotations

import typing


class CodeProtocol(typing.Protocol):
    co_argcount: int  # number of arguments
    co_code: str  # raw compiled bytecode
    co_cellvars: typing.Tuple[str, ...]  # names of cell variables
    co_consts: typing.Tuple[typing.Any, ...]  # Consts in bytecode
    co_filename: str  # Name of file in which this code object was created
    co_firstlineno: int  # No. first line in python source code
    co_flags: typing.Any  # Bitmap of CO_flags
    co_lnotab: typing.Mapping[
        int, int
    ]  # Encoding mapping of line numbers to bytecode indices
    co_freevars: typing.Tuple[str, ...]  # names of free variables
    co_posonlyargcount: int  # Positional only arguments
    co_kwonlyargcount: int  # Keyword only arguments
    co_name: str  # Name with which this code object was defined
    co_qualname: str  # Fully qualified name
    co_names: typing.Tuple[str, ...]  # Names other than arguments & function locals
    co_nlocals: int  # Number of local variables
    co_stacksize: int
    co_varnames: typing.Tuple[str, ...]  # Names of arguments & local variables


class FrameProtocol(typing.Protocol):
    f_back: typing.Optional[
        FrameProtocol
    ]  # Next outer frame object - this frame's caller
    f_builtins: typing.Any  # Builtins namespace seen by this frame
    f_code: CodeProtocol  # Code Object being executed
    f_lasti: int  # Index of last attempted instruction
    f_lineno: int  # Current Line Number
    f_locals: typing.Dict[str, typing.Any]  # Local namespace seen by this frame
    f_trace: typing.Optional  # Tracing function for this frame
    f_trace_lines: bool
    f_trace_opcodes: bool
