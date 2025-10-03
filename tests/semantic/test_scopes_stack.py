import program.semantic.typesys as T
from program.semantic.scopes import GlobalScope, ScopeStack, FunctionScope, ClassScope

def test_stack_helpers_for_function_and_class():
    st = ScopeStack(GlobalScope())
    fs = st.push_function(return_type=T.VOID, name="f")
    assert isinstance(fs, FunctionScope)
    cs = st.push_class("C")
    assert isinstance(cs, ClassScope)
    st.pop(); st.pop()
    assert st.current.kind == "global"
