from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Iterable
from program.semantic.symbols import Symbol

@dataclass
class Scope:
    """Ámbito semántico: mantiene un mapa nombre->símbolo y referencia al padre."""
    kind: str  # 'global' | 'class' | 'function' | 'block'
    parent: Optional['Scope'] = None
    symbols: Dict[str, Symbol] = field(default_factory=dict)
    owner: Symbol | None = None   


    def define(self, sym: Symbol) -> bool:
        """
        Intenta registrar 'sym' en este scope.
        Retorna False si el nombre ya existe en ESTE scope (redeclaración).
        """
        if sym.name in self.symbols:
            return False
        self.symbols[sym.name] = sym
        return True

    def resolve(self, name: str) -> Optional[Symbol]:
        """
        Busca el símbolo por 'name' en este scope y, si no está, recorre la cadena de padres.
        """
        s: Optional[Scope] = self
        while s is not None:
            if name in s.symbols:
                return s.symbols[name]
            s = s.parent
        return None

    # Utilidades
    def __contains__(self, name: str) -> bool:
        return name in self.symbols

    def items(self) -> Iterable[tuple[str, Symbol]]:
        return self.symbols.items()

# Subclases útiles

class GlobalScope(Scope):
    def __init__(self) -> None:
        super().__init__('global', None)

class BlockScope(Scope):
    def __init__(self, parent: Scope) -> None:
        super().__init__('block', parent)

class FunctionScope(Scope):
    def __init__(self, parent: Scope, return_type, name: str | None = None) -> None:
        super().__init__('function', parent)
        self.func_name = name
        self.return_type = return_type
        self.has_return = False  

class ClassScope(Scope):
    def __init__(self, parent: Scope, class_name: str) -> None:
        super().__init__('class', parent)
        self.class_name = class_name

# Pila de scopes

class ScopeStack:
    """
    Pila de scopes para usar desde el TypeChecker.
    """
    def __init__(self, root: Optional[Scope] = None):
        self.stack: list[Scope] = [root] if root else []

    @property
    def current(self) -> Scope:
        if not self.stack:
            raise RuntimeError("ScopeStack vacío: asegúrate de push(global) antes de usarlo.")
        return self.stack[-1]

    def push(self, kind: str) -> Scope:
        """Crea un hijo del tipo solicitado ('global'|'block'|'function'|'class'|otro)."""
        parent = self.stack[-1] if self.stack else None
        if kind == 'global':
            s = GlobalScope()
        elif kind == 'block':
            s = BlockScope(parent)  # type: ignore[arg-type]
        elif kind == 'function':
            s = FunctionScope(parent, return_type=None)  # type: ignore[arg-type]
        elif kind == 'class':
            s = ClassScope(parent, class_name="<anon>")  # type: ignore[arg-type]
        else:
            s = Scope(kind, parent)
        self.stack.append(s)
        return s
    
    def push_child(self, child: Scope) -> Scope:
        """Permite reutilizar un Scope preconstruido como hijo del actual, evitando ciclos."""
        # Si ya es el current, no lo dupliques
        if self.stack and child is self.current:
            return child

        new_parent = self.current if self.stack else None
        # Evitar ciclo directo: parent == child
        if child is new_parent:
            return child

        child.parent = self.current if self.stack else None
        self.stack.append(child)
        return child

    def push_function(self, return_type, name: str | None = None) -> FunctionScope:
        # Usa el padre ANTES de apilar para evitar ciclos o mirar al scope equivocado
        parent = self.current if self.stack else None
        fs = FunctionScope(parent, return_type, name)
        self.stack.append(fs)
        fs.owner = parent.resolve(name) if (name and parent) else None
        return fs

    def push_class(self, class_name: str) -> ClassScope:
        parent = self.current if self.stack else None
        cs = ClassScope(parent, class_name)
        self.stack.append(cs)
        cs.owner = parent.resolve(class_name) if parent else None
        return cs

    def pop(self) -> Scope:
        if not self.stack:
            raise RuntimeError("Pop en ScopeStack vacío.")
        return self.stack.pop()

    def depth(self) -> int:
        return len(self.stack)

    def inside(self, kind: str) -> bool:
        for s in reversed(self.stack):
            if s.kind == kind:
                return True
        return False