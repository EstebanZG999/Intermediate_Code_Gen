import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
from antlr4 import InputStream, CommonTokenStream
from antlr4.tree.Trees import Trees
import pandas as pd

from program.CompiscriptLexer import CompiscriptLexer
from program.CompiscriptParser import CompiscriptParser
from program.semantic.type_checker import TypeChecker
from program.semantic.error_reporter import ErrorReporter
from program.semantic.scopes import GlobalScope
from program.semantic.symbols import FuncSymbol, ClassSymbol, VarSymbol
from program.semantic.table import SymbolTable
from program.ir.tac_builder import TACBuilder
from program.ir.tac_gen import TACGen


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --- Graphviz helpers ---
def _node_label(parser, node) -> str:
    label = Trees.getNodeText(node, parser.ruleNames)
    return label.replace('"', r'\"')

def build_parse_tree_dot(parser, tree, max_nodes: int = 2000) -> str:
    lines = [
        "digraph ParseTree {",
        'rankdir=TB;',
        'node [shape=box, fontname="Helvetica"];'
    ]
    counter = 0
    overflow = False

    def add_node(n):
        nonlocal counter, overflow
        if counter >= max_nodes:
            overflow = True
            return None
        my_id = f"n{counter}"
        counter += 1
        lines.append(f'{my_id} [label="{_node_label(parser, n)}"];')
        for i in range(n.getChildCount()):
            ch = n.getChild(i)
            cid = add_node(ch)
            if cid is not None:
                lines.append(f"{my_id} -> {cid};")
        return my_id

    add_node(tree)
    if overflow:
        warn_id = f"n{counter}"
        lines.append(f'{warn_id} [label="... (árbol truncado en {max_nodes} nodos)"];')
    lines.append("}")
    return "\n".join(lines)


def compile_code(source: str):
    input_stream = InputStream(source)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)

    tree = parser.program()

    reporter = ErrorReporter()
    checker = TypeChecker(reporter)
    checker.visit(tree)

    return reporter, checker.scopes, checker.symtab, parser, tree

def render_scopes(scopes):
    """
    Renderiza todos los scopes detectados durante la compilación
    en formato de tablas Streamlit.
    """

    for scope in scopes.stack:
        st.subheader(f"Scope: {scope.kind}")

        rows = []
        for _, sym in scope.items():
            # --- Asignar región lógica ---
            region = getattr(sym, "region", None)

            # Si es constante, variable o función global → marcar manualmente
            if region is None and scope.kind == "global" and sym.category in ("const", "variable", "function"):
                region = "global"

            # Si es parámetro con offset, marcar como param
            if region is None and isinstance(sym, VarSymbol) and getattr(sym, "offset", None) is not None:
                region = "param"

            # Construir fila base
            row = {
                "Category": sym.category,
                "Name": sym.name,
                "Type": str(sym.type),
                "Region": region,
                "Addr": _fmt_addr(sym),
                "Offset": getattr(sym, "offset", None),
                "Line": getattr(sym, "line", 0),
                "Col": getattr(sym, "col", 0),
            }
            rows.append(row)

            # --- Parámetros si es función ---
            if isinstance(sym, FuncSymbol):
                for p in sym.params:
                    rows.append({
                        "Category": "param",
                        "Name": p.name,
                        "Type": str(p.type),
                        "Region": "param" if getattr(p, "offset", None) is not None else None,
                        "Addr": _fmt_addr(p),
                        "Offset": getattr(p, "offset", None),
                        "Line": getattr(p, "line", 0),
                        "Col": getattr(p, "col", 0),
                    })


                # Activation Record (si existe)
                if getattr(sym, "activation_record", None):
                    ar = sym.activation_record
                    with st.expander(f"AR de {sym.name}"):
                        st.write(
                            f"**has_this**={ar.has_this}, "
                            f"**params_size**={ar.params_size}, "
                            f"**locals_size**={ar.locals_size}, "
                            f"**frame_size**={ar.frame_size}"
                        )

            # --- Si es clase, listar campos y métodos ---
            if isinstance(sym, ClassSymbol):
                if getattr(sym, "fields", None):
                    st.markdown(f"**Campos de `{sym.name}`**")
                    st.table([{
                        "Name": fname,
                        "Type": str(fsym.type),
                        "field_offset": getattr(fsym, "field_offset", None),
                    } for fname, fsym in sym.fields.items()])

                if getattr(sym, "methods", None):
                    st.markdown(f"**Métodos de `{sym.name}`**")
                    st.table([{
                        "Name": mname,
                        "Type": str(msym.type),
                        "Params": ", ".join(f"{p.name}: {p.type}" for p in msym.params),
                    } for mname, msym in sym.methods.items()])

                    # AR por método
                    for mname, msym in sym.methods.items():
                        if getattr(msym, "activation_record", None):
                            ar = msym.activation_record
                            with st.expander(f"AR de {sym.name}.{mname}"):
                                st.write(
                                    f"**has_this**={ar.has_this}, "
                                    f"**params_size**={ar.params_size}, "
                                    f"**locals_size**={ar.locals_size}, "
                                    f"**frame_size**={ar.frame_size}"
                                )

        # Mostrar tabla final de símbolos del scope
        if rows:
            df = pd.DataFrame(rows)
            st.table(df)



