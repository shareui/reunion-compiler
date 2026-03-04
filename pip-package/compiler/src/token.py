from dataclasses import dataclass
from typing import Any
from .tokenTypes import TokenType


@dataclass
class Token:
    type: TokenType
    value: Any          # raw lexeme or parsed value
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"
