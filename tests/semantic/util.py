from antlr4 import InputStream, CommonTokenStream
from program.CompiscriptLexer import CompiscriptLexer
from program.CompiscriptParser import CompiscriptParser
from program.semantic.type_checker import TypeChecker
from program.semantic.error_reporter import ErrorReporter
from program.semantic.scopes import GlobalScope

def compile_source(source: str):
    """
    Compila una cadena de código Compiscript y devuelve (reporter, checker).
    """
    input_stream = InputStream(source)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()

    reporter = ErrorReporter()
    checker = TypeChecker(reporter)

    checker.visit(tree)
    return reporter, checker
