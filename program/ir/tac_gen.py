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
        self.fn_stack: list[str] = []

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
        # Si solo hay una subexpresión, devuélvela directamente
        if len(ctx.equalityExpr()) == 1:
            return self.visit(ctx.equalityExpr(0))

        # Caso con múltiples && encadenados
        L = self.visit(ctx.equalityExpr(0))
        for i in range(1, len(ctx.equalityExpr())):
            R = self.visit(ctx.equalityExpr(i))
            L = self.b.gen_expr_and(L, lambda R=R: R)
        return L

    def visitLogicalOrExpr(self, ctx):
        # Si solo hay una subexpresión, devuélvela directamente
        if len(ctx.logicalAndExpr()) == 1:
            return self.visit(ctx.logicalAndExpr(0))

        # Caso con múltiples || encadenados
        L = self.visit(ctx.logicalAndExpr(0))
        for i in range(1, len(ctx.logicalAndExpr())):
            R = self.visit(ctx.logicalAndExpr(i))
            L = self.b.gen_expr_or(L, lambda R=R: R)
        return L


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

    def visitNewExpr(self, ctx):
        """
        Traduce: new Clase(args)
        Genera una llamada al constructor si existe.
        """
        class_name = ctx.Identifier().getText()
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.visit(e))

        # Reservar memoria simbólicamente para el objeto
        temp_obj = self.b.tmps.new()
        self.b.tac.emit("alloc", Const(class_name), None, temp_obj)

        # Buscar constructor y generar llamada
        cls = self.symtab._resolve_class(class_name)
        if cls and "constructor" in cls.methods:
            ctor = cls.methods["constructor"]
            params = [ExprResult(Var("this"), False)] + args
            # Pasar 'this' + args al constructor
            self.b.tac.emit("param", temp_obj)
            for a in args:
                self.b.tac.emit("param", a.value)
            self.b.tac.emit("call", Const(f"{class_name}.constructor"), Const(len(args)+1))
        
        return ExprResult(temp_obj, is_temp=True)



    def visitPropertyAccessExpr(self, ctx):
        lhs_ctx = ctx.parentCtx
        obj_expr = self.visit(lhs_ctx.primaryAtom())
        field_name = ctx.Identifier().getText()

        # Obtener tipo del objeto
        if isinstance(obj_expr.value, Var):
            var_sym = self.symtab.scope_stack.current.resolve(obj_expr.value.name)
            obj_type_name = var_sym.type.name if isinstance(var_sym, VarSymbol) else None
        else:
            obj_type_name = None

        if obj_type_name is None:
            return self.b.gen_expr_literal(0)

        # --- NUEVO BLOQUE: si es método, no pidas field_offset ---
        cls = self.symtab._resolve_class(obj_type_name)
        if cls and field_name in cls.methods:
            # devolvemos referencia simbólica al método (no field)
            return self.b.gen_expr_var(f"{obj_type_name}.{field_name}")

        # Si no es método, tratamos como campo normal
        off = self.symtab.field_offset(obj_type_name, field_name)
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
        """
        - foo(args)               → función global o local calificada si estamos dentro de otra función
        - obj.metodo(args)        → método con this como primer argumento
        """
        # 1) argumentos
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.visit(e))

        # 2) subir al LHS (SuffixOp(Call) -> LeftHandSide)
        parent = ctx.parentCtx
        lhs = getattr(parent, "parentCtx", None)
        if lhs is not None:
            lhs_text = lhs.getText()

            # 2a) llamada a método obj.metodo(...)
            if "." in lhs_text:
                before_paren = lhs_text.split("(", 1)[0]
                obj_name, method_name = before_paren.split(".", 1)

                # intenta resolver el tipo del objeto
                obj_sym = self.symtab.scope_stack.current.resolve(obj_name)
                obj_type = obj_sym.type.name if isinstance(obj_sym, VarSymbol) and hasattr(obj_sym.type, "name") else None

                # this + args
                self.b.tac.emit("param", Var(obj_name))
                for a in args:
                    self.b.tac.emit("param", a.value)

                tmp = self.b.tmps.new()
                callee = f"{obj_type}.{method_name}" if obj_type else f"{obj_name}.{method_name}"
                self.b.tac.emit("call", Const(callee), Const(len(args) + 1), tmp)
                return ExprResult(tmp, is_temp=True)

            # 2b) función (foo(args))
            if hasattr(lhs, "primaryAtom") and lhs.primaryAtom() and lhs.primaryAtom().Identifier():
                base_name = lhs.primaryAtom().Identifier().getText()

                # si estamos en función anidada, probar calificada: <outer>.<base_name>
                qualified = f"{self.fn_stack[-1]}.{base_name}" if self.fn_stack else base_name

                # emitimos como calificada si hay anidamiento; si quieres ser más estricto
                # podrías chequear en symtab si existe; aquí preferimos calificar SOLO si hay anidamiento
                callee_name = qualified if self.fn_stack else base_name

                for a in args:
                    self.b.tac.emit("param", a.value)
                tmp = self.b.tmps.new()
                self.b.tac.emit("call", Const(callee_name), Const(len(args)), tmp)
                return ExprResult(tmp, is_temp=True)

            # 3) Si el LHS no existe (llamada directa en expresión)
            if ctx.Identifier():
                func_name = ctx.Identifier().getText()
                # calificar si estamos dentro de función anidada
                callee_name = f"{self.fn_stack[-1]}.{func_name}" if self.fn_stack else func_name
                for a in args:
                    self.b.tac.emit("param", a.value)
                tmp = self.b.tmps.new()
                self.b.tac.emit("call", Const(callee_name), Const(len(args)), tmp)
                return ExprResult(tmp, is_temp=True)

            # 4) fallback final
            return self.b.gen_expr_literal(0)



 
 
    # ---------- Statements ----------
    def visitVariableDeclaration(self, ctx):
        name = ctx.Identifier().getText()
        if ctx.initializer():
            init = ctx.initializer()
            if init.arrayLiteral():
                rhs = self.visit(init.arrayLiteral())
            else:
                rhs = self.visit(init.expression())
            if rhs is None:
                rhs = ExprResult(Const(0), is_temp=False)
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
        def else_cb(b): self.visit(ctx.block(1)) if len(ctx.block()) > 1 else None
        if len(ctx.block()) > 1:
            self.b.gen_stmt_if(cond, then_cb, else_cb)
        else:
            self.b.gen_stmt_if(cond, then_cb, None)
        return None


    def visitWhileStatement(self, ctx):
        """
        Traduce:
        while (<expr>) <block>
        """
        def cond_cb(b):
            if ctx.expression():
                return self.visit(ctx.expression())
            return self.b.gen_expr_literal(1)  # por si falta expresión

        def body_cb(b):
            self.visit(ctx.block())

        self.b.gen_stmt_while(cond_cb, body_cb)
        return None


    def visitBlock(self, ctx):
        for st in ctx.statement():
            self.visit(st)
        return None

    # ---------- Funciones y clases (solo etiquetas para funciones top-level) ----------
    def visitFunctionDeclaration(self, ctx):
        fname = ctx.Identifier().getText()

        # calificar si estamos dentro de otra función
        if self.fn_stack:
            fname = f"{self.fn_stack[-1]}.{fname}"

        self.b.gen_fn_begin(fname)

        # push
        self.fn_stack.append(fname)
        try:
            for st in ctx.block().statement():
                self.visit(st)
        finally:
            # pop SIEMPRE, aunque haya error
            self.fn_stack.pop()

        self.b.gen_fn_end(fname)
        return None



    def visitClassDeclaration(self, ctx):
        # TAC no materializa clases por ahora (solo accedemos a offsets vía symtab)
        return None

    def visitDoWhileStatement(self, ctx):
        """
        Traduce:
        do <block> while (<expr>);
        """
        def body_cb(b):
            self.visit(ctx.block())

        def cond_cb(b):
            if ctx.expression():
                return self.visit(ctx.expression())
            return self.b.gen_expr_literal(1)

        self.b.gen_stmt_do_while(body_cb, cond_cb)
        return None


    def visitForStatement(self, ctx):
        """
        Traduce:
        for (<init>; <cond>; <update>) <block>
        donde <init> puede ser variableDeclaration, assignment o ';'
        """

        def init_cb(b):
            first = ctx.getChild(2)
            if isinstance(first, CompiscriptParser.VariableDeclarationContext):
                self.visit(first)
            elif isinstance(first, CompiscriptParser.AssignmentContext):
                self.visit(first)
            # Si es ';', no hace nada

        def cond_cb(b):
            exprs = ctx.expression()
            if len(exprs) >= 1:
                return self.visit(exprs[0])
            return self.b.gen_expr_literal(1)

        def step_cb(b):
            exprs = ctx.expression()
            if len(exprs) == 2:
                self.visit(exprs[1])

        def body_cb(b):
            self.visit(ctx.block())

        self.b.gen_stmt_for(init_cb, cond_cb, step_cb, body_cb)
        return None



 
    def visitBreakStatement(self, ctx):
        self.b.gen_stmt_break()
        return None

    def visitContinueStatement(self, ctx):
        self.b.gen_stmt_continue()
        return None

    def visitSwitchStatement(self, ctx):
        expr = self.visit(ctx.expression())
        case_blocks = []

        for c in ctx.switchCase():
            val = self.visit(c.expression())  # no uses int() porque puede no ser literal
            def cb(b, c=c): 
                for st in c.statement():
                    self.visit(st)
            case_blocks.append((val, cb))

        default_cb = None
        if ctx.defaultCase():
            def default_cb(b):
                for st in ctx.defaultCase().statement():
                    self.visit(st)

        self.b.gen_stmt_switch(expr, case_blocks, default_cb)
        return None


    def visitArrayLiteral(self, ctx):
        elems = [self.visit(e) for e in ctx.expression()] if ctx.expression() else []
        temp_arr = self.b.tmps.new()
        self.b.tac.emit("alloc_array", Const(len(elems)), None, temp_arr)
        for i, e in enumerate(elems):
            idx = self.b.gen_expr_literal(i)
            self.b.gen_array_store(temp_arr, idx, e)
        return ExprResult(temp_arr, is_temp=True)



    def visitThisExpr(self, ctx):
        # 'this' sin campo explícito
        return self.b.gen_expr_var("this")



    def visitTernaryExpr(self, ctx):
        # Si solo hay 1 hijo, no existe el operador ternario
        if ctx.getChildCount() == 1:
            return self.visit(ctx.logicalOrExpr())

        # Si hay ternario (cond ? expr1 : expr2)
        cond = self.visit(ctx.logicalOrExpr())
        then_expr = lambda: self.visit(ctx.expression(0))
        else_expr = lambda: self.visit(ctx.expression(1))

        L_true = self.b.labels.new("Ltern_true")
        L_false = self.b.labels.new("Ltern_false")
        L_end = self.b.labels.new("Ltern_end")

        res = self.b.tmps.new()
        self.b.tac.emit("ifgoto", cond.value, None, L_true)
        self.b.tac.emit("goto", None, None, L_false)

        self.b.tac.label(L_true)
        t_then = then_expr()
        self.b.tac.emit(":=", t_then.value, None, res)
        self.b.tac.emit("goto", None, None, L_end)

        self.b.tac.label(L_false)
        t_else = else_expr()
        self.b.tac.emit(":=", t_else.value, None, res)

        self.b.tac.label(L_end)
        return ExprResult(res, is_temp=True)

    # assignmentExpr:
    #   lhs=leftHandSide '=' assignmentExpr            # AssignExpr
    # | lhs=leftHandSide '.' Identifier '=' assignmentExpr # PropertyAssignExpr
    # | conditionalExpr                                # ExprNoAssign

    def visitAssignExpr(self, ctx: CompiscriptParser.AssignExprContext):
        # LHS puede ser Identificador o índice (a[i] = ...)
        lhs_ctx = ctx.lhs
        rhs = self.visit(ctx.assignmentExpr())

        # Caso: a[i] = v  (si el último sufijo es IndexExpr)
        # Inspeccionamos el texto por simplicidad (podrías caminar el AST si prefieres)
        lhs_text = lhs_ctx.getText()
        if '[' in lhs_text and lhs_text.endswith(']'):
            # extraer base e índice: a[i]
            base = lhs_text[:lhs_text.index('[')]
            # mejor visitar el índice real del último suffix:
            # asumimos una sola indexación al final:
            # buscamos el ÚLTIMO suffix, que es IndexExpr
            suffixes = list(lhs_ctx.suffixOp())
            if suffixes and suffixes[-1].expression():
                idx = self.visit(suffixes[-1].expression())
                self.b.gen_stmt_assign_index(base, idx, rhs)
                return rhs

        # Caso general: variable simple
        if lhs_ctx.primaryAtom() and lhs_ctx.primaryAtom().Identifier():
            var_name = lhs_ctx.primaryAtom().Identifier().getText()
            self.b._assign(Var(var_name), rhs)
            return rhs

        # Fallback (si apareciera otra forma)
        return rhs


    def visitPropertyAssignExpr(self, ctx: CompiscriptParser.PropertyAssignExprContext):
        # obj.prop = expr
        rhs = self.visit(ctx.assignmentExpr())
        lhs_ctx = ctx.lhs  # leftHandSide
        # obj es la cabeza del LHS
        obj_name = lhs_ctx.primaryAtom().Identifier().getText() if lhs_ctx.primaryAtom().Identifier() else None
        prop = ctx.Identifier().getText()

        if obj_name:
            obj_sym = self.symtab.scope_stack.current.resolve(obj_name)
            obj_type_name = obj_sym.type.name if isinstance(obj_sym, VarSymbol) else None
            off = self.symtab.field_offset(obj_type_name, prop) if obj_type_name else 0
            self.b.gen_field_store(Var(obj_name), off, rhs)
        return rhs





