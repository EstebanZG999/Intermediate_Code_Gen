import pytest
from program.ir.tac_builder import TACBuilder, ExprResult, Const, Var

def test_func_and_class_field():
    tb = TACBuilder()

    # Simula función f(a,b)
    tb.gen_fn_begin("f")
    a = ExprResult(Var("a"))
    b = ExprResult(Var("b"))
    t = tb.gen_expr_add(a, b)
    tb.gen_stmt_return(t)
    tb.gen_fn_end("f")

    # Simula función g()
    tb.gen_fn_begin("g")
    o = Var("o")
    tb.gen_field_store(o, 2, ExprResult(Const(7)))
    val = tb.gen_field_load(o, 2)
    tb.gen_stmt_print(val)
    tb.gen_fn_end("g")

    print(tb.tac)
