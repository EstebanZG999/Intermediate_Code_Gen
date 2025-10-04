from program.CompiscriptVisitor import CompiscriptVisitor
from program.CompiscriptParser import CompiscriptParser
from program.ir.tac_builder import TACBuilder, ExprResult
from program.ir.tac_ir import Var, Const
from program.semantic.symbols import VarSymbol, FuncSymbol, ClassSymbol
from program.semantic.table import SymbolTable

class TACGen(CompiscriptVisitor):
    def __init__(self, symtab: SymbolTable, builder: TACBuilder):
        super().__init__()
        self.symtab = symtab
        self.b = builder

    # ---------- Programa ----------
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        for st in ctx.statement():
            self.visit(st)
        return None

    # ---------- Literales / Identificadores ----------
    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        txt = ctx.getText()
        if txt == "null":
            return self.b.gen_expr_literal(None)
        if txt in ("true", "false"):
            return self.b.gen_expr_literal(1 if txt == "true" else 0)
        if txt.isdigit():
            return self.b.gen_expr_literal(int(txt))
        if txt.startswith('"') and txt.endswith('"'):
            # si tu IR trata strings como Const(str)
            return ExprResult(Const(txt.strip('"')))
        return self.b.gen_expr_literal(0)

    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        return self.b.gen_expr_var(name)

    # ---------- Operadores (usa tu builder ya hecho) ----------
    def visitAdditiveExpr(self, ctx):
        L = self.visit(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            op = ctx.getChild(2*i-1).getText()
            R = self.visit(ctx.multiplicativeExpr(i))
            L = self.b.gen_expr_add(L, R) if op == "+" else self.b.gen_expr_sub(L, R)
        return L

    def visitMultiplicativeExpr(self, ctx):
        L = self.visit(ctx.unaryExpr(0))
        for i in range(1, len(ctx.unaryExpr())):
            op = ctx.getChild(2*i-1).getText()
            R = self.visit(ctx.unaryExpr(i))
            if op == "*": L = self.b.gen_expr_mul(L, R)
            elif op == "/": L = self.b.gen_expr_div(L, R)
            else: L = self.b.gen_expr_mod(L, R)
        return L

    def visitRelationalExpr(self, ctx):
        if not ctx.additiveExpr(): return self.b.gen_expr_literal(0)
        L = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            op = ctx.getChild(2*i-1).getText()   # <, <=, >, >=
            R = self.visit(ctx.additiveExpr(i))
            L = self.b.gen_expr_rel(op, L, R)
        return L

    def visitEqualityExpr(self, ctx):
        if not ctx.relationalExpr(): return self.b.gen_expr_literal(0)
        L = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            op = ctx.getChild(2*i-1).getText()   # ==, !=
            R = self.visit(ctx.relationalExpr(i))
            L = self.b.gen_expr_rel(op, L, R)
        return L

    def visitLogicalAndExpr(self, ctx):
        def fold(i, acc):
            if i == len(ctx.equalityExpr()): return acc
            return self.b.gen_expr_and(acc, lambda: self.visit(ctx.equalityExpr(i)))
        return fold(1, self.visit(ctx.equalityExpr(0)))

    def visitLogicalOrExpr(self, ctx):
        def fold(i, acc):
            if i == len(ctx.logicalAndExpr()): return acc
            return self.b.gen_expr_or(acc, lambda: self.visit(ctx.logicalAndExpr(i)))
        return fold(1, self.visit(ctx.logicalAndExpr(0)))

    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() == 2:
            op = ctx.getChild(0).getText()
            E = self.visit(ctx.unaryExpr())
            return self.b.gen_expr_rel("==", E, ExprResult(Const(0))) if op == "!" else E
        return self.visit(ctx.primaryExpr())

    def visitPrimaryExpr(self, ctx):
        if ctx.literalExpr(): return self.visit(ctx.literalExpr())
        if ctx.leftHandSide(): return self.visit(ctx.leftHandSide())
        if ctx.expression(): return self.visit(ctx.expression())
        return self.b.gen_expr_literal(0)

    # ---------- LHS (propiedad, index, llamada) ----------
    def visitLeftHandSide(self, ctx):
        base = self.visit(ctx.primaryAtom())
        for s in ctx.suffixOp():
            base = self.visit(s)  # cada suffix devuelve ExprResult
        return base

    def visitPropertyAccessExpr(self, ctx):
        # parent LHS contiene el objeto en primaryAtom()
        lhs_ctx = ctx.parentCtx
        obj_expr = self.visit(lhs_ctx.primaryAtom())
        field_name = ctx.Identifier().getText()

        # Necesitamos el tipo del objeto; en un compilador “real”
        # lo obtendrías desde semántica. Aquí: asumimos Var(name) y consultamos symtab.
        if isinstance(obj_expr.value, Var):
            var_sym = self.symtab.scope_stack.current.resolve(obj_expr.value.name)
            obj_type_name = var_sym.type.name if isinstance(var_sym, VarSymbol) else None
        else:
            obj_type_name = None

        if obj_type_name is None:
            return self.b.gen_expr_literal(0)

        off = self.symtab.field_offset(obj_type_name, field_name)
        # lectura (expr)
        return self.b.gen_field_load(obj_expr.value, off)

    def visitIndexExpr(self, ctx):
        # a[i] como parte de LHS
        lhs_ctx = ctx.parentCtx.primaryAtom()
        base_name = lhs_ctx.Identifier().getText() if lhs_ctx and lhs_ctx.Identifier() else None
        idx_res = self.visit(ctx.expression())
        if base_name:
            return self.b.gen_expr_index(base_name, idx_res)
        return self.b.gen_expr_literal(0)

    def visitCallExpr(self, ctx):
        # foo(args) y obj.m(args) (para este esqueleto: foo(args))
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.visit(e))
        lhs_ctx = ctx.parentCtx
        base_name = lhs_ctx.primaryAtom().Identifier().getText() if lhs_ctx.primaryAtom() and lhs_ctx.primaryAtom().Identifier() else None
        if base_name:
            return self.b.gen_call(base_name, args)
        return self.b.gen_expr_literal(0)

    # ---------- Statements ----------
    def visitVariableDeclaration(self, ctx):
        # solo inicialización (para TAC)
        if ctx.initializer():
            rhs = self.visit(ctx.initializer().expression())
            name = ctx.Identifier().getText()
            self.b._assign(Var(name), rhs)
        return None

    def visitConstantDeclaration(self, ctx):
        # idem variable, pero constante
        rhs = self.visit(ctx.expression())
        name = ctx.Identifier().getText()
        self.b._assign(Var(name), rhs)
        return None

    def visitAssignment(self, ctx):
        exprs = ctx.expression()
        if isinstance(exprs, list) and len(exprs) == 2:
            # obj.prop = expr
            obj = self.visit(exprs[0])  # ExprResult
            prop = ctx.Identifier().getText()
            val = self.visit(exprs[1])
            # deduce tipo de obj
            obj_type_name = None
            if isinstance(obj.value, Var):
                var_sym = self.symtab.scope_stack.current.resolve(obj.value.name)
                obj_type_name = var_sym.type.name if isinstance(var_sym, VarSymbol) else None
            off = self.symtab.field_offset(obj_type_name, prop) if obj_type_name else 0
            self.b.gen_field_store(obj.value, off, val)
            return None
        # var = expr
        name = ctx.Identifier().getText()
        val = self.visit(exprs[0] if isinstance(exprs, list) else exprs)
        self.b._assign(Var(name), val)
        return None

    def visitPrintStatement(self, ctx):
        v = self.visit(ctx.expression())
        self.b.gen_stmt_print(v)
        return None

    def visitReturnStatement(self, ctx):
        if ctx.expression():
            self.b.gen_stmt_return(self.visit(ctx.expression()))
        else:
            self.b.gen_stmt_return()
        return None

    def visitIfStatement(self, ctx):
        cond = self.visit(ctx.expression())
        def then_cb(b): self.visit(ctx.block(0))
        def else_cb(b): self.visit(ctx.block(1))
        if ctx.block(1):
            self.b.gen_stmt_if(cond, then_cb, else_cb)
        else:
            self.b.gen_stmt_if(cond, then_cb, None)
        return None

    def visitWhileStatement(self, ctx):
        def cond_cb(b): return self.visit(ctx.expression())
        def body_cb(b): self.visit(ctx.block())
        self.b.gen_stmt_while(cond_cb, body_cb)
        return None

    def visitBlock(self, ctx):
        for st in ctx.statement():
            self.visit(st)
        return None

    # ---------- Funciones y clases (solo etiquetas para funciones top-level) ----------
    def visitFunctionDeclaration(self, ctx):
        fname = ctx.Identifier().getText()
        self.b.gen_fn_begin(fname)
        # cuerpo
        for st in ctx.block().statement():
            self.visit(st)
        # si la función es void y no retornó explícito, gen_fn_end garantiza ret None
        self.b.gen_fn_end(fname)
        return None

    def visitClassDeclaration(self, ctx):
        # TAC no materializa clases por ahora (solo accedemos a offsets vía symtab)
        return None
