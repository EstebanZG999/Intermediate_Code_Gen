from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Const, Var

def test_params_call_return():
    tb = TACBuilder()

    # simula: t = add(a,b); print(t);
    a = ExprResult(Var("a"))
    b = ExprResult(Var("b"))
    call_res = tb.gen_call("add", [a, b])
    tb.gen_stmt_print(call_res)

    # y una llamada cuyo resultado se ignora: log(1);
    tb.gen_stmt_expr(tb.gen_call("log", [ExprResult(Const(1))]))

    print(tb.tac)
