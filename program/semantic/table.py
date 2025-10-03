from program.semantic.scopes import Scope, ScopeStack
from program.semantic.symbols import Symbol, VarSymbol, ParamSymbol, FuncSymbol, ClassSymbol
from program.runtime.activation_record import ActivationRecord
from program.ir.tac_ir import Addr
from typing import Optional, List

def print_scope(scope: Scope, indent=0):
    pad = "  " * indent
    print(f"{pad}Scope ({scope.kind})")

    for name, sym in scope.items():
        row = f"{pad}- {sym.category:<8} {sym.name:<12} : {sym.type}"
        if hasattr(sym, "line") and hasattr(sym, "col"):
            row += f" (line {getattr(sym, 'line', 0)}, col {getattr(sym, 'col', 0)})"
        print(row)

        if isinstance(sym, FuncSymbol):
            for p in sym.params:
                print(f"{pad}    param {p.name} : {p.type} (index {p.index})")
            if hasattr(sym, "nested"):
                for nname, nsym in sym.nested.items():
                    print(f"{pad}    nested function {nname} : {nsym.type}")
                    for np in nsym.params:
                        print(f"{pad}        param {np.name} : {np.type} (index {np.index})")

        if isinstance(sym, ClassSymbol):
            for fname, fsym in sym.fields.items():
                print(f"{pad}    field {fname} : {fsym.type}")
            for mname, msym in sym.methods.items():
                print(f"{pad}    method {mname} : {msym.type}")

def print_symbol_table(stack: ScopeStack):
    if not stack.stack:
        print(" No hay scopes registrados en la tabla de símbolos.")
        return
    print("\nTabla de Símbolos")
    print("====================")
    root = stack.stack[0]
    print_scope(root, 0)

class SymbolTable:
    def __init__(self, scope_stack: ScopeStack):
        self.scope_stack: ScopeStack = scope_stack

    def current_function(self) -> Optional[FuncSymbol]:
        """
        Devuelve la función 'dueña' del scope actual.
        Ajusta esta lógica a tu implementación real de Scope/ScopeStack.
        """
        if not self.scope_stack.stack:
            return None
        cur: Scope = self.scope_stack.stack[-1]
        return getattr(cur, "function", None)

    def function_ar(self, func_sym: FuncSymbol) -> Optional[ActivationRecord]:
        return func_sym.activation_record

    def addr_of(self, var_sym: VarSymbol) -> Addr:
        if var_sym.offset is None:
            raise RuntimeError(f"Variable {var_sym.name} no tiene offset asignado.")
        # Base 'fp' por convención; ajusta si tu Addr necesita otro tipo/base
        return Addr("fp", var_sym.offset)

    def params_in_order(self, func_sym: FuncSymbol) -> List[str]:
        return [p.name for p in func_sym.params]

    def _resolve_class(self, type_name: str) -> Optional[ClassSymbol]:
        if not self.scope_stack.stack:
            return None
        root: Scope = self.scope_stack.stack[0]
        sym = root.resolve(type_name)
        return sym if isinstance(sym, ClassSymbol) else None

    def field_offset(self, type_name: str, field_name: str) -> int:
        """
        Devuelve el offset acumulado del campo en la jerarquía:
          (#campos en todas las bases) + índice local en la clase que lo declara.
        Si el campo ya tiene field_offset precalculado en esa clase, lo usamos.
        """
        cls = self._resolve_class(type_name)
        if cls is None:
            raise KeyError(f"Clase no encontrada: {type_name}")

        # Si en la clase actual ya está precalculado
        if field_name in cls.fields and cls.fields[field_name].field_offset is not None:
            return int(cls.fields[field_name].field_offset)

        # Construye la cadena base→…→derivada
        chain: list[ClassSymbol] = []
        cur = cls
        while isinstance(cur, ClassSymbol):
            chain.append(cur)
            if getattr(cur, "base", None):
                cur = self._resolve_class(cur.base)
            else:
                break
        chain = list(reversed(chain))

        total = 0
        for c in chain:
            if field_name in c.fields:
                names = list(c.fields.keys())
                return total + names.index(field_name)
            total += len(c.fields)

        raise KeyError(f"Campo {field_name} no existe en jerarquía de {type_name}")

