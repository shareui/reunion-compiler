from .errorFormat import formatDiagnostic
# fixes from claude

class ReunionParseError(Exception):
    def __init__(self, message: str, filename: str, line: int, col: int,
                 source_line: str = "", length: int = 1):
        self.msg = message
        self.filename = filename
        self.line = line
        self.col = col
        self.source_line = source_line
        self.length = length
        super().__init__(self._format())

    def _format(self) -> str:
        return formatDiagnostic(
            kind="error",
            message=self.msg,
            filename=self.filename,
            line=self.line,
            col=self.col,
            source_line=self.source_line,
            length=self.length,
        )
