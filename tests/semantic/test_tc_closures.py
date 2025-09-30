from tests.semantic.util import compile_source

def test_nested_functions_decl_ok():
    code = """
    function outer(): integer {
      let base: integer = 5;
      function inner(): integer {
        return base + 1;   // captura base
      }
      // sin llamadas; devolvemos una expresión equivalente
      return base + 1;
    }
    let r: integer = 0;   // no usamos outer() como expresión
    """
    rep, _ = compile_source(code)
    assert not rep.has_errors(), f"Esperaba sin errores, got: {[str(e) for e in rep]}"

def test_nested_functions_capture_undeclared():
    code_bad = """
    function outer(): integer {
      function inner(): integer {
        return base + 1;   // error: base no declarada en ningún entorno visible
      }
      return 0;
    }
    """
    rep, _ = compile_source(code_bad)
    assert rep.has_errors(), "Uso de identificador no resuelto en closure debía fallar"
