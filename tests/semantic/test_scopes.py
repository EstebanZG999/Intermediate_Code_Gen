import pytest

from program.semantic.scopes import Scope, GlobalScope, FunctionScope, ClassScope
from program.semantic.symbols import VarSymbol
import program.semantic.typesys as T

Int = T.INTEGER

def test_define_and_resolve_basic():
    g = Scope('global')
    assert g.define(VarSymbol('x', Int))
    assert g.resolve('x') is not None
    assert g.resolve('y') is None

def test_redeclaration_same_scope_fails():
    g = Scope('global')
    assert g.define(VarSymbol('x', Int)) is True
    assert g.define(VarSymbol('x', Int)) is False

def test_shadowing_in_child_scope_ok():
    g = Scope('global')
    inner = Scope('block', parent=g)

    assert g.define(VarSymbol('x', Int)) is True
    # sombra en el hijo: permitido
    assert inner.define(VarSymbol('x', Int)) is True

    # resolve en hijo encuentra primero el símbolo del hijo
    sym_child = inner.resolve('x')
    sym_parent = g.resolve('x')
    assert sym_child is not None and sym_parent is not None
    assert sym_child is not sym_parent

def test_cascading_resolution_parent_visible_in_child():
    g = Scope('global')
    b = Scope('block', parent=g)
    assert g.define(VarSymbol('z', Int)) is True
    assert b.resolve('z') is not None

def test_function_scope_basic():
    g = GlobalScope()
    f = FunctionScope(g, return_type=T.VOID, name="f")
    assert f.define(VarSymbol("x", Int)) is True
    assert f.resolve("x") is not None
    assert g.resolve("x") is None
    # shadowing permitido
    assert g.define(VarSymbol("x", Int)) is True
    assert f.resolve("x") is not g.resolve("x")

def test_class_scope_basic():
    g = GlobalScope()
    c = ClassScope(g, class_name="C")
    assert c.define(VarSymbol("a", Int)) is True
    assert c.resolve("a") is not None
    assert g.resolve("a") is None

def test_redeclaration_rules_per_scope():
    g = GlobalScope()
    assert g.define(VarSymbol("y", Int)) is True
    assert g.define(VarSymbol("y", Int)) is False

def test_no_cross_resolution_between_siblings():
    g = Scope('global')
    a = Scope('block', parent=g)
    b = Scope('block', parent=g)
    assert a.define(VarSymbol('x', Int)) is True
    assert b.resolve('x') is None
