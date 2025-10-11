from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .tac_ir import TACProgram, Operand, Const, Var, Temp, Label, Addr
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

    # ============================
    # CONTROL DE FLUJO (Persona B)
    # ============================

    def gen_stmt_while(self, cond_cb, body_cb) -> None:
        """Genera TAC para un ciclo while(cond) { body }"""
        L_start = self.labels.new("Lwhile_start")
        L_body  = self.labels.new("Lwhile_body")
        L_end   = self.labels.new("Lwhile_end")

        # Empieza el ciclo
        self.tac.label(L_start)
        cond = cond_cb(self)
        self.tac.emit("ifgoto", cond.value, None, L_body)
        self.tac.emit("goto", None, None, L_end)

        # Registrar etiquetas de loop
        self.labels.push_loop(continue_lbl=L_start, break_lbl=L_end)

        # Cuerpo
        self.tac.label(L_body)
        body_cb(self)
        self.tac.emit("goto", None, None, L_start)

        # Fin del ciclo
        self.labels.pop_loop()
        self.tac.label(L_end)

        if cond.is_temp and isinstance(cond.value, Temp):
            self.tmps.free(cond.value)

    def gen_stmt_do_while(self, body_cb, cond_cb) -> None:
        """Genera TAC para un ciclo do { body } while(cond)"""
        L_body = self.labels.new("Ldo_body")
        L_cond = self.labels.new("Ldo_cond")
        L_end  = self.labels.new("Ldo_end")

        self.tac.label(L_body)

        self.labels.push_loop(continue_lbl=L_cond, break_lbl=L_end)
        body_cb(self)
        self.labels.pop_loop()

        self.tac.label(L_cond)
        cond = cond_cb(self)
        self.tac.emit("ifgoto", cond.value, None, L_body)
        self.tac.label(L_end)

        if cond.is_temp and isinstance(cond.value, Temp):
            self.tmps.free(cond.value)

    def gen_stmt_for(self, init_cb, cond_cb, step_cb, body_cb) -> None:
        """Genera TAC para for(init; cond; step) { body }"""
        L_cond = self.labels.new("Lfor_cond")
        L_body = self.labels.new("Lfor_body")
        L_step = self.labels.new("Lfor_step")
        L_end  = self.labels.new("Lfor_end")

        # init
        if init_cb:
            init_cb(self)

        self.tac.label(L_cond)
        cond = cond_cb(self)
        self.tac.emit("ifgoto", cond.value, None, L_body)
        self.tac.emit("goto", None, None, L_end)

        self.labels.push_loop(continue_lbl=L_step, break_lbl=L_end)

        self.tac.label(L_body)
        body_cb(self)
        self.tac.label(L_step)
        if step_cb:
            step_cb(self)
        self.tac.emit("goto", None, None, L_cond)

        self.labels.pop_loop()
        self.tac.label(L_end)

        if cond.is_temp and isinstance(cond.value, Temp):
            self.tmps.free(cond.value)

    def gen_stmt_break(self) -> None:
        """Salto a la etiqueta break del bucle actual"""
        self.tac.emit("goto", None, None, self.labels.current_break)

    def gen_stmt_continue(self) -> None:
        """Salto a la etiqueta continue del bucle actual"""
        self.tac.emit("goto", None, None, self.labels.current_continue)

    def gen_stmt_switch(self, expr: ExprResult, case_blocks, default_cb=None) -> None:
        """
        case_blocks = [(const_value, body_cb), ...]
        default_cb = body_cb or None
        """
        L_end = self.labels.new("Lswitch_end")
        case_labels = [(self.labels.new(f"Lcase_{i}"), val, cb)
                       for i, (val, cb) in enumerate(case_blocks)]
        L_default = self.labels.new("Lswitch_default") if default_cb else L_end

        # Comparaciones de expr con cada case
        for lbl, val, _ in case_labels:
            t_cmp = self.tmps.new()
            self.tac.emit("==", expr.value, Const(val), t_cmp)
            self.tac.emit("ifgoto", t_cmp, None, lbl)
            self.tmps.free(t_cmp)
        self.tac.emit("goto", None, None, L_default)

        # Ejecutar cada case
        for lbl, _, cb in case_labels:
            self.tac.label(lbl)
            cb(self)

        # Default
        if default_cb:
            self.tac.label(L_default)
            default_cb(self)

        self.tac.label(L_end)

        if expr.is_temp and isinstance(expr.value, Temp):
            self.tmps.free(expr.value)

    def gen_stmt_return(self, expr: Optional[ExprResult] = None) -> None:
        """Genera 'ret v' o 'ret'"""
        if expr:
            self.tac.emit("ret", expr.value)
            if expr.is_temp and isinstance(expr.value, Temp):
                self.tmps.free(expr.value)
        else:
            self.tac.emit("ret")

    

    def gen_fn_begin(self, fname: str, has_this: bool = False, params: list[str] | None = None) -> None:
        """
        Marca la entrada de una función.
        Nota: 'has_this' y 'params' son informativos para el futuro; el TAC base solo necesita la etiqueta.
        """
        self.tmps.reset() 
        self.tac.label(Label(f"func_{fname}_entry"))

    def gen_fn_end(self, fname: str) -> None:
        """
        Marca el punto de salida canónico de la función (útil si normalizas returns).
        """
        self.tac.label(Label(f"func_{fname}_end"))
        self.tac.emit("ret", Const(None))

    def gen_call(self, fname: str, args: list[ExprResult]) -> ExprResult:
        """
        Convención:
          - Empaquetar argumentos en orden con 'param arg'
          - Emitir 'call fname, nargs -> t_ret'
          - Devolver ExprResult(t_ret, is_temp=True) para componer en expresiones
        """
        for a in args:
            self.tac.emit("param", a.value)
            if a.is_temp and isinstance(a.value, Temp):
                self.tmps.free(a.value)

        tret = self.tmps.new()
        self.tac.emit("call", Const(fname), Const(len(args)), tret)
        return ExprResult(tret, is_temp=True)

    def gen_stmt_expr(self, expr_res: ExprResult | None) -> None:
        """
        Permite emitir una 'expresión como statement'. Útil para llamadas cuyo retorno se ignora.
        """
        if expr_res and expr_res.is_temp and isinstance(expr_res.value, Temp):
            self.tmps.free(expr_res.value)
    
    

    def gen_array_load(self, base_operand: Operand, idx_expr: ExprResult) -> ExprResult:
        """
        Carga: taddr = base[index]; tval = load(taddr)
        IR esperado:
          addr_index base, idx -> taddr
          load taddr -> tval
        """
        taddr = self.tmps.new()
        self.tac.emit("addr_index", base_operand, idx_expr.value, taddr)

        tval = self.tmps.new()
        self.tac.emit("load", taddr, None, tval)

        # liberar temporales
        if idx_expr.is_temp and isinstance(idx_expr.value, Temp):
            self.tmps.free(idx_expr.value)
        self.tmps.free(taddr)

        return ExprResult(tval, is_temp=True)

    def gen_array_store(self, base_operand: Operand, idx_expr: ExprResult, src_expr: ExprResult) -> None:
        """
        Almacenamiento: base[index] = src
        IR esperado:
          addr_index base, idx -> taddr
          store src, taddr
        """
        taddr = self.tmps.new()
        self.tac.emit("addr_index", base_operand, idx_expr.value, taddr)
        self.tac.emit("store", src_expr.value, taddr)

        if idx_expr.is_temp and isinstance(idx_expr.value, Temp):
            self.tmps.free(idx_expr.value)
        if src_expr.is_temp and isinstance(src_expr.value, Temp):
            self.tmps.free(src_expr.value)
        self.tmps.free(taddr)

    def gen_expr_index(self, base_var_name: str, idx_expr: ExprResult) -> ExprResult:
        """
        Azúcar: devuelve el valor de base[idx] como ExprResult.
        Uso típico en expresiones: x = a[i] + 1;
        """
        return self.gen_array_load(Var(base_var_name), idx_expr)

    def gen_stmt_assign_index(self, base_var_name: str, idx_expr: ExprResult, src_expr: ExprResult) -> None:
        """
        Azúcar: statement de asignación a[i] = v;
        Uso típico en LHS indexado.
        """
        self.gen_array_store(Var(base_var_name), idx_expr, src_expr)

    

    def gen_field_load(self, base_operand: Operand, field_offset: int) -> ExprResult:
        """
        Lee base.campo
        IR:
          addr_field base, offset -> taddr
          load taddr -> tval
        """
        taddr = self.tmps.new()
        self.tac.emit("addr_field", base_operand, Const(field_offset), taddr)
        tval = self.tmps.new()
        self.tac.emit("load", taddr, None, tval)
        self.tmps.free(taddr)
        return ExprResult(tval, is_temp=True)

    def gen_field_store(self, base_operand: Operand, field_offset: int, src_expr: ExprResult) -> None:
        """
        Escribe base.campo = src
        IR:
          addr_field base, offset -> taddr
          store src, taddr
        """
        taddr = self.tmps.new()
        self.tac.emit("addr_field", base_operand, Const(field_offset), taddr)
        self.tac.emit("store", src_expr.value, taddr)
        if src_expr.is_temp and isinstance(src_expr.value, Temp):
            self.tmps.free(src_expr.value)
        self.tmps.free(taddr)

    # Azúcar: this.campo
    def gen_this_field_load(self, field_offset: int) -> ExprResult:
        return self.gen_field_load(Var("this"), field_offset)

    def gen_this_field_store(self, field_offset: int, src_expr: ExprResult) -> None:
        self.gen_field_store(Var("this"), field_offset, src_expr)

    def gen_load_addr(self, addr: Addr) -> ExprResult:
        t = self.tmps.new()
        self.tac.emit("load", addr, None, t)   # load addr -> t
        return ExprResult(t, is_temp=True)

    def gen_store_addr(self, addr: Addr, src: ExprResult) -> None:
        # IMPORTANTE: usa 'addr' como segundo operando (b)
        self.tac.emit("store", src.value, addr)  # store src, addr
        if src.is_temp and isinstance(src.value, Temp):
            self.tmps.free(src.value)
