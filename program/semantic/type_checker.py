from program.semantic.typesys import make_fn, FunctionType
from program.semantic.scopes import GlobalScope, ScopeStack
from program.semantic.symbols import VarSymbol, FuncSymbol, ClassSymbol, ParamSymbol
from program.semantic.typesys import (
    Type, INTEGER, STRING, BOOLEAN, VOID, NULL,
    ArrayType,   
    can_assign, arithmetic_type, logical_type, comparison_type,
    make_array, plus_type, arith_type, relational_type, equality_type, is_array,
    element_type,
)

from program.semantic.error_reporter import ErrorReporter
from program.CompiscriptVisitor import CompiscriptVisitor
from program.CompiscriptParser import CompiscriptParser
from contextlib import contextmanager

from program.runtime.activation_record import ActivationRecord
from program.semantic.symbols import VarSymbol, ParamSymbol, FuncSymbol, ClassSymbol
from program.semantic.table import SymbolTable

class TypeChecker(CompiscriptVisitor):
    def __init__(self, reporter: ErrorReporter):
        super().__init__()
        self.reporter = reporter
        self.scopes = ScopeStack()
        self.scopes.push("global")
        self._current_class: str | None = None
        self.symtab = SymbolTable(self.scopes)
        self._current_func: FuncSymbol | None = None 

    def define_symbol(self, sym):
        if not self.scopes.stack:
            self.scopes.push("global")
        if not self.scopes.current.define(sym):
            self.reporter.report(0, 0, "E_REDECL", f"Redeclaración de {sym.name}")

    def resolve_symbol(self, name, line=0, col=0):
        if name in ("integer", "string", "boolean", "void"):
            return None

        sym = self.scopes.current.resolve(name)
        if sym is None:
            self.reporter.report(line, col, "E_UNDEF", f"Símbolo no definido: {name}")
        return sym

    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        for stmt in ctx.statement():
            self.visit(stmt)
        return None

    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        vtype = self.visit(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else VOID
        sym = VarSymbol(
            name, vtype,
            is_const=False,
            is_initialized=False,
            line=ctx.start.line,
            col=ctx.start.column
        )

        if ctx.initializer():
            init_t = self.visit(ctx.initializer().expression()) or VOID
            if not can_assign(vtype, init_t):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                    f"No se puede asignar {init_t} a {vtype}")
            else:
                sym.is_initialized = True

        self.define_symbol(sym)

        # si estamos dentro de una función/método, asigar offset/región ahora mismo
        if self.scopes.inside("function") and self._current_func and self._current_func.activation_record:
            ar = self._current_func.activation_record
            ar.add_local(name)
            slot = ar.addr_of(name)
            if slot:
                sym.offset = slot.offset
                sym.region = "local"  # o REG_LOCAL

        return None

    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        vtype = self.visit(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else VOID
        init_t = self.visit(ctx.expression())
        sym = VarSymbol(
            name, vtype,
            is_const=True,
            is_initialized=True,
            line=ctx.start.line,
            col=ctx.start.column
        )

        if not can_assign(vtype, init_t):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                f"No se puede asignar {init_t} a {vtype}")

        self.define_symbol(sym)

        # Si es const local a función, también ocupa un slot de local (inmutable pero vive en el frame)
        if self.scopes.inside("function") and self._current_func and self._current_func.activation_record:
            ar = self._current_func.activation_record
            ar.add_local(name)
            slot = ar.addr_of(name)
            if slot:
                sym.offset = slot.offset
                sym.region = "local"  # o REG_LOCAL

        return None

    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        exprs = ctx.expression()

        # asignación de propiedad ->  <expr> '.' Identifier '=' <expr> ';'
        if isinstance(exprs, list) and len(exprs) == 2:
            obj_t = self.visit(exprs[0]) or VOID
            value_t = self.visit(exprs[1]) or VOID
            prop_name = ctx.Identifier().getText()

            # Debe ser un objeto con tipo de clase conocido
            if not isinstance(obj_t, Type):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                    f"No se puede asignar propiedad '{prop_name}' en {obj_t}")
                return VOID

            # Resolver la clase y buscar el campo (con herencia)
            class_sym = self.resolve_symbol(obj_t.name, ctx.start.line, ctx.start.column)
            while isinstance(class_sym, ClassSymbol):
                field = class_sym.fields.get(prop_name) if hasattr(class_sym, "fields") else None
                if field:
                    # const field no reasignable
                    if getattr(field, "is_const", False):
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_CONST",
                                            f"No se puede asignar a la constante de clase '{prop_name}'")
                        return field.type
                    # Verificar asignabilidad
                    if not can_assign(field.type, value_t):
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                            f"No se puede asignar {value_t} a campo {field.type}")
                    return field.type
                # subir a la base si hay herencia
                if hasattr(class_sym, "base") and class_sym.base:
                    class_sym = self.resolve_symbol(class_sym.base, ctx.start.line, ctx.start.column)
                else:
                    break

            # Campo no existe en la jerarquía
            self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                f"Campo '{prop_name}' no definido en {obj_t.name}")
            return VOID

        # asignación simple ->  Identifier '=' <expr> ';'
        else:
            name = ctx.Identifier().getText()
            sym = self.resolve_symbol(name, ctx.start.line, ctx.start.column)
            target_t = (sym.type if sym else VOID) or VOID

            # const variable no reasignable
            if isinstance(sym, VarSymbol) and sym.is_const:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_CONST",
                                    f"No se puede asignar a la constante '{name}'")
            else:
                expr_node = exprs[0] if isinstance(exprs, list) else exprs
                value_t = self.visit(expr_node) or VOID

                if not can_assign(target_t, value_t):
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                        f"No se puede asignar {value_t} a {target_t}")
                else:
                    # NUEVO: marcar inicializada la variable
                    if isinstance(sym, VarSymbol):
                        sym.is_initialized = True
            return target_t


    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        ret_type = self.visit(ctx.type_()) if ctx.type_() else VOID

        params = []
        if ctx.parameters():
            for i, p in enumerate(ctx.parameters().parameter()):
                pname = p.Identifier().getText()
                ptype = self.visit(p.type_()) if p.type_() else VOID
                param_sym = ParamSymbol(
                    pname, ptype, i,
                    line=p.start.line, col=p.start.column
                )
                params.append(param_sym)

        func_type = make_fn([p.type for p in params], ret_type)
        func_sym = FuncSymbol(
            name, type=func_type, params=tuple(params),
            line=ctx.start.line, col=ctx.start.column,
            closure_scope=self.scopes.current
        )
        prev_func = self._current_func
        self._current_func = func_sym
        self.define_symbol(func_sym)

        # Registrar funciones anidadas (tu lógica original)
        parent_scope = self.scopes.current
        if hasattr(parent_scope, "func_name") and parent_scope.func_name:
            parent_sym = self.resolve_symbol(parent_scope.func_name)
            if isinstance(parent_sym, FuncSymbol):
                if not hasattr(parent_sym, "nested"):
                    parent_sym.nested = {}
                parent_sym.nested[name] = func_sym

        # PUSH del scope de función
        self.scopes.push_function(ret_type, name)

        # Capturamos el scope de función "real"
        func_scope = self.scopes.current

        # Definir símbolos de parámetros en el scope de función (como haces hoy)
        for psym in params:
            self.define_symbol(psym)

        # Crear RA y asignar offsets a THIS (si aplica) + PARÁMETROS
        self._begin_function_layout(func_sym, func_scope)

        # Visitar cuerpo: tus locales se declaran aquí dentro (en un BlockScope)
        returns = []
        has_terminated = False
        with self._block():
            for stmt in ctx.block().statement():
                if has_terminated:
                    self.reporter.report(
                        stmt.start.line, stmt.start.column, "E_DEADCODE",
                        "Código muerto: esta instrucción nunca se ejecutará"
                    )
                r = self.visit(stmt)
                if stmt.returnStatement():
                    returns.append(r or VOID)
                    has_terminated = True

        # Tras visitar el cuerpo, asignar offsets a LOCALES
        self._finalize_function_layout(func_sym, func_scope)
        
        self._current_func = prev_func

        # POP del scope de función
        self.scopes.pop()

        if not returns and ret_type != VOID:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_RETURN",
                                f"Función {name} sin return pero declarada {ret_type}")

        for rt in returns:
            if not can_assign(ret_type, rt):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_RETURN",
                                    f"Return {rt} incompatible con {ret_type}")

        return None

    def _begin_function_layout(self, func_sym: FuncSymbol, func_scope):
        """
        Crea el AR y asigna offsets a THIS (si aplica) y a todos los parámetros.
        Además, inyecta un símbolo 'this' (VarSymbol) en el scope del método para
        poder tomar su dirección en el generador de TAC.
        """
        ar = ActivationRecord(func_name=func_sym.name)

        # (1) THIS si es método de clase
        if self._is_method(func_sym, func_scope):
            ar.add_this()
            # inyectar símbolo 'this' en el scope del método
            this_sym = VarSymbol(
                "this",
                Type(self._current_class) if self._current_class else Type("object"),
                is_const=True, is_initialized=True,
                region="this",  # o REG_THIS
                offset=ar.addr_of("this").offset
            )
            # defínelo solo si no existe
            cur = None
            if hasattr(func_scope, "resolve"):
                cur = func_scope.resolve("this")
            elif hasattr(func_scope, "symbols"):
                cur = func_scope.symbols.get("this")
            if not cur:
                if hasattr(func_scope, "define"):
                    func_scope.define(this_sym)
                elif hasattr(func_scope, "symbols"):
                    func_scope.symbols["this"] = this_sym

        # (2) Parámetros en orden
        for p in func_sym.params:
            ar.add_param(p.name)
            slot = ar.addr_of(p.name)
            if slot:
                # marca en el símbolo de parámetro
                p.offset = slot.offset
                p.region = "param"  # o REG_PARAM

                # si también quieres un VarSymbol sombra (opcional):
                # vparam = VarSymbol(p.name, p.type, is_const=False, is_initialized=True,
                #                    region="param", offset=slot.offset)
                # func_scope.define(vparam)

        func_sym.activation_record = ar


    def _finalize_function_layout(self, func_sym: FuncSymbol, func_scope):
        """
        Barrido de seguridad: asigna offset local a cualquier VarSymbol del scope
        de función que aún no tenga offset/region (por ejemplo si se definió sin pasar
        por visitVariableDeclaration, o si quedó en el scope de función).
        En este diseño, la idea es asignar locales 'en caliente' en visitVariableDeclaration,
        por lo que aquí normalmente habrá poco que hacer.
        """
        ar = func_sym.activation_record
        if ar is None:
            ar = ActivationRecord(func_name=func_sym.name)
            func_sym.activation_record = ar

        items_iter = []
        if hasattr(func_scope, "items"):
            items_iter = list(func_scope.items())
        elif hasattr(func_scope, "symbols"):
            items_iter = list(func_scope.symbols.items())

        for name, sym in items_iter:
            if isinstance(sym, VarSymbol) and sym.region not in ("param", "this", "field", "global"):
                if sym.offset is None:
                    ar.add_local(name)
                    slot = ar.addr_of(name)
                    if slot:
                        sym.offset = slot.offset
                        sym.region = "local"  # o REG_LOCAL


    def _is_method(self, func_sym: FuncSymbol, func_scope) -> bool:
        """
        Somos un método si estamos dentro de una clase (via _current_class)
        o si el scope padre es de tipo 'class'.
        """
        if self._current_class:
            return True
        if len(self.scopes.stack) >= 2:
            parent = self.scopes.stack[-2]
            if getattr(parent, "kind", "") == "class":
                return True
        return False

    def visitReturnStatement(self, ctx):
        # Validar que estemos dentro de una función
        if not self.scopes.inside("function"):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_RETURN", "`return` fuera de una función.")
            # Evaluar expresión para no romper el recorrido
            if ctx.expression() is not None:
                self.visit(ctx.expression())
            return VOID

        # Evaluar el tipo retornado y regresarlo (visitFunctionDeclaration lo recolecta)
        ret_t = VOID
        if ctx.expression() is not None:
            ret_t = self.visit(ctx.expression()) or VOID
        return ret_t

    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        # patrón: term (('+'|'-') term)*
        t = self.visit(ctx.multiplicativeExpr(0)) or VOID
        n = len(ctx.multiplicativeExpr())
        # operadores están en posiciones impares de getChildren()
        # o puedes contar: hay n-1 operadores
        child_i = 1  # primer operador está en child 1
        for i in range(1, n):
            op = ctx.getChild(child_i).getText()  # '+' o '-'
            right_t = self.visit(ctx.multiplicativeExpr(i)) or VOID
            if op == "+":
                t2 = plus_type(t, right_t)
            else:
                t2 = arith_type(t, right_t)
            if t2 is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ARITH",
                                    f"Operación inválida: {t} {op} {right_t}")
                return VOID
            t = t2
            child_i += 2
        return t

    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        # patrón: factor (('*'|'/'|'%') factor)*
        t = self.visit(ctx.unaryExpr(0)) or VOID
        n = len(ctx.unaryExpr())
        child_i = 1
        for i in range(1, n):
            op = ctx.getChild(child_i).getText()
            right_t = self.visit(ctx.unaryExpr(i)) or VOID
            t2 = arith_type(t, right_t)
            if t2 is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ARITH",
                                    f"Operación inválida: {t} {op} {right_t}")
                return VOID
            t = t2
            child_i += 2
        return t

    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        # patrón: additive (('<'|'<='|'>'|'>=') additive)*
        if ctx.additiveExpr():
            t = self.visit(ctx.additiveExpr(0)) or VOID
            n = len(ctx.additiveExpr())
            child_i = 1
            for i in range(1, n):
                op = ctx.getChild(child_i).getText()
                right_t = self.visit(ctx.additiveExpr(i)) or VOID
                t2 = relational_type(t, right_t)
                if t2 is None:
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_REL",
                                        f"Operación relacional inválida: {t} {op} {right_t}")
                    return VOID
                t = t2  # sigue siendo BOOLEAN si llegó aquí
                child_i += 2
            return t
        return VOID

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        # patrón: relational (('=='|'!=') relational)*
        if ctx.relationalExpr():
            t = self.visit(ctx.relationalExpr(0)) or VOID
            n = len(ctx.relationalExpr())
            child_i = 1
            for i in range(1, n):
                op = ctx.getChild(child_i).getText()
                right_t = self.visit(ctx.relationalExpr(i)) or VOID
                t2 = equality_type(t, right_t)
                if t2 is None:
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_EQ",
                                        f"Comparación inválida: {t} {op} {right_t}")
                    return VOID
                t = t2  # BOOLEAN
                child_i += 2
            return t
        return VOID

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        if ctx.equalityExpr():
            t = self.visit(ctx.equalityExpr(0)) or VOID
            for e in ctx.equalityExpr()[1:]:
                right_t = self.visit(e) or VOID
                t2 = logical_type(t, right_t)  # ya valida boolean && boolean
                if t2 is None:
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_LOGIC",
                                        f"Operación lógica inválida: {t} && {right_t}")
                    return VOID
                t = t2
            return t
        return VOID

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        if ctx.logicalAndExpr():
            t = self.visit(ctx.logicalAndExpr(0)) or VOID
            for e in ctx.logicalAndExpr()[1:]:
                right_t = self.visit(e) or VOID
                t = logical_type(t, right_t) or VOID
            return t
        return VOID

    def visitCallExpr(self, ctx: CompiscriptParser.CallExprContext):
        # === 1. Recolectar tipos de argumentos ===
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                arg_t = self.visit(e) or VOID
                args.append(arg_t)

        # === 2. Subir al LHS (LeftHandSideContext) ===
        lhs_ctx = ctx.parentCtx
        if not isinstance(lhs_ctx, CompiscriptParser.LeftHandSideContext):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL", "Contexto inválido en llamada")
            return VOID

        # === 3. Obtener base_name de forma segura ===
        base_name = None
        if hasattr(lhs_ctx, "primaryAtom") and lhs_ctx.primaryAtom():
            atom = lhs_ctx.primaryAtom()
            if hasattr(atom, "Identifier") and atom.Identifier():
                base_name = atom.Identifier().getText()
            elif hasattr(atom, "ThisExpr") or atom.getText() == "this":
                base_name = "this"
            else:
                base_name = None

        # === 4. Caso: llamada simple (foo(args)) ===
        if len(lhs_ctx.suffixOp()) == 1 and lhs_ctx.suffixOp(0) == ctx and base_name is not None:
            sym = self.resolve_symbol(base_name, ctx.start.line, ctx.start.column)

            # Buscar también en scopes anidados
            if not sym:
                for scope in reversed(self.scopes.stack):
                    table = getattr(scope, "symbols", None)
                    if table and base_name in table and isinstance(table[base_name], FuncSymbol):
                        sym = table[base_name]
                        break

            if not sym or not isinstance(sym, FuncSymbol):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                    f"{base_name} no es una función válida o visible")
                return VOID

            # Validar tipos de argumentos
            if len(args) != len(sym.params):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                    f"Número incorrecto de argumentos en {base_name}")
            else:
                for i, (arg_t, param) in enumerate(zip(args, sym.params)):
                    if not can_assign(param.type, arg_t):
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                            f"Argumento {i} incompatible en {base_name}: {arg_t}, se esperaba {param.type}")

            return sym.type.ret if isinstance(sym.type, FunctionType) else sym.type

        # === 5. Caso: llamada de método (obj.metodo(args)) ===
        if len(lhs_ctx.suffixOp()) >= 2 and lhs_ctx.suffixOp()[-1] == ctx:
            prev_suffix = lhs_ctx.suffixOp()[-2]
            if isinstance(prev_suffix, CompiscriptParser.PropertyAccessExprContext):
                method_name = prev_suffix.Identifier().getText()
                obj_atom = lhs_ctx.primaryAtom()

                # --- soporte para this.metodo() ---
                if obj_atom.getText() == "this":
                    obj_type = Type(self._current_class) if self._current_class else VOID
                else:
                    obj_sym = self.resolve_symbol(obj_atom.getText(), ctx.start.line, ctx.start.column)
                    obj_type = obj_sym.type if obj_sym else VOID

                if obj_type == VOID:
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                        f"Objeto inválido en llamada a {method_name}")
                    return VOID

                class_sym = self.resolve_symbol(obj_type.name, ctx.start.line, ctx.start.column)
                if not isinstance(class_sym, ClassSymbol):
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                        f"{obj_type.name} no es una clase válida")
                    return VOID

                # Buscar método (recursivo por herencia)
                cur_class = class_sym
                method = None
                while isinstance(cur_class, ClassSymbol):
                    if method_name in cur_class.methods:
                        method = cur_class.methods[method_name]
                        break
                    if hasattr(cur_class, "base") and cur_class.base:
                        cur_class = self.resolve_symbol(cur_class.base, ctx.start.line, ctx.start.column)
                    else:
                        break

                if not method:
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                        f"Método {method_name} no definido en {obj_type.name}")
                    return VOID

                # Validar aridad y tipos
                if len(args) != len(method.params):
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                        f"Número incorrecto de argumentos en {obj_type.name}.{method_name}")
                else:
                    for i, (arg_t, param) in enumerate(zip(args, method.params)):
                        if not can_assign(param.type, arg_t):
                            self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                                f"Argumento {i} incompatible en {obj_type.name}.{method_name}: {arg_t} esperado {param.type}")

                return method.type.ret if isinstance(method.type, FunctionType) else method.type

        # === 6. Fallback ===
        self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                            f"Llamada inválida{f' en {base_name}' if base_name else ''}")
        return VOID



    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()

        if name == "integer": return INTEGER
        if name == "string": return STRING
        if name == "boolean": return BOOLEAN
        if name == "void": return VOID

        sym = self.resolve_symbol(name, ctx.start.line, ctx.start.column)
        if sym:
            if isinstance(sym, VarSymbol):
                # uso antes de inicializar
                if not sym.is_initialized and not sym.is_const:
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_UNINIT",
                                        f"Variable '{name}' usada antes de ser inicializada")
                return sym.type
            if isinstance(sym, ParamSymbol):
                return sym.type
            if isinstance(sym, FuncSymbol):
                return sym.type  
            if isinstance(sym, ClassSymbol):
                return sym.type

        return VOID

    def visitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        name = ctx.Identifier(0).getText()
        csym = ClassSymbol(name, type=Type(name),
                        line=ctx.start.line, col=ctx.start.column)
        csym.fields = {}
        csym.methods = {}
        if ctx.Identifier(1):
            csym.base = ctx.Identifier(1).getText()
        else:
            csym.base = None
        
        self.define_symbol(csym)

        prev = self._current_class
        self._current_class = name
        self.scopes.push_class(name)

        for member in ctx.classMember():
            if member.functionDeclaration():
                fname = member.functionDeclaration().Identifier().getText()
                ret_type = self.visit(member.functionDeclaration().type_()) if member.functionDeclaration().type_() else VOID

                params = []
                if member.functionDeclaration().parameters():
                    for i, p in enumerate(member.functionDeclaration().parameters().parameter()):
                        pname = p.Identifier().getText()
                        ptype = self.visit(p.type_()) if p.type_() else VOID
                        params.append(ParamSymbol(pname, ptype, i,
                                                 line=p.start.line, col=p.start.column))

                func_type = make_fn([p.type for p in params], ret_type)
                fsym = FuncSymbol(fname, type=func_type, params=tuple(params),
                                  line=member.start.line, col=member.start.column)
                csym.methods[fname] = fsym

                # PUSH del scope de función del método
                self.scopes.push_function(ret_type, fname)
                func_scope = self.scopes.current

                for psym in params:
                    self.define_symbol(psym)

                # RA para método (detectará THIS por _is_method)
                self._begin_function_layout(fsym, func_scope)

                # Cuerpo del método
                self.visit(member.functionDeclaration().block())

                # Offsets de locales del método
                self._finalize_function_layout(fsym, func_scope)

                # POP del scope de función
                self.scopes.pop()

            elif member.variableDeclaration():
                vname = member.variableDeclaration().Identifier().getText()
                vtype = self.visit(member.variableDeclaration().typeAnnotation().type_()) if member.variableDeclaration().typeAnnotation() else VOID
                vsym = VarSymbol(vname, vtype, is_const=False, is_initialized=False,
                                line=member.start.line, col=member.start.column)
                csym.fields[vname] = vsym
                self.define_symbol(vsym)

            elif member.constantDeclaration():
                cname = member.constantDeclaration().Identifier().getText()
                ctype = self.visit(member.constantDeclaration().typeAnnotation().type_()) if member.constantDeclaration().typeAnnotation() else VOID
                csym.fields[cname] = VarSymbol(cname, ctype, is_const=True, is_initialized=True,
                                            line=member.start.line, col=member.start.column)
                self.define_symbol(csym.fields[cname])

        # Calcula el desplazamiento base por herencia
        base_field_count = 0
        if csym.base:
            base_sym = self.resolve_symbol(csym.base, ctx.start.line, ctx.start.column)
            if isinstance(base_sym, ClassSymbol):
                base_field_count = len(base_sym.fields)

        # Asigna field_offset a los campos de ESTA clase por orden de declaración
        for i, (fname, fsym) in enumerate(csym.fields.items()):
            if isinstance(fsym, VarSymbol):
                fsym.field_offset = base_field_count + i

        self.scopes.pop()
        self._current_class = prev
        return None

    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        txt = ctx.getText()

        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
        if txt == "null":
            return NULL
        if txt in ("true", "false"):
            return BOOLEAN
        if txt.isdigit():
            return INTEGER
        if txt.startswith('"') and txt.endswith('"'):
            return STRING
        
        return VOID

    def visitArrayLiteral(self, ctx: CompiscriptParser.ArrayLiteralContext):
        elems = [self.visit(e) for e in ctx.expression()]

        if not elems:
            return make_array(VOID, 1)

        elem_type = elems[0]

        if all(isinstance(t, Type) and t.name.endswith("[]") for t in elems):
            base = elems[0]
            if isinstance(base, ArrayType):
                return make_array(base.elem, base.dims + 1)

        for t in elems[1:]:
            if not (can_assign(elem_type, t) and can_assign(t, elem_type)):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ARRAY_ELEM",
                                    f"Tipos incompatibles en arreglo: {elem_type} y {t}")
        return make_array(elem_type, 1)

    def visitThisExpr(self, ctx: CompiscriptParser.ThisExprContext):
        if not self._current_class:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_THIS",
                                "Uso de 'this' fuera de una clase")
            return VOID
        return Type(self._current_class)

    def visitNewExpr(self, ctx: CompiscriptParser.NewExprContext):
        class_name = ctx.Identifier().getText()

        sym = self.resolve_symbol(class_name, ctx.start.line, ctx.start.column)
        if not sym or not isinstance(sym, ClassSymbol):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                f"Clase no definida: {class_name}")
            return VOID

        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.visit(e) or VOID)

        ctor = sym.methods.get("constructor")
        if not ctor and hasattr(sym, "base") and sym.base:
            base_sym = self.resolve_symbol(sym.base, ctx.start.line, ctx.start.column)
            if isinstance(base_sym, ClassSymbol):
                ctor = base_sym.methods.get("constructor")

        if ctor and isinstance(ctor.type, FunctionType):
            if len(args) != len(ctor.params):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                    f"Número incorrecto de argumentos al construir {class_name}")
            else:
                for i, (arg_t, param) in enumerate(zip(args, ctor.params)):
                    if not can_assign(param.type, arg_t):
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                            f"Argumento {i} incompatible en constructor de {class_name}: {arg_t}, se esperaba {param.type}")
        else:
            if args:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                    f"Clase {class_name} no tiene constructor que reciba argumentos")

        return Type(class_name)

    def visitType(self, ctx: CompiscriptParser.TypeContext):
        base_txt = ctx.baseType().getText()

        if ctx.baseType().Identifier():
            elem = Type(ctx.baseType().Identifier().getText())
        elif base_txt == "integer":
            elem = INTEGER
        elif base_txt == "string":
            elem = STRING
        elif base_txt == "boolean":
            elem = BOOLEAN
        elif base_txt == "void":
            elem = VOID
        else:
            elem = VOID

        children = list(ctx.getChildren())
        dims = (len(children) - 1) // 2
        tipo_final = make_array(elem, dims) if dims > 0 else elem
        return tipo_final

    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        cond_t = self.visit(ctx.expression()) or VOID
        if cond_t != BOOLEAN:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_IF",
                                f"Condición de if debe ser boolean, no {cond_t}")

        # then
        self.visit(ctx.block(0))  # crea BlockScope vía visitBlock

        # else (opcional)
        if ctx.block(1):
            self.visit(ctx.block(1))  # crea BlockScope
        return None


    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        cond_t = self.visit(ctx.expression()) or VOID
        if cond_t != BOOLEAN:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_WHILE",
                                f"Condición de while debe ser boolean, no {cond_t}")
        self.scopes.push("loop")
        self.visit(ctx.block())  # BlockScope dentro del loop
        self.scopes.pop()
        return None


    def visitDoWhileStatement(self, ctx: CompiscriptParser.DoWhileStatementContext):
        self.scopes.push("loop")
        self.visit(ctx.block())  # BlockScope dentro del loop
        self.scopes.pop()

        cond_t = self.visit(ctx.expression()) or VOID
        if cond_t != BOOLEAN:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_DOWHILE",
                                f"Condición de do-while debe ser boolean, no {cond_t}")
        return None


    def visitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        self.scopes.push("loop")

        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())

        if ctx.expression(0):
            cond_t = self.visit(ctx.expression(0)) or VOID
            if cond_t != BOOLEAN:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_FOR",
                                    f"Condición de for debe ser boolean, no {cond_t}")

        if ctx.expression(1):
            self.visit(ctx.expression(1))

        self.visit(ctx.block())  # BlockScope dentro del loop
        self.scopes.pop()
        return None

    def visitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        iter_t = self.visit(ctx.expression()) or VOID
        if not is_array(iter_t):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_FOREACH",
                                f"foreach requiere un arreglo, no {iter_t}")
            elem_t = VOID
        else:
            elem_t = element_type(iter_t) or VOID

        var_name = ctx.Identifier().getText()
        sym = VarSymbol(var_name, elem_t, is_const=False, is_initialized=True,
                        line=ctx.start.line, col=ctx.start.column)
        self.define_symbol(sym)

        # tras self.define_symbol(sym)
        if self.scopes.inside("function") and self._current_func and self._current_func.activation_record:
            ar = self._current_func.activation_record
            ar.add_local(var_name)
            slot = ar.addr_of(var_name)
            if slot:
                sym.offset = slot.offset
                sym.region = "local"

        self.scopes.push("loop")
        self.visit(ctx.block())
        self.scopes.pop()
        return None

    def visitSwitchStatement(self, ctx: CompiscriptParser.SwitchStatementContext):
        control_t = self.visit(ctx.expression())
        self.scopes.push("switch")

        for case in ctx.switchCase():
            case_t = self.visit(case.expression())
            if not can_assign(control_t, case_t):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_SWITCH",
                                    f"case {case_t} incompatible con switch {control_t}")
            self.check_block_statements(case.statement(), ctx)

        if ctx.defaultCase():
            self.check_block_statements(ctx.defaultCase().statement(), ctx)

        self.scopes.pop()
        return None


    def visitBreakStatement(self, ctx: CompiscriptParser.BreakStatementContext):
        if not self.scopes.inside("loop") and not self.scopes.inside("switch"):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_BREAK",
                                "break solo se permite en bucles o switch")
        return None

    def visitContinueStatement(self, ctx: CompiscriptParser.ContinueStatementContext):
        if not self.scopes.inside("loop"):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_CONTINUE",
                                "continue solo se permite en bucles")
        return None

    def visitTryCatchStatement(self, ctx: CompiscriptParser.TryCatchStatementContext):
        self.visit(ctx.block(0))  

        self.scopes.push("catch")
        err_name = ctx.Identifier().getText()
        self.define_symbol(VarSymbol(err_name, STRING, is_const=False, is_initialized=True,
                                    line=ctx.start.line, col=ctx.start.column))
        self.visit(ctx.block(1))  
        self.scopes.pop()
        return None

    def visitIndexExpr(self, ctx: CompiscriptParser.IndexExprContext):
        """
        Maneja expresiones de indexación de arreglos, como:
            a[0], m[1][2], etc.

        Valida que el índice sea integer y que el objeto sea un arreglo.
        Soporta arreglos multidimensionales (integer[][] -> integer[] -> integer).
        """
        # === 1. Resolver el nombre base del arreglo ===
        lhs_ctx = ctx.parentCtx.primaryAtom()
        if lhs_ctx and lhs_ctx.Identifier():
            arr_name = lhs_ctx.Identifier().getText()
            arr_sym = self.resolve_symbol(arr_name, ctx.start.line, ctx.start.column)
            arr_t = arr_sym.type if arr_sym else VOID
        else:
            arr_t = VOID

        # === 2. Verificar el tipo del índice ===
        idx_t = self.visit(ctx.expression()) or VOID
        if idx_t != INTEGER:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_INDEX",
                                f"Índice debe ser integer, no {idx_t}")

        # === 3. Validar que el objeto sea un arreglo ===
        if not is_array(arr_t):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_INDEX",
                                f"El objeto {arr_t} no es indexable")
            return VOID

        # === 4. Si es un arreglo multidimensional, reducir una dimensión ===
        if isinstance(arr_t, ArrayType):
            # integer[][] → integer[]
            if arr_t.dims > 1:
                return make_array(arr_t.elem, arr_t.dims - 1)
            # integer[] → integer
            else:
                return arr_t.elem

        # === 5. Caso general (por compatibilidad con tipos antiguos) ===
        elem_t = element_type(arr_t) or VOID
        return elem_t




    def visitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        if ctx.getChildCount() == 2:  
            op = ctx.getChild(0).getText()
            t = self.visit(ctx.unaryExpr()) or VOID
            if op == "-" and t != INTEGER:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_UNARY",
                                    f"Operador '-' solo válido para integer, no {t}")
                return VOID
            if op == "!" and t != BOOLEAN:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_UNARY",
                                    f"Operador '!' solo válido para boolean, no {t}")
                return VOID
            return t
        else:
            return self.visit(ctx.primaryExpr()) or VOID


    def visitPropertyAccessExpr(self, ctx: CompiscriptParser.PropertyAccessExprContext):
        """
        Traduce expresiones del tipo:
            obj.prop
            this.prop
        y retorna el tipo del campo o método correspondiente.
        """
        lhs_ctx = ctx.parentCtx
        obj_t = VOID

        # === 1. Determinar el tipo del objeto base ===
        if isinstance(lhs_ctx, CompiscriptParser.LeftHandSideContext):
            if lhs_ctx.primaryAtom():
                atom = lhs_ctx.primaryAtom()
                txt = atom.getText()

                # Caso especial: this.prop
                if txt == "this":
                    if not self._current_class:
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_THIS",
                                            "Uso de 'this' fuera de una clase")
                        return VOID
                    obj_t = Type(self._current_class)
                elif hasattr(atom, "Identifier") and atom.Identifier():
                    base_name = atom.Identifier().getText()
                    sym = self.resolve_symbol(base_name, ctx.start.line, ctx.start.column)
                    obj_t = sym.type if isinstance(sym, VarSymbol) else VOID
                else:
                    obj_t = VOID

        prop_name = ctx.Identifier().getText()

        # === 2. Si el objeto es de tipo clase, buscar campo o método ===
        if isinstance(obj_t, Type):
            class_sym = self.resolve_symbol(obj_t.name, ctx.start.line, ctx.start.column)
            while isinstance(class_sym, ClassSymbol):
                # Buscar en campos
                if prop_name in class_sym.fields:
                    return class_sym.fields[prop_name].type
                # Buscar en métodos
                if prop_name in class_sym.methods:
                    return class_sym.methods[prop_name].type
                # Buscar en la clase base
                if hasattr(class_sym, "base") and class_sym.base:
                    class_sym = self.resolve_symbol(class_sym.base, ctx.start.line, ctx.start.column)
                else:
                    break

            # Si no se encontró el campo ni método
            self.reporter.report(ctx.start.line, ctx.start.column, "E_PROP",
                                f"Propiedad o método '{prop_name}' no definido en {obj_t.name}")
            return VOID

        # === 3. Si no es clase, error ===
        self.reporter.report(ctx.start.line, ctx.start.column, "E_PROP",
                            f"No se puede acceder a la propiedad '{prop_name}' de {obj_t}")
        return VOID

 
    def visitLeftHandSide(self, ctx: CompiscriptParser.LeftHandSideContext):
        t = self.visit(ctx.primaryAtom()) or VOID
        for suffix in ctx.suffixOp():
            res = self.visit(suffix)
            t = res
        return t

    def visitExpression(self, ctx: CompiscriptParser.ExpressionContext):
        return self.visit(ctx.assignmentExpr()) or VOID

    def visitAssignmentExpr(self, ctx: CompiscriptParser.AssignmentExprContext):
        if ctx.getChildCount() == 3 and ctx.getChild(1).getText() == "=":
            # Intentar detectar si lhs es un identificador simple para chequear const
            lhs = ctx.leftHandSide()
            lhs_id = None
            if lhs and lhs.primaryAtom() and lhs.primaryAtom().Identifier():
                lhs_id = lhs.primaryAtom().Identifier().getText()
            lhs_t = self.visit(lhs) or VOID
            rhs_t = self.visit(ctx.assignmentExpr()) or VOID

            # const en asignación expresiva
            if lhs_id is not None:
                sym = self.resolve_symbol(lhs_id, ctx.start.line, ctx.start.column)
                if isinstance(sym, VarSymbol) and sym.is_const:
                    self.reporter.report(ctx.start.line, ctx.start.column, "E_CONST",
                                        f"No se puede asignar a la constante '{lhs_id}'")
                else:
                    if isinstance(sym, VarSymbol):
                        sym.is_initialized = True

            if not can_assign(lhs_t, rhs_t):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                    f"No se puede asignar {rhs_t} a {lhs_t}")
            return lhs_t
        else:
            return self.visit(ctx.conditionalExpr()) or VOID

    def visitConditionalExpr(self, ctx: CompiscriptParser.ConditionalExprContext):
        if ctx.getChildCount() == 5:  
            cond_t = self.visit(ctx.logicalOrExpr()) or VOID
            if cond_t != BOOLEAN:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_TERNARY",
                                     f"Condición de operador ternario debe ser boolean, no {cond_t}")
            then_t = self.visit(ctx.expression(0)) or VOID
            else_t = self.visit(ctx.expression(1)) or VOID
            if can_assign(then_t, else_t):
                return then_t
            if can_assign(else_t, then_t):
                return else_t
            return VOID
        else:
            return self.visit(ctx.logicalOrExpr()) or VOID

    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr()) or VOID
        if ctx.leftHandSide():
            return self.visit(ctx.leftHandSide()) or VOID
        if ctx.expression():
            return self.visit(ctx.expression()) or VOID
        return VOID
    
    def check_block_statements(self, stmts, ctx):
        """
        Recorre un bloque y marca código muerto:
        - después de return
        - después de break
        - después de continue
        """
        has_terminated = False
        for stmt in stmts:
            if has_terminated:
                self.reporter.report(
                    stmt.start.line, stmt.start.column, "E_DEADCODE",
                    "Código muerto: esta instrucción nunca se ejecutará"
                )
            result = self.visit(stmt)

            if stmt.returnStatement() or stmt.breakStatement() or stmt.continueStatement():
                has_terminated = True

    @contextmanager
    def _block(self):
        """Crea un scope de bloque { ... }."""
        self.scopes.push("block")
        try:
            yield
        finally:
            self.scopes.pop()

    def visitBlock(self, ctx):
        with self._block():
            self.check_block_statements(ctx.statement(), ctx)
        return VOID

    @contextmanager
    def _loop(self):
        """Marca contexto de loop para validar break/continue."""
        self.scopes.push("loop")
        try:
            yield
        finally:
            self.scopes.pop()