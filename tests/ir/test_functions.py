from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Var, Const

def test_function_begin_end_and_returns():
    tb = TACBuilder()

    # function f(a,b) { return a+b; }
    tb.gen_fn_begin("f")
    add = tb.gen_expr_add(ExprResult(Var("a")), ExprResult(Var("b")))
    tb.gen_stmt_return(add)         # ret con valor
    tb.gen_fn_end("f")              # también emite ret None (convención); ok doble salida canónica

    # function g() { print(1); }  (sin return explícito => ret None al final)
    tb.gen_fn_begin("g")
    tb.gen_stmt_print(ExprResult(Const(1)))
    tb.gen_fn_end("g")

    print(tb.tac)
