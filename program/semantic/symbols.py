from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, TYPE_CHECKING
from .typesys import Type, FunctionType
if TYPE_CHECKING:
    from .scopes import Scope

@dataclass
class Symbol:
    name: str
    type: Type
    category: str = "unknown"   # variable, const, param, func, class
    line: int = 0               # línea de declaración
    col: int = 0                # columna de declaración

@dataclass
class VarSymbol(Symbol):
    is_const: bool = False
    is_initialized: bool = False
    offset: int | None = None   
    def __init__(self, name, type, is_const=False, is_initialized=False, line=0, col=0):
        super().__init__(name, type, category="variable" if not is_const else "const", line=line, col=col)
        self.is_const = is_const
        self.is_initialized = is_initialized

@dataclass
class ParamSymbol(Symbol):
    index: int = 0
    def __init__(self, name, type, index, line=0, col=0):
        super().__init__(name, type, category="param", line=line, col=col)
        self.index = index

@dataclass
class FuncSymbol(Symbol):
    type: FunctionType
    params: Tuple[ParamSymbol, ...] = field(default_factory=tuple)
    closure_scope: Optional['Scope'] = None

    def __init__(self, name, type, params=(), line=0, col=0, closure_scope=None):
        super().__init__(name, type, category="function", line=line, col=col)
        self.params = tuple(params)
        self.closure_scope = closure_scope

@dataclass
class ClassSymbol(Symbol):
    fields: Dict[str, VarSymbol] = field(default_factory=dict)
    methods: Dict[str, FuncSymbol] = field(default_factory=dict)
    base: str | None = None
    def __init__(self, name, type, line=0, col=0):
        super().__init__(name, type, category="class", line=line, col=col)
