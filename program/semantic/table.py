from semantic.scopes import Scope, ScopeStack
from semantic.symbols import Symbol, VarSymbol, ParamSymbol, FuncSymbol, ClassSymbol

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
