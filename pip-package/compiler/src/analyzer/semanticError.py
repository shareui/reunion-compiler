from dataclasses import dataclass, field
from ..errorFormat import formatDiagnostic


@dataclass
class SemanticError:
    message: str
    filename: str
    line: int
    col: int
    sourceLine: str = ""
    length: int = 1

    def format(self) -> str:
        return formatDiagnostic(
            kind="error",
            message=self.message,
            filename=self.filename,
            line=self.line,
            col=self.col,
            source_line=self.sourceLine,
            length=self.length,
        )

    def __str__(self) -> str:
        return self.format()


@dataclass
class SemanticWarning:
    message: str
    filename: str
    line: int
    col: int
    sourceLine: str = ""
    length: int = 1

    def format(self) -> str:
        return formatDiagnostic(
            kind="warning",
            message=self.message,
            filename=self.filename,
            line=self.line,
            col=self.col,
            source_line=self.sourceLine,
            length=self.length,
        )

    def __str__(self) -> str:
        return self.format()


class ReunionSemanticError(Exception):
    """Raised when analysis finds errors — wraps the list for clean CLI output."""
    def __init__(self, errors: list[SemanticError], warnings: list[SemanticWarning]):
        self.errors = errors
        self.warnings = warnings
        msg = "\n\n".join(e.format() for e in errors)
        super().__init__(msg)
