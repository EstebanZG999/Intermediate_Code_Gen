# program/semantic/table.py
from program.semantic.scopes import Scope, ScopeStack
from program.semantic.symbols import Symbol, VarSymbol, ParamSymbol, FuncSymbol, ClassSymbol
from program.runtime.activation_record import ActivationRecord
from program.ir.tac_ir import Addr
from typing import Optional, List, Union

def print_scope(scope: Scope, indent=0):
    pad = "  " * indent
    print(f"{pad}Scope ({scope.kind})")

    for name, sym in scope.items():
        row = f"{pad}- {sym.category:<8} {sym.name:<12} : {sym.type}"

        # Mostrar línea y columna si existen
        if hasattr(sym, "line") and hasattr(sym, "col"):
            row += f" (line {getattr(sym, 'line', 0)}, col {getattr(sym, 'col', 0)})"

        # NUEVO: región/offset si aplica o si es global const/variable
        region = getattr(sym, "region", None)

        # Si es una constante o variable global, marcar manualmente como global
        if region is None and scope.kind == "global" and sym.category in ("const", "variable"):
            region = "global"

        if region is not None:
            row += f"   [region={region}"
            offset = getattr(sym, "offset", None)
            if offset is not None:
                row += f", offset={offset}"
            row += "]"

        print(row)

        # --- Funciones ---
        if isinstance(sym, FuncSymbol):
            def _fmt_off(off):
                return f"{'+' if off is not None and off >= 0 else ''}{off}"

            # Parámetros
            for p in sym.params:
                extra = ""
                if getattr(p, "offset", None) is not None:
                    extra = f" [param@fp{_fmt_off(p.offset)}]"
                print(f"{pad}    param {p.name} : {p.type} (index {p.index}){extra}")

            # ActivationRecord (si existe)
            ar = getattr(sym, "activation_record", None)
            if ar is not None:
                fs = getattr(ar, "frame_size", 2 + (1 if ar.has_this else 0) + ar.params_size + ar.locals_size)
                print(f"{pad}    AR: has_this={ar.has_this}, params_size={ar.params_size}, locals_size={ar.locals_size}, frame_size={fs}")

            # Funciones anidadas (si las hubiera)
            if hasattr(sym, "nested"):
                for nname, nsym in sym.nested.items():
                    print(f"{pad}    nested function {nname} : {nsym.type}")
                    for np in nsym.params:
                        print(f"{pad}        param {np.name} : {np.type} (index {np.index})")

        # --- Clases ---
        if isinstance(sym, ClassSymbol):
            for fname, fsym in sym.fields.items():
                extra = ""
                if getattr(fsym, "field_offset", None) is not None:
                    extra = f" [field_offset={fsym.field_offset}]"
                print(f"{pad}    field {fname} : {fsym.type}{extra}")

            for mname, msym in sym.methods.items():
                print(f"{pad}    method {mname} : {msym.type}")
                ar = getattr(msym, "activation_record", None)
                if ar is not None:
                    fs = getattr(ar, "frame_size", 2 + (1 if ar.has_this else 0) + ar.params_size + ar.locals_size)
                    print(f"{pad}        AR: has_this={ar.has_this}, params_size={ar.params_size}, locals_size={ar.locals_size}, frame_size={fs}")



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

    def resolve(self, name: str):
        return self.scope_stack.current.resolve(name)

    def current_function(self) -> Optional[FuncSymbol]:
        """
        Busca el scope más interno de tipo 'function' y devuelve su FuncSymbol real.
        """
        for i in range(len(self.scope_stack.stack)-1, -1, -1):
            s: Scope = self.scope_stack.stack[i]
            if getattr(s, "kind", None) == "function":
                fname = getattr(s, "func_name", None)
                if not fname:
                    continue
                # busca hacia arriba el símbolo de función
                for j in range(i, -1, -1):
                    up: Scope = self.scope_stack.stack[j]
                    sym = up.resolve(fname)
                    if isinstance(sym, FuncSymbol):
                        return sym
        return None

    def function_ar(self, func_sym: FuncSymbol) -> Optional[ActivationRecord]:
        return func_sym.activation_record

    def addr_of(self, var_or_name: Union[VarSymbol, str]) -> Addr:
        """
        Devuelve Addr(fp, offset) de una variable local/param/this.
        Acepta símbolo o nombre.
        """
        if isinstance(var_or_name, str):
            sym = self.resolve(var_or_name)
            if not isinstance(sym, VarSymbol):
                raise RuntimeError(f"{var_or_name} no es VarSymbol")
        else:
            sym = var_or_name

        if sym.offset is None:
            raise RuntimeError(f"Variable {sym.name} no tiene offset asignado.")

        return Addr("fp", int(sym.offset))

    def params_in_order(self, func_sym: FuncSymbol) -> List[str]:
        return [p.name for p in func_sym.params]

    def _resolve_class(self, type_name: str) -> Optional[ClassSymbol]:
        if not self.scope_stack.stack:
            return None
        root: Scope = self.scope_stack.stack[0]
        sym = root.resolve(type_name)
        return sym if isinstance(sym, ClassSymbol) else None

    def field_offset(self, type_name: str, field_name: str) -> int:
        cls = self._resolve_class(type_name)
        if cls is None:
            raise KeyError(f"Clase no encontrada: {type_name}")

        if field_name in cls.fields and cls.fields[field_name].field_offset is not None:
            return int(cls.fields[field_name].field_offset)

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
