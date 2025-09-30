from tests.semantic.util import compile_source

def test_function_decl_and_return_ok():
    code = """
    function suma(a: integer, b: integer): integer {
      return a + b;
    }
    let z: integer = 0;   // sin llamadas; el objetivo es validar la declaración/return
    """
    rep, _ = compile_source(code)
    assert not rep.has_errors(), f"Esperaba sin errores, got: {[str(e) for e in rep]}"

def test_return_type_enforced_and_return_outside():
    code_bad = """
    function g(a: integer): integer {
      return "hola";  // error: string no es integer
    }
    return 5;         // error: return fuera de función
    """
    rep, _ = compile_source(code_bad)
    assert rep.has_errors(), "Return incompatible y return fuera de función debían fallar"
