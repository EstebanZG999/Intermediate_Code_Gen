from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from .tac_ir import Label

@dataclass
class LoopLabels:
    continue_lbl: Label
    break_lbl: Label

@dataclass
class LabelManager:
    prefix: str = "L"
    _counter: int = 0
    _loop_stack: List[LoopLabels] = field(default_factory=list)

    def new(self, prefix: Optional[str] = None) -> Label:
        p = prefix if prefix is not None else self.prefix
        name = f"{p}{self._counter}"
        self._counter += 1
        return Label(name)

    def push_loop(self, continue_lbl: Label, break_lbl: Label) -> None:
        self._loop_stack.append(LoopLabels(continue_lbl, break_lbl))

    def pop_loop(self) -> None:
        assert self._loop_stack, "loop stack underflow"
        self._loop_stack.pop()

    @property
    def current_continue(self) -> Label:
        assert self._loop_stack, "no active loop"
        return self._loop_stack[-1].continue_lbl

    @property
    def current_break(self) -> Label:
        assert self._loop_stack, "no active loop"
        return self._loop_stack[-1].break_lbl