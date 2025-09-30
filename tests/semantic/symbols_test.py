from program.semantic.symbols import VarSymbol, ParamSymbol, FuncSymbol, ClassSymbol
from program.semantic.typesys import INTEGER, STRING, make_fn

def test_varsymbol():
    x = VarSymbol(name="x", type=INTEGER, is_const=False, is_initialized=True)
    assert x.name == "x" and x.type == INTEGER and not x.is_const and x.is_initialized

def test_funcsymbol():
    ftype = make_fn([INTEGER, STRING], INTEGER)
    p0 = ParamSymbol(name="a", type=INTEGER, index=0)
    p1 = ParamSymbol(name="b", type=STRING, index=1)
    f = FuncSymbol(name="foo", type=ftype, params=(p0, p1))
    assert f.type.ret == INTEGER and len(f.params) == 2

def test_classsymbol_minimal():

    c = ClassSymbol(name="Point", type=STRING)
    assert c.name == "Point"
    assert c.category == "class"

    if hasattr(c, "fields"):
        c.fields["x"] = VarSymbol(name="x", type=INTEGER)
        assert "x" in c.fields
