from tests.semantic.util import compile_source

def test_assign_valid_and_invalid():
    code = """
    let x: integer = 5;
    x = 6;            // ok
    """
    rep, _ = compile_source(code)
    assert not rep.has_errors(), f"Esperaba sin errores, obtuve: {[str(e) for e in rep]}"

    code_bad = """
    let x: integer = 5;
    x = "hola";       // error: string -> integer
    """
    rep, _ = compile_source(code_bad)
    assert rep.has_errors(), "Asignación incompatible debía fallar"

def test_const_decl_initialization_ok():
    # Validamos que una const bien declarada no produce errores.
    code = """
    const C: integer = 10;
    """
    rep, _ = compile_source(code)
    assert not rep.has_errors(), f"Const con inicialización debía ser válida: {[str(e) for e in rep]}"
