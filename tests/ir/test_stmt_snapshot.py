# tests/ir/test_stmt_snapshot.py
import pytest
from program.ir.tac_builder import TACBuilder, ExprResult, Const, Var

def test_while_with_print(snapshot):
    """
    while (1) { print(42); }
    """
    tb = TACBuilder()
    tb.gen_stmt_while(
        cond_cb=lambda self: ExprResult(Const(1)),
        body_cb=lambda self: self.gen_stmt_print(ExprResult(Const(42)))
    )
    snapshot.assert_match(tb.tac.dump(), "while_with_print.tac")


def test_do_while(snapshot):
    """
    do { print(1); } while (0);
    """
    tb = TACBuilder()
    tb.gen_stmt_do_while(
        body_cb=lambda self: self.gen_stmt_print(ExprResult(Const(1))),
        cond_cb=lambda self: ExprResult(Const(0))
    )
    snapshot.assert_match(tb.tac.dump(), "do_while_false_once.tac")


def test_for_loop(snapshot):
    """
    for (i=0; i<3; i++) { print(i); }
    """
    tb = TACBuilder()

    def init(self):
        self._assign(Var("i"), ExprResult(Const(0)))

    def cond(self):
        return self.gen_expr_rel("<", ExprResult(Var("i")), ExprResult(Const(3)))

    def step(self):
        self._assign(Var("i"), self.gen_expr_add(ExprResult(Var("i")), ExprResult(Const(1))))

    def body(self):
        self.gen_stmt_print(ExprResult(Var("i")))

    tb.gen_stmt_for(init, cond, step, body)
    snapshot.assert_match(tb.tac.dump(), "for_loop.tac")


def test_break_and_continue(snapshot):
    """
    while (1) { print(10); break; }
    """
    tb = TACBuilder()

    def cond(self):
        return ExprResult(Const(1))

    def body(self):
        self.gen_stmt_print(ExprResult(Const(10)))
        self.gen_stmt_break()

    tb.gen_stmt_while(cond_cb=cond, body_cb=body)
    snapshot.assert_match(tb.tac.dump(), "while_break.tac")


def test_switch(snapshot):
    """
    switch (2) {
      case 1: print(100);
      case 2: print(200);
      default: print(999);
    }
    """
    tb = TACBuilder()

    def case1(self):
        self.gen_stmt_print(ExprResult(Const(100)))

    def case2(self):
        self.gen_stmt_print(ExprResult(Const(200)))

    def default(self):
        self.gen_stmt_print(ExprResult(Const(999)))

    tb.gen_stmt_switch(
        ExprResult(Const(2)),
        [(1, case1), (2, case2)],
        default_cb=default
    )
    snapshot.assert_match(tb.tac.dump(), "switch_example.tac")


def test_return(snapshot):
    """
    return 123;
    """
    tb = TACBuilder()
    tb.gen_stmt_return(ExprResult(Const(123)))
    snapshot.assert_match(tb.tac.dump(), "return_value.tac")


def test_return_void(snapshot):
    """
    return;
    """
    tb = TACBuilder()
    tb.gen_stmt_return()
    snapshot.assert_match(tb.tac.dump(), "return_void.tac")
