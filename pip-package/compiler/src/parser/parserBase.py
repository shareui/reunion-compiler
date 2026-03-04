from typing import List
from ..token import Token
from ..tokenTypes import TokenType
from ..parseError import ReunionParseError
# fixes from claude

class ParserBase:
    def __init__(self, tokens: List[Token], filename: str = "<stdin>", source: str = ""):
        self.tokens = tokens
        self.pos = 0
        self.filename = filename
        self.srcLines = source.splitlines() if source else []

    # ------------------------------------------------------------------
    # navigation
    # ------------------------------------------------------------------

    def _peek(self) -> Token:
        if self.pos >= len(self.tokens):
            last = self.tokens[-1] if self.tokens else Token(TokenType.EOF, "", 1, 1)
            return Token(TokenType.EOF, "", last.line, last.col)
        return self.tokens[self.pos]

    def _peekAt(self, offset: int) -> Token | None:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _check(self, ttype: TokenType) -> bool:
        return self._peek().type == ttype

    def _atEof(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _isKw(self, tok: Token, value: str) -> bool:
        return tok.type == TokenType.KEYWORD and tok.value == value

    # ------------------------------------------------------------------
    # consume / expect / error
    # ------------------------------------------------------------------

    def _consume(self, ttype: TokenType, value: str | None = None) -> Token:
        tok = self._peek()
        if tok.type == TokenType.EOF:
            expected = value or ttype.name
            self._error(f"Unexpected end of file — expected {expected!r}", tok)
        if tok.type != ttype:
            expected = value or ttype.name
            self._error(f"Expected {expected!r} but got {tok.value!r}", tok)
        if value is not None and tok.value != value:
            self._error(f"Expected {value!r} but got {tok.value!r}", tok)
        return self._advance()

    def _expect(self, ttype: TokenType, msg: str) -> Token:
        tok = self._peek()
        if tok.type == TokenType.EOF:
            self._error(f"Unexpected end of file — {msg}", tok)
        if tok.type != ttype:
            self._error(msg + f" (got {tok.value!r})", tok)
        return self._advance()

    def _error(self, msg: str, tok: Token | None = None) -> None:
        t = tok or self._peek()
        srcLine = self.srcLines[t.line - 1] if 0 < t.line <= len(self.srcLines) else ""
        length = len(str(t.value)) if t.value else 1
        raise ReunionParseError(msg, self.filename, t.line, t.col, srcLine, length)

    # ------------------------------------------------------------------
    # optional semicolon separator between statements
    # ------------------------------------------------------------------

    def _skipSemis(self) -> None:
        while self._check(TokenType.SEMICOLON):
            self._advance()

    # ------------------------------------------------------------------
    # block: { stmt* }
    # ------------------------------------------------------------------

    def _parseBlock(self) -> list:
        openBrace = self._consume(TokenType.LBRACE)
        self._skipSemis()
        stmts = []
        while not self._check(TokenType.RBRACE) and not self._atEof():
            stmts.extend(self._parseStatement())
            self._skipSemis()
        if self._atEof():
            self._error(
                f"Unclosed block — missing '}}' (opened at line {openBrace.line})",
                self._peek(),
            )
        self._consume(TokenType.RBRACE)
        return stmts

    # ------------------------------------------------------------------
    # parameters
    # ------------------------------------------------------------------

    def _parseParamList(self) -> list:
        from ..ast import ParamNode
        self._consume(TokenType.LPAREN)
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._parseParam())
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RPAREN):
                    break
                params.append(self._parseParam())
        self._consume(TokenType.RPAREN)
        return params

    def _parseParam(self):
        from ..ast import ParamNode
        tok = self._expect(TokenType.IDENTIFIER, "expected parameter name")
        default = None
        if self._check(TokenType.ASSIGN):
            self._advance()
            default = self._parseExpr()
        return ParamNode(name=tok.value, default=default, line=tok.line, col=tok.col)

    # forward declarations
    def _parseStatement(self) -> list:
        raise NotImplementedError

    def _parseExpr(self):
        raise NotImplementedError
