from tests.semantic.util import compile_source

def test_conditions_must_be_boolean():
    code = """
    let x: integer = 1;
    if (x) { }           // error: cond no booleana
    while (x + 1) { }    // error: cond no booleana
    """
    rep, _ = compile_source(code)
    assert rep.has_errors(), "Condiciones no booleanas debían fallar"

def test_break_continue_context_and_dead_code():
    code = """
    break;                // error: fuera de bucle
    continue;             // error: fuera de bucle
    function f(): integer {
      return 1;
      let x: integer = 2;  // dead code (señalado por checker si está implementado)
    }
    """
    rep, _ = compile_source(code)
    assert rep.has_errors(), "break/continue fuera de bucle y/o dead code debían fallar"
