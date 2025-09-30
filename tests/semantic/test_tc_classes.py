from tests.semantic.util import compile_source

def test_class_fields_and_constructor_decl_ok():
    code = """
    class Point {
      let x: integer;
      let y: integer;
      function constructor(x: integer, y: integer) {
        this.x = x; this.y = y;
      }
      function touch(): void { /* no-op */ }
    }
    // No instanciamos ni llamamos métodos; solo validamos la declaración de la clase
    let p: Point;   // declaración de variable de tipo clase
    """
    rep, _ = compile_source(code)
    assert not rep.has_errors(), f"Esperaba sin errores, got: {[str(e) for e in rep]}"

def test_class_invalid_member_access_and_this_outside():
    code_bad = """
    class A {
      let v: integer;
      function constructor(v: integer) { this.v = v; }
      function foo(): integer { return this.v; }
    }
    this.v = 5;    // error: this fuera de clase
    a.nope;        // 'a' ni está declarado; además, campo inexistente si se declarara
    """
    rep, _ = compile_source(code_bad)
    assert rep.has_errors(), "Errores de this fuera de clase y acceso inválido debían fallar"