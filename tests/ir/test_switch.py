from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Const, Var

def test_switch_basic():
    tb = TACBuilder()
    expr = ExprResult(Var("k"))

    def case0(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Const(0)))

    def case1(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Const(1)))

    def dflt(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Const(9)))

    tb.gen_stmt_switch(expr, [(0, case0), (1, case1)], default_cb=dflt)
    print(tb.tac)
