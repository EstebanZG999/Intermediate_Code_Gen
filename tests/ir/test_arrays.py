from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Const, Var

def test_array_load_store():
    tb = TACBuilder()

    # a[i] = 7; x = a[i];
    i = ExprResult(Var("i"))
    tb.gen_array_store(Var("a"), i, ExprResult(Const(7)))
    val = tb.gen_array_load(Var("a"), i)
    tb.gen_stmt_print(val)

    print(tb.tac)
