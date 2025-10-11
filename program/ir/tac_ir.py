# program/ir/tac_ir.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Union

class Operand:
    def __str__(self) -> str:
        return self.__repr__()

@dataclass(frozen=True)
class Const(Operand):
    value: Union[int, float, bool, str, None]
    def __repr__(self) -> str:
        if isinstance(self.value, str):
            return f'"{self.value}"'
        if self.value is None:
            return "null"
        return str(self.value).lower() if isinstance(self.value, bool) else str(self.value)

@dataclass(frozen=True)
class Var(Operand):
    name: str
    def __repr__(self) -> str:
        return self.name

@dataclass(frozen=True)
class Temp(Operand):
    name: str
    def __repr__(self) -> str:
        return self.name

@dataclass(frozen=True)
class Addr(Operand):
    base: Union[Operand, str]
    offset: int
    def __repr__(self) -> str:
        base = str(self.base)
        sign = "+" if self.offset >= 0 else ""
        return f"[{base}{sign}{self.offset}]"

@dataclass(frozen=True)
class Label(Operand):
    name: str
    def __repr__(self) -> str:
        return self.name

@dataclass
class Quadruple:
    op: str
    a: Optional[Operand] = None
    b: Optional[Operand] = None
    dst: Optional[Operand] = None

    def __repr__(self) -> str:
        if self.op == "label":
            return f"{self.dst}:"
        if self.op == "goto":
            return f"goto {self.dst}"
        if self.op == "ifgoto":
            return f"if {self.a} goto {self.dst}"
        if self.op == "param":
            return f"param {self.a}"
        if self.op == "call":
            return (f"call {self.a}, nargs={self.b}"
                    if self.dst is None
                    else f"call {self.a}, nargs={self.b} -> {self.dst}")
        if self.op == "ret":
            return f"ret {self.a}"
        if self.op == "print":
            return f"print {self.a}"
        if self.op == ":=":
            return f"{self.dst} := {self.a}"
        if self.op == "load":
            return f"load {self.a} -> {self.dst}"
        if self.op == "store":
            # *** clave: imprime la dirección en 'b' ***
            return f"store {self.a}, {self.b}"
        if self.op == "alloc":
            return f"alloc {self.a} -> {self.dst}"
        if self.op == "alloc_array":
            return f"alloc_array {self.a} -> {self.dst}"
        if self.op == "len":
            return f"len {self.a} -> {self.dst}"
        # Los de 3 operandos (addr_field/index, +, -, etc.)
        return f"{self.op} {self.a}, {self.b} -> {self.dst}"

@dataclass
class TACProgram:
    code: List[Quadruple] = field(default_factory=list)

    def emit(self, op: str, a: Optional[Operand] = None, b: Optional[Operand] = None, dst: Optional[Operand] = None) -> Quadruple:
        q = Quadruple(op, a, b, dst)
        self.code.append(q)
        return q

    def label(self, lbl: Label) -> Quadruple:
        return self.emit("label", dst=lbl)

    def __iter__(self):
        return iter(self.code)

    def __len__(self) -> int:
        return len(self.code)

    def dump(self) -> str:
        return "\n".join(repr(q) for q in self.code)
