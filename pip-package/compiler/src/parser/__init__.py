from .topParser import TopParser
from ..token import Token
from ..tokenTypes import TokenType


class Parser(TopParser):
    """
    Public entry point. Inherits the full pipeline:
    TopParser -> StmtParser -> ExprParser -> ParserBase
    """
    pass


__all__ = ["Parser"]