def get_global_scope(scopes):
    # Devuelve el primer scope de tipo 'global' (o el 0 si no lo encuentra)
    for s in scopes.stack:
        if s.kind == "global":
            return s
    return scopes.stack[0] if scopes.stack else None


def render_symbols(scopes, st):
    g = get_global_scope(scopes)
    if not g:
        st.warning("No hay scope global disponible.")
        return

    # ---- Funciones globales
    funcs = [(name, sym) for name, sym in g.items() if isinstance(sym, FuncSymbol)]
    if funcs:
        st.subheader("Funciones globales")
        for name, sym in funcs:
            st.markdown(f"**{name}** — `{sym.type}`")
            # parámetros de la función global
            if sym.params:
                st.table([{
                    "param": p.name,
                    "index": p.index,
                    "type": str(p.type)
                } for p in sym.params])
            # funciones anidadas
            if hasattr(sym, "nested") and sym.nested:
                st.markdown("↳ Funciones anidadas")
                st.table([{
                    "name": n,
                    "type": str(ns.type),
                    "params": ", ".join(f"{p.name}: {p.type}" for p in ns.params)
                } for n, ns in sym.nested.items()])
    else:
        st.info("No hay funciones globales.")

def _fmt_addr(sym):
    off = getattr(sym, "offset", None)
    reg = getattr(sym, "region", None)

    # Asegurar que region esté actualizado
    if reg is None and hasattr(sym, "category"):
        if sym.category in ("const", "variable", "function"):
            reg = "global"

    # --- Mostrar dirección simbólica para globales ---
    if reg == "global":
        return "[gp]"  # global pointer simbólico

    # --- Direcciones para locales, parámetros y this ---
    if reg in ("param", "local", "this") and off is not None:
        try:
            val = float(off)
            sign = "+" if val >= 0 else ""
            return f"[fp{sign}{int(val)}]"
        except (ValueError, TypeError):
            pass

    # Si no aplica, devolver "-" en lugar de vacío (evita <NA>)
    return "-"





st.set_page_config(page_title="Compiscript IDE", layout="wide")

st.title("Compiscript Mini-IDE")
st.write("Escribe tu programa en Compiscript y compílalo con un clic.")

default_code = """// Programa de ejemplo
const PI: integer = 314;
let saludo: string = "Hola mundo!";

function externo(x: integer): integer {
  function interno(y: integer): integer {
    return x + y;
  }
  return interno(5);
}

let resultado: integer = externo(10);
print("Resultado: " + resultado);
"""
code = st.text_area("Editor", default_code, height=400)


# Controles
col_a, col_b, col_c = st.columns([1,1,2])
with col_a:
    do_compile = st.button("Compile 🚀", key="compile_main")
with col_b:
    show_tree = st.checkbox("Árbol sintáctico", value=True)
    show_tac  = st.checkbox("Generar TAC", value=True)
with col_c:
    max_nodes = st.slider("Límite de nodos del árbol", min_value=200, max_value=5000, value=2000, step=100)

if do_compile:
    reporter, scopes, symtab, parser, tree = compile_code(code)

    if reporter.has_errors():
        st.error(" Errores semánticos encontrados:")
        for e in reporter:
            st.write(f"- {e}")
    else:
        st.success(" Compilación completada sin errores")

    if show_tree:
        st.subheader("Árbol sintáctico")
        dot = build_parse_tree_dot(parser, tree, max_nodes=max_nodes)
        st.graphviz_chart(dot, use_container_width=True)
    
    # Generación de TAC (solo si no hay errores)
    if show_tac and not reporter.has_errors():
        st.subheader("TAC")
        # Usamos la tabla de símbolos a partir de 'scopes'
        builder = TACBuilder()
        gen     = TACGen(symtab, builder)
        gen.visit(tree)
        st.code(builder.tac.dump(), language="text")

    # Tabla de símbolos por scope
    render_scopes(scopes)


    # mostrar parámetros de cada función declarada en el scope global
    # ---- Mostrar clases y sus miembros (en el global)
    global_scope = scopes.stack[0]
    for name, sym in global_scope.items():
        if isinstance(sym, ClassSymbol):
            st.markdown(f"### Clase `{name}`")

            if getattr(sym, "fields", None):
                st.markdown("**Campos**")
                st.table([{
                    "Nombre": fname,
                    "Tipo": str(fsym.type),
                    "Línea": getattr(fsym, "line", 0),
                    "Col": getattr(fsym, "col", 0),
                } for fname, fsym in sym.fields.items()])

            if getattr(sym, "methods", None):
                st.markdown("**Métodos**")
                st.table([{
                    "Nombre": mname,
                    "Tipo": str(msym.type),
                    "Parámetros": ", ".join(f"{p.name}: {p.type}" for p in msym.params),
                    "Línea": getattr(msym, "line", 0),
                    "Col": getattr(msym, "col", 0),
                } for mname, msym in sym.methods.items()])
