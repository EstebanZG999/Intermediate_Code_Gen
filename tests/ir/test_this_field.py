from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Const

def test_this_field():
    tb = TACBuilder()

    # this.z = 9; print(this.z);
    tb.gen_this_field_store(2, ExprResult(Const(9)))  # offset 2 como en el ejemplo
    v = tb.gen_this_field_load(2)
    tb.gen_stmt_print(v)

    print(tb.tac)
