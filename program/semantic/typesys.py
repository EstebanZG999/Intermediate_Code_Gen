from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


T_INTEGER = "integer"
T_STRING  = "string"
T_BOOLEAN = "boolean"
T_NULL    = "null"
T_VOID    = "void"


@dataclass(frozen=True)
class Type:
    name: str
    def __str__(self) -> str: return self.name
    def is_primitive(self) -> bool:
        return self.name in {T_INTEGER, T_STRING, T_BOOLEAN, T_NULL, T_VOID}

@dataclass(frozen=True)
class ArrayType(Type):
    elem: Type | None = None
    dims: int = 1
    def __str__(self) -> str:
        if self.elem is None:
            return "[]"
        return f"{self.elem}{'[]'*self.dims}"

@dataclass(frozen=True)
class FunctionType(Type):
    params: Tuple[Type, ...] = ()
    ret: Type = Type(T_VOID)
    def __str__(self) -> str:
        args = ", ".join(str(p) for p in self.params)
        return f"({args}) -> {self.ret}"

@dataclass(frozen=True)
class ClassType(Type):
    pass


INTEGER = Type(T_INTEGER)
STRING  = Type(T_STRING)
BOOLEAN = Type(T_BOOLEAN)
NULL    = Type(T_NULL)
VOID    = Type(T_VOID)


def is_numeric(t: Type) -> bool:
    return t.name == T_INTEGER

def is_boolean(t: Type) -> bool: return t.name == T_BOOLEAN
def is_string(t: Type) -> bool:  return t.name == T_STRING

def equal_types(a: Optional[Type], b: Optional[Type]) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, ArrayType) and isinstance(b, ArrayType):
        return a.dims == b.dims and equal_types(a.elem, b.elem)
    return a.name == b.name

def make_array(elem: Type, dims: int = 1) -> ArrayType:
    return ArrayType(name=f"{elem.name}{'[]'*dims}", elem=elem, dims=dims)

def make_fn(params: list[Type], ret: Type) -> FunctionType:
    return FunctionType(name="function", params=tuple(params), ret=ret)


def can_assign(dst: Optional[Type], src: Optional[Type]) -> bool:
    if dst is None or src is None:
        return False
    if equal_types(dst, src):
        return True
    if isinstance(dst, ArrayType) and src.name == T_NULL:
        return True
    if isinstance(dst, ClassType) and src.name == T_NULL:
        return True
    if is_string(dst) and src.name == T_NULL:
        return True
    return False

def arithmetic_type(lhs: Type, rhs: Type) -> Optional[Type]:
    """
    Reglas para operaciones aritméticas y concatenación:
      - integer (+,-,*,/) integer → integer
      - string + string → string
      - string + integer → string
      - integer + string → string
    """
    if is_numeric(lhs) and is_numeric(rhs):
        return INTEGER
    if is_string(lhs) and is_string(rhs):
        return STRING
    if is_string(lhs) and is_numeric(rhs):
        return STRING
    if is_numeric(lhs) and is_string(rhs):
        return STRING
    return None

def logical_type(lhs: Type, rhs: Type) -> Optional[Type]:
    if is_boolean(lhs) and is_boolean(rhs):
        return BOOLEAN
    return None

def comparison_type(lhs: Type, rhs: Type) -> Optional[Type]:
    
    if equal_types(lhs, rhs):
        return BOOLEAN
    if is_numeric(lhs) and is_numeric(rhs):
        return BOOLEAN
    return None

def is_array(t: Type) -> bool:
    return isinstance(t, ArrayType)

def element_type(t: Type) -> Optional[Type]:
    return t.elem if isinstance(t, ArrayType) else None

def plus_type(lhs: Type, rhs: Type) -> Optional[Type]:
    """
    Reglas SOLO para '+':
      - integer + integer -> integer
      - string + string -> string
      - string + integer / integer + string -> string (concatenación)
    """
    if is_numeric(lhs) and is_numeric(rhs):
        return INTEGER
    if is_string(lhs) and is_string(rhs):
        return STRING
    if (is_string(lhs) and is_numeric(rhs)) or (is_numeric(lhs) and is_string(rhs)):
        return STRING
    return None

def arith_type(lhs: Type, rhs: Type) -> Optional[Type]:
    """
    Reglas para '-', '*', '/', '%': solo integer con integer.
    """
    if is_numeric(lhs) and is_numeric(rhs):
        return INTEGER
    return None

def relational_type(lhs: Type, rhs: Type) -> Optional[Type]:
    """
    Reglas para '<', '<=', '>', '>=': solo numéricos.
    """
    if is_numeric(lhs) and is_numeric(rhs):
        return BOOLEAN
    return None

def equality_type(lhs: Type, rhs: Type) -> Optional[Type]:
    """
    Reglas para '==' y '!=':
    - Tipos iguales -> boolean
    - (Opcional) null con referencias (array, class, string) -> boolean
    """
    if equal_types(lhs, rhs):
        return BOOLEAN
    # permitir comparar con null referencias válidas
    if (is_array(lhs) or isinstance(lhs, ClassType) or is_string(lhs)) and rhs == NULL:
        return BOOLEAN
    if (is_array(rhs) or isinstance(rhs, ClassType) or is_string(rhs)) and lhs == NULL:
        return BOOLEAN
    # numérico con numérico distintos no debería llegar aquí con equal_types,
    # pero por claridad:
    if is_numeric(lhs) and is_numeric(rhs):
        return BOOLEAN
    return None