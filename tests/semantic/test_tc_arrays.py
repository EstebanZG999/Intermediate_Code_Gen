from tests.semantic.util import compile_source

def test_array_index_and_element_type():
    code_ok = """
    let a: integer[] = [1, 2, 3];
    let x: integer = a[0];    // ok
    """
    rep, _ = compile_source(code_ok)
    assert not rep.has_errors(), f"Esperaba sin errores, got: {[str(e) for e in rep]}"

    code_bad = """
    let a: integer[] = [1, 2, 3];
    let s: string = a[0];   // error: integer no asignable a string
    let y = a["0"];         // error: índice no es integer
    let z = 10[0];          // error: indexar algo no-array
    """
    rep, _ = compile_source(code_bad)
    assert rep.has_errors(), "Índices inválidos / tipos incompatibles debían fallar"

def test_multidim_arrays_basics():
    code = """
    let m: integer[][] = [[1,2],[3,4]];
    let t: integer[] = m[0];     // fila es integer[]
    let v: integer = t[1];       // elemento es integer
    """
    rep, _ = compile_source(code)
    assert not rep.has_errors(), f"Esperaba sin errores, got: {[str(e) for e in rep]}"
