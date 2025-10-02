import textwrap
from program.ir.tac_builder import TACBuilder
from tests.ir.util_tac import normalize_tac

def test_add_assign_and_print_snapshot():
    b = TACBuilder()
    t2 = b.gen_expr_literal(2)
    t3 = b.gen_expr_literal(3)
    s  = b.gen_expr_add(t2, t3)
    b._assign(b.gen_expr_var("x").value, s)
    b.gen_stmt_print(b.gen_expr_var("x"))
    got = normalize_tac(b.tac.dump())
    expected = normalize_tac(textwrap.dedent('''
        t0 := 2
        t1 := 3
        + t0, t1 -> t2
        x := t2
        print x
    '''))
    assert got == expected

def test_logical_and_short_circuit_shape():
    b = TACBuilder()
    x = b.gen_expr_var("x")
    def rhs(): return b.gen_expr_var("y")
    r = b.gen_expr_and(x, rhs)
    txt = b.tac.dump()
    assert "if x goto" in txt
    assert ":= 1" in txt or ":= 0" in txt