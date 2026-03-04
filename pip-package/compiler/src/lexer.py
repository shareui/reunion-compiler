from typing import List
from .token import Token
from .tokenTypes import TokenType, KEYWORDS
from .errors import ReunionLexError


class Lexer:
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.lines = source.splitlines()

    def tokenize(self) -> List[Token]:
        self._checkMixedIndents()
        while self.pos < len(self.source):
            self._scanToken()
        self._emit(TokenType.EOF, "", self.line, self.col)
        return self.tokens

    def _checkMixedIndents(self) -> None:
        """Detect files that mix tabs and spaces for indentation."""
        has_space_indent = False
        has_tab_indent = False
        for lineno, line in enumerate(self.lines, 1):
            stripped = line.lstrip()
            if not stripped:
                continue
            indent = line[: len(line) - len(stripped)]
            if not indent:
                continue
            if " " in indent:
                has_space_indent = True
            if "	" in indent:
                has_tab_indent = True
            if has_space_indent and has_tab_indent:
                srcLine = self.lines[lineno - 1]
                raise ReunionLexError(
                    "Mixed indentation — file uses both spaces and tabs; pick one",
                    self.filename, lineno, 1, srcLine,
                )

    def _scanToken(self) -> None:
        two = self.source[self.pos:self.pos + 2]
        if two == "->":
            self._emitCurrent(TokenType.ARROW, "->", 2); return
        if two == "**":
            self._emitCurrent(TokenType.STARSTAR, "**", 2); return
        if two == "==":
            self._emitCurrent(TokenType.EQ, "==", 2); return
        if two == "!=":
            self._emitCurrent(TokenType.NEQ, "!=", 2); return
        if two == "<=":
            self._emitCurrent(TokenType.LTE, "<=", 2); return
        if two == ">=":
            self._emitCurrent(TokenType.GTE, ">=", 2); return

        if self._match("/*"):
            self._blockComment(); return

        # allow Python-style # comments (useful inside raw blocks)
        if self._current() == "#":
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                self.pos += 1
            return

        if two == "//":
            after = self.source[self.pos + 2:self.pos + 3]
            if after in ("", "\n") or after.isalpha() or after == "_":
                self._lineComment()
            else:
                self._emitCurrent(TokenType.SLASHSLASH, "//", 2)
            return

        ch = self._current()

        if ch in (" ", "\t", "\r", "\n"):
            if ch == "\n":
                self.line += 1
                self.col = 1
                self.pos += 1
            else:
                self._advance()
            return

        if self._peek3() in ('"""', "'''"):
            self._tripleString(self._peek3()[0]); return

        if ch in ('"', "'"):
            self._string(ch); return

        if ch.isdigit():
            self._number(); return

        if ch.isalpha() or ch == "_":
            self._identifier(); return

        single = {
            "(": TokenType.LPAREN, ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            ",": TokenType.COMMA, ":": TokenType.COLON,
            ";": TokenType.SEMICOLON, ".": TokenType.DOT,
            "=": TokenType.ASSIGN, "+": TokenType.PLUS,
            "-": TokenType.MINUS, "*": TokenType.STAR,
            "/": TokenType.SLASH, "%": TokenType.PERCENT,
            "<": TokenType.LT, ">": TokenType.GT,
        }
        if ch in single:
            self._emitCurrent(single[ch], ch, 1); return

        self._error(f"Unexpected character {ch!r}")

    def _tripleString(self, quote: str) -> None:
        startLine, startCol = self.line, self.col
        delim = quote * 3
        self.pos += 3; self.col += 3
        raw = []
        while self.pos < len(self.source):
            if self.source[self.pos:self.pos + 3] == delim:
                self.pos += 3; self.col += 3
                self._emitInterpolated("".join(raw), startLine, startCol)
                return
            ch = self.source[self.pos]
            if ch == "\n":
                raw.append(ch); self.pos += 1; self.line += 1; self.col = 1
            else:
                raw.append(ch); self.pos += 1; self.col += 1
        self._error("Unterminated triple-quoted string", line=startLine, col=startCol)

    def _string(self, quote: str) -> None:
        startLine, startCol = self.line, self.col
        self._advance()
        raw = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == "\n":
                self._error("Unterminated string literal", line=startLine, col=startCol)
            if ch == "\\":
                self._advance()
                if self.pos < len(self.source):
                    esc = self.source[self.pos]; self._advance()
                    _escapes = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"'}
                    raw.append(_escapes.get(esc, esc))
                continue
            if ch == quote:
                self._advance()
                self._emitInterpolated("".join(raw), startLine, startCol)
                return
            raw.append(ch); self._advance()
        self._error("Unterminated string literal", line=startLine, col=startCol)

    def _emitInterpolated(self, raw: str, line: int, col: int) -> None:
        parts = self._splitInterpolation(raw, line, col)
        if len(parts) == 1 and parts[0][0] == TokenType.STRING:
            self._emit(TokenType.STRING, parts[0][1], line, col)
        else:
            for ttype, value in parts:
                self._emit(ttype, value, line, col)

    def _splitInterpolation(self, raw: str, line: int, col: int) -> list[tuple[TokenType, str]]:
        parts: list[tuple[TokenType, str]] = []
        i = 0
        buf = []
        while i < len(raw):
            ch = raw[i]
            if ch == "$" and i + 1 < len(raw):
                next_ch = raw[i + 1]
                if next_ch == "{":
                    if buf:
                        parts.append((TokenType.STRING_PART, "".join(buf))); buf = []
                    i += 2; depth = 1; expr = []
                    while i < len(raw) and depth > 0:
                        c = raw[i]
                        if c == "{": depth += 1
                        elif c == "}":
                            depth -= 1
                            if depth == 0: i += 1; break
                        expr.append(c); i += 1
                    else:
                        self._error("Unclosed '${' in string interpolation", line=line, col=col)
                    parts.append((TokenType.INTERP_EXPR, "".join(expr))); continue
                elif next_ch.isalpha() or next_ch == "_":
                    if buf:
                        parts.append((TokenType.STRING_PART, "".join(buf))); buf = []
                    i += 1; ident = []
                    while i < len(raw) and (raw[i].isalnum() or raw[i] == "_"):
                        ident.append(raw[i]); i += 1
                    parts.append((TokenType.INTERP_EXPR, "".join(ident))); continue
            buf.append(ch); i += 1
        if buf:
            parts.append((TokenType.STRING, "".join(buf)))
        if not parts:
            parts.append((TokenType.STRING, ""))
        return parts

    def _number(self) -> None:
        startLine, startCol = self.line, self.col
        buf = []
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == "_"):
            buf.append(self.source[self.pos]); self._advance()
        if (self.pos < len(self.source) and self.source[self.pos] == "."
                and self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit()):
            buf.append("."); self._advance()
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                buf.append(self.source[self.pos]); self._advance()
        raw = "".join(buf).replace("_", "")
        value = float(raw) if "." in raw else int(raw)
        self._emit(TokenType.NUMBER, value, startLine, startCol)

    def _identifier(self) -> None:
        startLine, startCol = self.line, self.col
        buf = []
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
            buf.append(self.source[self.pos]); self._advance()
        word = "".join(buf)
        if word == "true":
            self._emit(TokenType.BOOL, True, startLine, startCol)
        elif word == "false":
            self._emit(TokenType.BOOL, False, startLine, startCol)
        elif word == "null":
            self._emit(TokenType.NULL, None, startLine, startCol)
        elif word in KEYWORDS:
            self._emit(TokenType.KEYWORD, word, startLine, startCol)
        else:
            self._emit(TokenType.IDENTIFIER, word, startLine, startCol)

    def _lineComment(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            self._advance()

    def _blockComment(self) -> None:
        startLine, startCol = self.line, self.col
        self.pos += 2; self.col += 2
        while self.pos < len(self.source):
            if self._match("*/"):
                return
            if self.source[self.pos] == "\n":
                self.line += 1; self.col = 1; self.pos += 1
            else:
                self.pos += 1; self.col += 1
        self._error("Unterminated block comment", line=startLine, col=startCol)

    def _current(self) -> str:
        return self.source[self.pos] if self.pos < len(self.source) else ""

    def _advance(self) -> str:
        ch = self.source[self.pos]; self.pos += 1
        if ch == "\n":
            self.line += 1; self.col = 1
        else:
            self.col += 1
        return ch

    def _match(self, s: str) -> bool:
        if self.source[self.pos:self.pos + len(s)] == s:
            self.pos += len(s); self.col += len(s); return True
        return False

    def _peek3(self) -> str:
        return self.source[self.pos:self.pos + 3]

    def _emit(self, ttype: TokenType, value, line: int, col: int) -> None:
        self.tokens.append(Token(ttype, value, line, col))

    def _emitCurrent(self, ttype: TokenType, value: str, length: int) -> None:
        self._emit(ttype, value, self.line, self.col)
        self.pos += length; self.col += length

    def _error(self, msg: str, line: int | None = None, col: int | None = None) -> None:
        l = line if line is not None else self.line
        c = col if col is not None else self.col
        srcLine = self.lines[l - 1] if 0 < l <= len(self.lines) else ""
        raise ReunionLexError(msg, self.filename, l, c, srcLine)
