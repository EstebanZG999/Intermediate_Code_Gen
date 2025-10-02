from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .tac_ir import TACProgram, Operand, Const, Var, Temp, Label
from .temp_alloc import TempAllocator
from .label_mgr import LabelManager

@dataclass
class ExprResult:
    value: Operand
    is_temp: bool = False

class TACBuilder:
    """
    Builder de TAC centrado en EXPRESIONES y helpers de control mínimos.
    Persona A es propietaria de este archivo (sección expresiones).
    Persona B/C lo extenderán con statements/llamadas/memoria.
    """
    def __init__(self) -> None:
        self.tac = TACProgram()
        self.tmps = TempAllocator()
        self.labels = LabelManager()

    def _binop(self, op: str, lhs: ExprResult, rhs: ExprResult) -> ExprResult:
        t = self.tmps.new()
        self.tac.emit(op, lhs.value, rhs.value, t)
        if lhs.is_temp and isinstance(lhs.value, Temp):
            self.tmps.free(lhs.value)
        if rhs.is_temp and isinstance(rhs.value, Temp):
            self.tmps.free(rhs.value)
        return ExprResult(t, is_temp=True)

    def _assign(self, dst: Operand, src: ExprResult) -> None:
        self.tac.emit(":=", src.value, None, dst)
        if src.is_temp and isinstance(src.value, Temp):
            self.tmps.free(src.value)

    # Literales y variables
    def gen_expr_literal(self, value) -> ExprResult:
        t = self.tmps.new()
        self.tac.emit(":=", Const(value), None, t)
        return ExprResult(t, is_temp=True)

    def gen_expr_var(self, name: str) -> ExprResult:
        return ExprResult(Var(name), is_temp=False)

    # Aritmética
    def gen_expr_add(self, L: ExprResult, R: ExprResult) -> ExprResult: return self._binop("+", L, R)
    def gen_expr_sub(self, L: ExprResult, R: ExprResult) -> ExprResult: return self._binop("-", L, R)
    def gen_expr_mul(self, L: ExprResult, R: ExprResult) -> ExprResult: return self._binop("*", L, R)
    def gen_expr_div(self, L: ExprResult, R: ExprResult) -> ExprResult: return self._binop("/", L, R)
    def gen_expr_mod(self, L: ExprResult, R: ExprResult) -> ExprResult: return self._binop("%", L, R)

    # Relacionales (0/1)
    def gen_expr_rel(self, op: str, L: ExprResult, R: ExprResult) -> ExprResult:
        return self._binop(op, L, R)

    # Lógicos con short-circuit
    def gen_expr_not(self, E: ExprResult) -> ExprResult:
        zero = ExprResult(Const(0), is_temp=False)
        return self._binop("==", E, zero)

    def gen_expr_and(self, L: ExprResult, R_cb) -> ExprResult:
        res = self.tmps.new()
        L_check_rhs = self.labels.new()
        L_false = self.labels.new()
        L_end = self.labels.new()

        self.tac.emit("ifgoto", L.value, None, L_check_rhs)
        self.tac.emit("goto", None, None, L_false)

        self.tac.label(L_check_rhs)
        R = R_cb()
        L_true = self.labels.new()
        self.tac.emit("ifgoto", R.value, None, L_true)
        self.tac.emit("goto", None, None, L_false)

        self.tac.label(L_true)
        self.tac.emit(":=", Const(1), None, res)
        self.tac.emit("goto", None, None, L_end)

        self.tac.label(L_false)
        self.tac.emit(":=", Const(0), None, res)

        self.tac.label(L_end)

        if L.is_temp and isinstance(L.value, Temp): self.tmps.free(L.value)
        if R.is_temp and isinstance(R.value, Temp): self.tmps.free(R.value)  # type: ignore

        return ExprResult(res, is_temp=True)

    def gen_expr_or(self, L: ExprResult, R_cb) -> ExprResult:
        res = self.tmps.new()
        L_true = self.labels.new()
        L_check_rhs = self.labels.new()
        L_end = self.labels.new()

        self.tac.emit("ifgoto", L.value, None, L_true)
        self.tac.emit("goto", None, None, L_check_rhs)

        self.tac.label(L_check_rhs)
        R = R_cb()
        self.tac.emit("ifgoto", R.value, None, L_true)
        self.tac.emit(":=", Const(0), None, res)
        self.tac.emit("goto", None, None, L_end)

        self.tac.label(L_true)
        self.tac.emit(":=", Const(1), None, res)
        self.tac.label(L_end)

        if L.is_temp and isinstance(L.value, Temp): self.tmps.free(L.value)
        if R.is_temp and isinstance(R.value, Temp): self.tmps.free(R.value)  # type: ignore

        return ExprResult(res, is_temp=True)

    # Demo de statement: print
    def gen_stmt_print(self, expr: ExprResult) -> None:
        self.tac.emit("print", expr.value)
        if expr.is_temp and isinstance(expr.value, Temp):
            self.tmps.free(expr.value)

    def gen_stmt_if(self, cond: ExprResult, then_body_cb, else_body_cb=None) -> None:
        L_then = self.labels.new()
        L_end  = self.labels.new()
        L_else = self.labels.new() if else_body_cb else L_end
        self.tac.emit("ifgoto", cond.value, None, L_then)
        self.tac.emit("goto", None, None, L_else)
        self.tac.label(L_then)
        then_body_cb(self)
        if else_body_cb:
            self.tac.emit("goto", None, None, L_end)
            self.tac.label(L_else)
            else_body_cb(self)
        self.tac.label(L_end)
        if cond.is_temp and isinstance(cond.value, Temp):
            self.tmps.free(cond.value)