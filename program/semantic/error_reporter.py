# program/semantic/error_reporter.py

from dataclasses import dataclass

@dataclass
class SemanticError:
    line: int
    col: int
    code: str
    msg: str

    def __str__(self):
        return f"[{self.line}:{self.col}] {self.code}: {self.msg}"


class ErrorReporter:
    """
    Recolector simple de errores semánticos.
    Cada error incluye: línea, columna, código y mensaje.
    """

    def __init__(self):
        self.errors: list[SemanticError] = []

    def report(self, line: int, col: int, code: str, msg: str):
        """
        Registra un error con su posición, código y mensaje.
        """
        self.errors.append(SemanticError(line, col, code, msg))

    def has_errors(self) -> bool:
        """True si se registraron errores."""
        return len(self.errors) > 0

    def count(self) -> int:
        """Número de errores registrados."""
        return len(self.errors)

    def clear(self):
        """Limpia la lista de errores."""
        self.errors.clear()

    def __iter__(self):
        return iter(self.errors)

    def __str__(self):
        if not self.errors:
            return " No hay errores."
        return "\n".join(str(e) for e in self.errors)
