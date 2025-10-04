import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from antlr4 import InputStream, CommonTokenStream
from antlr4.tree.Trees import Trees
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic.type_checker import TypeChecker
from semantic.error_reporter import ErrorReporter
from semantic.scopes import GlobalScope
from semantic.symbols import FuncSymbol, ClassSymbol, VarSymbol
from ir.tac_builder import TACBuilder
from ir.tac_gen import TACGen
from semantic.table import SymbolTable

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

    return reporter, checker.scopes, parser, tree

def render_scope(scope, container, indent=0):
    pad = " " * (indent * 2)

    rows = []
    for _, sym in scope.items():
        rows.append({
            "Category": sym.category,
            "Name": sym.name,
            "Type": str(sym.type),
            "Line": getattr(sym, "line", 0),
            "Col": getattr(sym, "col", 0)
        })

        # Mostrar parámetros
        if isinstance(sym, FuncSymbol):
            for p in sym.params:
                rows.append({
                    "Category": "param",
                    "Name": p.name,
                    "Type": str(p.type),
                    "Line": getattr(p, "line", 0),
                    "Col": getattr(p, "col", 0)
                })
            # Mostrar funciones anidadas
            if hasattr(sym, "nested"):
                for nname, nsym in sym.nested.items():
                    rows.append({
                        "Category": "nested function",
                        "Name": nname,
                        "Type": str(nsym.type),
                        "Line": getattr(nsym, "line", 0),
                        "Col": getattr(nsym, "col", 0)
                    })
                    for np in nsym.params:
                        rows.append({
                            "Category": "param",
                            "Name": np.name,
                            "Type": str(np.type),
                            "Line": getattr(np, "line", 0),
                            "Col": getattr(np, "col", 0)
                        })

        # Mostrar clases
        if isinstance(sym, ClassSymbol):
            for fname, fsym in sym.fields.items():
                rows.append({
                    "Category": "field",
                    "Name": fname,
                    "Type": str(fsym.type),
                    "Line": getattr(fsym, "line", 0),
                    "Col": getattr(fsym, "col", 0)
                })
            for mname, msym in sym.methods.items():
                rows.append({
                    "Category": "method",
                    "Name": mname,
                    "Type": str(msym.type),
                    "Line": getattr(msym, "line", 0),
                    "Col": getattr(msym, "col", 0)
                })

    if rows:
        container.table(rows)

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
    reporter, scopes, parser, tree = compile_code(code)

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
        symtab  = SymbolTable(scopes)
        builder = TACBuilder()
        gen     = TACGen(symtab, builder)
        gen.visit(tree)
        tac_text = "\n".join(str(instr) for instr in builder.tac.code)
        st.code(tac_text, language="text")

    # Tabla de símbolos por scope
    for scope in scopes.stack:
        st.subheader(f"Scope: {scope.kind}")
        rows = [
            {
                "Category": sym.category,
                "Name": sym.name,
                "Type": str(sym.type),
                "Line": sym.line,
                "Col": sym.col
            }
            for _, sym in scope.items()
        ]
        st.table(rows)

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
