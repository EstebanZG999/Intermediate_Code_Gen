import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from program.semantic.type_checker import TypeChecker
from program.semantic.error_reporter import ErrorReporter
from program.semantic.table import print_symbol_table


def main(argv):
    if len(argv) < 2:
        print("Uso: python Driver.py <archivo.cps>")
        return

    
    input_stream = FileStream(argv[1], encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)

    
    tree = parser.program()

    
    reporter = ErrorReporter()
    checker = TypeChecker(reporter)

    
    checker.visit(tree)

    
    if reporter.has_errors():
        print("\nErrores semánticos encontrados:")
        for e in reporter:
            print("   ", e)
    else:
        print("\nAnálisis semántico completado sin errores.")

    
    print_symbol_table(checker.scopes)


if __name__ == "__main__":
    main(sys.argv)
