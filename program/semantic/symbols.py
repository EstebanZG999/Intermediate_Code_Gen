# program/semantic/symbols.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, TYPE_CHECKING
from .typesys import Type, FunctionType
if TYPE_CHECKING:
    # evitas import circular en tiempo de import
    from program.semantic.scopes import Scope
    from program.runtime.activation_record import ActivationRecord

# Convenciones de región
REG_GLOBAL = "global"
REG_PARAM  = "param"
REG_LOCAL  = "local"
REG_THIS   = "this"
REG_FIELD  = "field"
REG_CONST  = "const"  # si quieres distinguir const como región, aunque normalmente es categoría

@dataclass
class Symbol:
    name: str
    type: Type
    category: str = "unknown"   # variable, const, param, func, class
    line: int = 0               # línea de declaración
    col: int = 0                # columna de declaración
    # metadata de ejecución
    region: Optional[str] = None      # global|param|local|this|field|None
    offset: Optional[int] = None      # relativo a FP si aplica (param/local/this)

@dataclass
class VarSymbol(Symbol):
    is_const: bool = False
    is_initialized: bool = False
    # Para campos de clase:
    field_offset: Optional[int] = None  # offset dentro de objeto (this-relativo)

    def __init__(
        self,
        name,
        type,
        is_const: bool = False,
        is_initialized: bool = False,
        line: int = 0,
        col: int = 0,
        region: Optional[str] = None,
        offset: Optional[int] = None,
        field_offset: Optional[int] = None,
    ):
        super().__init__(
            name, type,
            category=("const" if is_const else "variable"),
            line=line, col=col,
            region=region, offset=offset
        )
        self.is_const = is_const
        self.is_initialized = is_initialized
        self.field_offset = field_offset

@dataclass
class ParamSymbol(Symbol):
    index: int = 0

    def __init__(
        self,
        name,
        type,
        index,
        line: int = 0,
        col: int = 0,
        offset: Optional[int] = None
    ):
        super().__init__(
            name, type,
            category="param",
            line=line, col=col,
            region=REG_PARAM, offset=offset
        )
        self.index = index

@dataclass
class FuncSymbol(Symbol):
    type: FunctionType
    params: Tuple[ParamSymbol, ...] = field(default_factory=tuple)
    closure_scope: Optional['Scope'] = None
    activation_record: Optional['ActivationRecord'] = None  # RA asociado

    def __init__(
        self,
        name,
        type: FunctionType,
        params=(),
        line: int = 0,
        col: int = 0,
        closure_scope: Optional['Scope'] = None,
        activation_record: Optional['ActivationRecord'] = None,
    ):
        super().__init__(
            name, type,
            category="function",
            line=line, col=col,
            region=REG_GLOBAL, offset=None
        )
        self.params = tuple(params)
        self.closure_scope = closure_scope
        self.activation_record = activation_record

@dataclass
class ClassSymbol(Symbol):
    fields: Dict[str, VarSymbol] = field(default_factory=dict)
    methods: Dict[str, FuncSymbol] = field(default_factory=dict)
    base: Optional[str] = None

    def __init__(self, name, type, line: int = 0, col: int = 0):
        super().__init__(name, type, category="class", line=line, col=col, region=REG_GLOBAL, offset=None)
        self.fields = {}
        self.methods = {}
        self.base = None
