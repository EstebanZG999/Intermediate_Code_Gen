import sys
from antlr4 import *
from program.CompiscriptLexer import CompiscriptLexer
from program.CompiscriptParser import CompiscriptParser
from program.semantic.type_checker import TypeChecker
from program.semantic.error_reporter import ErrorReporter
from program.semantic.table import print_symbol_table
from program.ir.tac_builder import TACBuilder
from program.ir.tac_gen import TACGen


def compile_full_from_text(src: str):
    """
    Compila una cadena fuente:
    - Lex/Parse con ANTLR
    - TypeCheck
    - Si no hay errores: genera TAC y lo devuelve como texto
    Retorna: (reporter, scopes, tree, tac_text)
    """
    # Local imports para tolerar ubicaciones de los generados ANTLR
    try:
        from program.CompiscriptLexer import CompiscriptLexer
        from program.CompiscriptParser import CompiscriptParser
    except ModuleNotFoundError:
        # Plan B: generados en la raíz
        from CompiscriptLexer import CompiscriptLexer
        from CompiscriptParser import CompiscriptParser

    # Importa TACGen ahora, para que su import no falle cuando falten los ANTLR
    from program.ir.tac_gen import TACGen

    input_stream = InputStream(src)
    lexer = CompiscriptLexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    tree = parser.program()

    reporter = ErrorReporter()
    checker = TypeChecker(reporter)
    checker.visit(tree)

    tac_text = ""
    if not reporter.has_errors():
        builder = TACBuilder()
        # Usa la symtab que ya trae tu TypeChecker
        gen = TACGen(checker.symtab, builder)
        gen.visit(tree)
        tac_text = str(builder.tac)

    return reporter, checker.scopes, tree, tac_text

def main(argv):
    if len(argv) < 2:
        print("Uso: python Driver.py <archivo.cps>")
        return

    input_stream = FileStream(argv[1], encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)

    tree = parser.program()

    reporter = ErrorReporter()
    checker = TypeChecker(reporter)
    checker.visit(tree)

    if reporter.has_errors():
        print("\nErrores semánticos encontrados:")
        for e in reporter:
            print("   ", e)
        return

    print("\nAnálisis semántico completado sin errores.")

    # ✅ Usar la symtab del checker (ya trae offsets y ActivationRecord)
    print("\n=== Tabla de Símbolos (con offsets) ===")
    print_symbol_table(checker.scopes)  # si tu print usa scopes; si tienes uno que acepta symtab, úsalo

    # ✅ Generación de TAC usando la symtab del checker
    print("\n=== Generación de Código Intermedio (TAC) ===")
    builder = TACBuilder()
    gen = TACGen(checker.symtab, builder)   # ← usa la symtab del checker, no reconstruyas
    gen.visit(tree)
    print(builder.tac)

if __name__ == "__main__":
    main(sys.argv)
