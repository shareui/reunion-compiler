from typing import Any
from .parserBase import ParserBase
from ..tokenTypes import TokenType
from ..ast import (
    IdentNode, NumberNode, StringNode, BoolNode, NullNode,
    ListNode, DictNode, SetNode,
    BinaryOpNode, UnaryOpNode, CallNode, ArgNode,
    IndexNode, SliceNode, MemberNode, LambdaNode,
    IfExprNode, SwitchExprNode, SwitchCaseNode,
)

# fixes from claude
class ExprParser(ParserBase):

    # ------------------------------------------------------------------
    # precedence climbing
    # ------------------------------------------------------------------

    def _parseExpr(self) -> Any:
        return self._parseOr()

    def _parseOr(self) -> Any:
        left = self._parseAnd()
        while self._isKw(self._peek(), "or"):
            op = self._advance().value
            right = self._parseAnd()
            left = BinaryOpNode(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _parseAnd(self) -> Any:
        left = self._parseNot()
        while self._isKw(self._peek(), "and"):
            op = self._advance().value
            right = self._parseNot()
            left = BinaryOpNode(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _parseNot(self) -> Any:
        tok = self._peek()
        if self._isKw(tok, "not"):
            self._advance()
            operand = self._parseNot()
            return UnaryOpNode(op="not", operand=operand, line=tok.line, col=tok.col)
        return self._parseComparison()

    def _parseComparison(self) -> Any:
        left = self._parseIn()
        cmpOps = {
            TokenType.EQ: "==", TokenType.NEQ: "!=",
            TokenType.LT: "<",  TokenType.GT: ">",
            TokenType.LTE: "<=", TokenType.GTE: ">=",
        }
        while self._peek().type in cmpOps:
            op = cmpOps[self._advance().type]
            right = self._parseIn()
            left = BinaryOpNode(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _parseIn(self) -> Any:
        left = self._parseAddSub()
        tok = self._peek()
        if self._isKw(tok, "in"):
            self._advance()
            right = self._parseAddSub()
            return BinaryOpNode(op="in", left=left, right=right, line=left.line, col=left.col)
        if self._isKw(tok, "not"):
            nxt = self._peekAt(1)
            if nxt and self._isKw(nxt, "in"):
                self._advance(); self._advance()
                right = self._parseAddSub()
                return BinaryOpNode(op="not in", left=left, right=right, line=left.line, col=left.col)
        return left

    def _parseAddSub(self) -> Any:
        left = self._parseMulDiv()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            right = self._parseMulDiv()
            left = BinaryOpNode(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _parseMulDiv(self) -> Any:
        left = self._parseUnary()
        mulOps = {
            TokenType.STAR: "*", TokenType.SLASH: "/",
            TokenType.PERCENT: "%", TokenType.STARSTAR: "**",
            TokenType.SLASHSLASH: "//",
        }
        while self._peek().type in mulOps:
            op = mulOps[self._advance().type]
            right = self._parseUnary()
            left = BinaryOpNode(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _parseUnary(self) -> Any:
        tok = self._peek()
        if tok.type == TokenType.MINUS:
            self._advance()
            operand = self._parseUnary()
            return UnaryOpNode(op="-", operand=operand, line=tok.line, col=tok.col)
        return self._parsePostfix()

    # ------------------------------------------------------------------
    # postfix: calls, member access, indexing
    # ------------------------------------------------------------------

    def _parsePostfix(self) -> Any:
        expr = self._parsePrimary()
        while True:
            tok = self._peek()
            if tok.type == TokenType.DOT:
                self._advance()
                # allow keywords as member names (e.g. obj.text, obj.type, obj.message)
                attrTok = self._peek()
                if attrTok.type in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    self._advance()
                    attr = attrTok.value
                else:
                    raise self._error(attrTok, "expected attribute name after '.'")
                expr = MemberNode(obj=expr, attr=attr, line=tok.line, col=tok.col)
            elif tok.type == TokenType.LPAREN:
                args = self._parseArgList()
                expr = CallNode(callee=expr, args=args, line=tok.line, col=tok.col)
            elif tok.type == TokenType.LBRACKET:
                self._advance()
                # support empty-start slice [:end]
                if self._check(TokenType.COLON):
                    self._advance()
                    if self._check(TokenType.RBRACKET):
                        # full slice [:]
                        self._consume(TokenType.RBRACKET)
                        expr = SliceNode(obj=expr, start=None, end=None, line=tok.line, col=tok.col)
                    else:
                        end = self._parseExpr()
                        self._consume(TokenType.RBRACKET)
                        expr = SliceNode(obj=expr, start=None, end=end, line=tok.line, col=tok.col)
                else:
                    idx = self._parseExpr()
                    if self._check(TokenType.COLON):
                        self._advance()
                        if self._check(TokenType.RBRACKET):
                            # slice with empty end: [n:]
                            self._consume(TokenType.RBRACKET)
                            expr = SliceNode(obj=expr, start=idx, end=None, line=tok.line, col=tok.col)
                        else:
                            end = self._parseExpr()
                            self._consume(TokenType.RBRACKET)
                            expr = SliceNode(obj=expr, start=idx, end=end, line=tok.line, col=tok.col)
                    else:
                        self._consume(TokenType.RBRACKET)
                        expr = IndexNode(obj=expr, index=idx, line=tok.line, col=tok.col)
            else:
                break
        return expr

    def _parseArgList(self) -> list:
        self._consume(TokenType.LPAREN)
        args = []
        if not self._check(TokenType.RPAREN):
            args.append(self._parseArg())
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RPAREN):
                    break
                args.append(self._parseArg())
        self._consume(TokenType.RPAREN)
        return args

    def _parseArg(self) -> ArgNode:
        tok = self._peek()
        if tok.type == TokenType.IDENTIFIER and self._peekAt(1) and self._peekAt(1).type == TokenType.ASSIGN:
            name = self._advance().value
            self._advance()  # =
            val = self._parseExpr()
            return ArgNode(value=val, keyword=name, line=tok.line, col=tok.col)
        val = self._parseExpr()
        return ArgNode(value=val, keyword=None, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # primary
    # ------------------------------------------------------------------

    def _parsePrimary(self) -> Any:
        tok = self._peek()

        if tok.type == TokenType.LPAREN and self._looksLikeLambda():
            return self._parseLambda()

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parseExpr()
            self._consume(TokenType.RPAREN)
            return expr

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberNode(value=tok.value, line=tok.line, col=tok.col)

        if tok.type in (TokenType.STRING, TokenType.STRING_PART, TokenType.INTERP_EXPR):
            return self._parseStringLiteral()

        if tok.type == TokenType.BOOL:
            self._advance()
            return BoolNode(value=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.NULL:
            self._advance()
            return NullNode(line=tok.line, col=tok.col)

        if tok.type == TokenType.LBRACKET:
            return self._parseList()

        if tok.type == TokenType.LBRACE:
            return self._parseDictOrSet()

        if self._isKw(tok, "if"):
            return self._parseIfExpr()

        if self._isKw(tok, "switch"):
            return self._parseSwitchExpr()

        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return IdentNode(name=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.KEYWORD:
            self._advance()
            return IdentNode(name=tok.value, line=tok.line, col=tok.col)

        self._error(f"Unexpected token {tok.value!r} in expression", tok)

    # ------------------------------------------------------------------
    # string literals with interpolation
    # ------------------------------------------------------------------

    def _parseStringLiteral(self) -> StringNode:
        tok = self._peek()
        parts = []
        while self._peek().type in (TokenType.STRING, TokenType.STRING_PART, TokenType.INTERP_EXPR):
            t = self._advance()
            if t.type == TokenType.INTERP_EXPR:
                from ..lexer import Lexer
                innerTokens = Lexer(t.value, self.filename).tokenize()
                innerParser = self.__class__(innerTokens, self.filename)
                parts.append(innerParser._parseExpr())
            else:
                parts.append(t.value)
        return StringNode(parts=parts, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # collections
    # ------------------------------------------------------------------

    def _parseList(self) -> ListNode:
        tok = self._consume(TokenType.LBRACKET)
        elements = []
        if not self._check(TokenType.RBRACKET):
            elements.append(self._parseExpr())
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACKET):
                    break
                elements.append(self._parseExpr())
        self._consume(TokenType.RBRACKET)
        return ListNode(elements=elements, line=tok.line, col=tok.col)

    def _parseDictOrSet(self) -> Any:
        tok = self._consume(TokenType.LBRACE)
        if self._check(TokenType.RBRACE):
            self._advance()
            return DictNode(pairs=[], line=tok.line, col=tok.col)
        first = self._parseExpr()
        if self._check(TokenType.COLON):
            self._advance()
            val = self._parseExpr()
            pairs = [(first, val)]
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACE):
                    break
                k = self._parseExpr()
                self._consume(TokenType.COLON)
                v = self._parseExpr()
                pairs.append((k, v))
            self._consume(TokenType.RBRACE)
            return DictNode(pairs=pairs, line=tok.line, col=tok.col)
        else:
            elements = [first]
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RBRACE):
                    break
                elements.append(self._parseExpr())
            self._consume(TokenType.RBRACE)
            return SetNode(elements=elements, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # if-expr, switch-expr, lambda
    # ------------------------------------------------------------------

    def _parseIfExpr(self) -> IfExprNode:
        tok = self._consume(TokenType.KEYWORD, "if")
        cond = self._parseExpr()
        self._consume(TokenType.KEYWORD, "then")
        thenVal = self._parseExpr()
        self._consume(TokenType.KEYWORD, "else")
        elseVal = self._parseExpr()
        return IfExprNode(condition=cond, thenVal=thenVal, elseVal=elseVal,
                          line=tok.line, col=tok.col)

    def _parseSwitchExpr(self) -> SwitchExprNode:
        tok = self._consume(TokenType.KEYWORD, "switch")
        subject = self._parseExpr()
        self._consume(TokenType.LBRACE)
        self._skipSemis()
        cases, elseBody = self._parseSwitchCases()
        self._consume(TokenType.RBRACE)
        elseVal = elseBody[0] if elseBody else None
        return SwitchExprNode(subject=subject, cases=cases, elseVal=elseVal,
                              line=tok.line, col=tok.col)

    def _parseLambda(self) -> LambdaNode:
        tok = self._peek()
        params = self._parseParamList()
        self._consume(TokenType.ARROW)
        # multi-statement lambda body uses { }
        if self._check(TokenType.LBRACE):
            body = self._parseBlock()
            return LambdaNode(params=params, body=body, line=tok.line, col=tok.col)
        body = self._parseExpr()
        return LambdaNode(params=params, body=body, line=tok.line, col=tok.col)

    def _looksLikeLambda(self) -> bool:
        i = self.pos + 1
        depth = 1
        while i < len(self.tokens):
            t = self.tokens[i]
            if t.type == TokenType.LPAREN:
                depth += 1
            elif t.type == TokenType.RPAREN:
                depth -= 1
                if depth == 0:
                    nxt = self.tokens[i + 1] if i + 1 < len(self.tokens) else None
                    return nxt is not None and nxt.type == TokenType.ARROW
            i += 1
        return False

    # ------------------------------------------------------------------
    # switch cases (shared between stmt and expr switch)
    # ------------------------------------------------------------------

    def _parseSwitchCases(self):
        cases = []
        elseBody = []
        while not self._check(TokenType.RBRACE) and not self._atEof():
            tok = self._peek()
            if self._isKw(tok, "else"):
                self._advance()
                self._consume(TokenType.ARROW)
                if self._check(TokenType.LBRACE):
                    elseBody = self._parseBlock()
                else:
                    elseBody = [self._parseSingleStatement()]
                self._skipSemis()
                break
            patterns = [self._parseExpr()]
            while self._check(TokenType.COMMA):
                self._advance()
                patterns.append(self._parseExpr())
            self._consume(TokenType.ARROW)
            if self._check(TokenType.LBRACE):
                body = self._parseBlock()
            else:
                body = [self._parseSingleStatement()]
            cases.append(SwitchCaseNode(patterns=patterns, body=body,
                                        line=tok.line, col=tok.col))
            self._skipSemis()
        return cases, elseBody

    def _parseSingleStatement(self):
        raise NotImplementedError
