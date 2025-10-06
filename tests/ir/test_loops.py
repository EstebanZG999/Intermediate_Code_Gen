from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Const, Var

def test_while_do_while_for_break_continue():
    tb = TACBuilder()

    # while (flag) { print(i); continue; }
    def w_cond(bd): return ExprResult(Var("flag"))
    def w_body(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Var("i")))
        bd.gen_stmt_continue()
    tb.gen_stmt_while(w_cond, w_body)

    # do { print(j); break; } while (cond)
    def d_body(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Var("j")))
        bd.gen_stmt_break()
    def d_cond(bd): return ExprResult(Var("cond"))
    tb.gen_stmt_do_while(d_body, d_cond)

    # for (i=i; i<10; i=i+1) { print(i); }
    def f_init(bd: TACBuilder):
        bd._assign(Var("i"), ExprResult(Var("i")))
    def f_cond(bd): 
        return bd.gen_expr_rel("<", ExprResult(Var("i")), ExprResult(Const(10)))
    def f_step(bd: TACBuilder):
        one = ExprResult(Const(1))
        nxt = bd.gen_expr_add(ExprResult(Var("i")), one)
        bd._assign(Var("i"), nxt)
    def f_body(bd: TACBuilder):
        bd.gen_stmt_print(ExprResult(Var("i")))
    tb.gen_stmt_for(f_init, f_cond, f_step, f_body)

    print(tb.tac)
