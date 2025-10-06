from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Const, Var

def test_if_else_and_or():
    tb = TACBuilder()

    # if (a && b) { print(1); } else { print(0); }
    a = ExprResult(Var("a"))
    b = ExprResult(Var("b"))
    cond = tb.gen_expr_and(a, lambda: b)

    def then_cb(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Const(1)))

    def else_cb(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Const(0)))

    tb.gen_stmt_if(cond, then_cb, else_cb)

    # x = (c || d)
    c = ExprResult(Var("c"))
    d = ExprResult(Var("d"))
    res_or = tb.gen_expr_or(c, lambda: d)
    tb._assign(Var("x"), res_or)

    print(tb.tac)
