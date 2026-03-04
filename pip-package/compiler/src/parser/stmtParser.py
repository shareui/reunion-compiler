from typing import Any
from .exprParser import ExprParser
from ..tokenTypes import TokenType
from ..ast import (
    FunNode, ValNode, VarNode, AssignNode, ReturnNode,
    BreakNode, ContinueNode, RaiseNode, CancelNode, ModifyNode, DefaultNode,
    IfNode, SwitchNode, ForNode, WhileNode, SusNode, SusHandlerNode,
    ExprStmtNode, HookDeclNode, HookSendMessageDeclNode,
)


class StmtParser(ExprParser):

    # ------------------------------------------------------------------
    # statement list — one or more statements, separated by optional ';'
    # ------------------------------------------------------------------

    def _parseStatement(self) -> list:
        stmts = [self._parseSingleStatement()]
        while self._check(TokenType.SEMICOLON):
            self._advance()
            # trailing semicolon before } is fine
            if self._check(TokenType.RBRACE) or self._atEof():
                break
            stmts.append(self._parseSingleStatement())
        return stmts

    def _parseSingleStatement(self) -> Any:
        tok = self._peek()

        if self._isKw(tok, "val"):      return self._parseVal()
        if self._isKw(tok, "var"):      return self._parseVar()
        if self._isKw(tok, "return"):   return self._parseReturn()
        if self._isKw(tok, "break"):
            self._advance()
            return BreakNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "continue"):
            self._advance()
            return ContinueNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "raise"):    return self._parseRaise()
        if self._isKw(tok, "cancel"):
            self._advance()
            return CancelNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "modify"):   return self._parseModify()
        if self._isKw(tok, "default"):
            self._advance()
            return DefaultNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "if"):       return self._parseIf()
        if self._isKw(tok, "switch"):   return self._parseSwitchStmt()
        if self._isKw(tok, "for"):      return self._parseFor()
        if self._isKw(tok, "while"):    return self._parseWhile()
        if self._isKw(tok, "sus"):      return self._parseSus()
        if self._isKw(tok, "hook"):     return self._parseHookDecl()
        if self._isKw(tok, "hook_send_message"):
            t = self._advance()
            return HookSendMessageDeclNode(line=t.line, col=t.col)
        if self._isKw(tok, "fun"):      return self._parseFun()

        return self._parseAssignOrExpr()

    # ------------------------------------------------------------------
    # variable declarations
    # ------------------------------------------------------------------

    def _parseVal(self) -> ValNode:
        tok = self._consume(TokenType.KEYWORD, "val")
        name = self._expect(TokenType.IDENTIFIER, "expected variable name after 'val'").value
        self._consume(TokenType.ASSIGN)
        value = self._parseExpr()
        return ValNode(name=name, value=value, line=tok.line, col=tok.col)

    def _parseVar(self) -> VarNode:
        tok = self._consume(TokenType.KEYWORD, "var")
        name = self._expect(TokenType.IDENTIFIER, "expected variable name after 'var'").value
        self._consume(TokenType.ASSIGN)
        value = self._parseExpr()
        return VarNode(name=name, value=value, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # control flow
    # ------------------------------------------------------------------

    def _parseReturn(self) -> ReturnNode:
        tok = self._consume(TokenType.KEYWORD, "return")
        value = None
        # no value if next is } ; EOF or a statement-starting keyword
        if not self._check(TokenType.RBRACE) and not self._check(TokenType.SEMICOLON) and not self._atEof():
            value = self._parseExpr()
        return ReturnNode(value=value, line=tok.line, col=tok.col)

    def _parseRaise(self) -> RaiseNode:
        tok = self._consume(TokenType.KEYWORD, "raise")
        value = self._parseExpr()
        return RaiseNode(value=value, line=tok.line, col=tok.col)

    def _parseModify(self) -> ModifyNode:
        tok = self._consume(TokenType.KEYWORD, "modify")
        target = self._expect(TokenType.IDENTIFIER, "expected 'request' or 'params' after 'modify'").value
        return ModifyNode(target=target, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # assignment vs expression statement
    # ------------------------------------------------------------------

    def _parseAssignOrExpr(self) -> Any:
        expr = self._parseExpr()
        if self._check(TokenType.ASSIGN):
            self._advance()
            value = self._parseExpr()
            return AssignNode(target=expr, value=value, line=expr.line, col=expr.col)
        return ExprStmtNode(expr=expr, line=expr.line, col=expr.col)

    def _parseExprStmt(self) -> ExprStmtNode:
        expr = self._parseExpr()
        return ExprStmtNode(expr=expr, line=expr.line, col=expr.col)

    # ------------------------------------------------------------------
    # if / switch / for / while
    # ------------------------------------------------------------------

    def _parseIf(self) -> IfNode:
        tok = self._consume(TokenType.KEYWORD, "if")
        cond = self._parseExpr()
        thenBody = self._parseBlock()
        elseIfs = []
        elseBody = []
        while self._isKw(self._peek(), "else"):
            self._advance()
            if self._isKw(self._peek(), "if"):
                self._advance()
                eic = self._parseExpr()
                eib = self._parseBlock()
                elseIfs.append((eic, eib))
            else:
                elseBody = self._parseBlock()
                break
        return IfNode(condition=cond, thenBody=thenBody, elseIfs=elseIfs,
                      elseBody=elseBody, line=tok.line, col=tok.col)

    def _parseSwitchStmt(self) -> SwitchNode:
        tok = self._consume(TokenType.KEYWORD, "switch")
        subject = self._parseExpr()
        self._consume(TokenType.LBRACE)
        self._skipSemis()
        cases, elseBody = self._parseSwitchCases()
        self._consume(TokenType.RBRACE)
        return SwitchNode(subject=subject, cases=cases, elseBody=elseBody,
                          line=tok.line, col=tok.col)

    def _parseFor(self) -> ForNode:
        tok = self._consume(TokenType.KEYWORD, "for")
        targets = [self._expect(TokenType.IDENTIFIER, "expected loop variable").value]
        if self._check(TokenType.COMMA):
            self._advance()
            targets.append(self._expect(TokenType.IDENTIFIER, "expected second loop variable").value)
        self._consume(TokenType.KEYWORD, "in")
        iterable = self._parseExpr()
        body = self._parseBlock()
        return ForNode(targets=targets, iterable=iterable, body=body,
                       line=tok.line, col=tok.col)

    def _parseWhile(self) -> WhileNode:
        tok = self._consume(TokenType.KEYWORD, "while")
        cond = self._parseExpr()
        body = self._parseBlock()
        return WhileNode(condition=cond, body=body, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # sus / try / finally
    # ------------------------------------------------------------------

    def _parseSus(self) -> SusNode:
        tok = self._consume(TokenType.KEYWORD, "sus")
        body = self._parseBlock()
        handlers = []
        finallyBody = []
        while self._isKw(self._peek(), "try"):
            self._advance()
            excType = None
            asName = None
            if not self._check(TokenType.LBRACE):
                excType = self._parseExpr()
                if self._isKw(self._peek(), "as"):
                    self._advance()
                    asName = self._expect(TokenType.IDENTIFIER, "expected name after 'as'").value
            hBody = self._parseBlock()
            handlers.append(SusHandlerNode(excType=excType, asName=asName,
                                           body=hBody, line=tok.line, col=tok.col))
        if self._isKw(self._peek(), "finally"):
            self._advance()
            finallyBody = self._parseBlock()
        return SusNode(body=body, handlers=handlers, finallyBody=finallyBody,
                       line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # hook declarations
    # ------------------------------------------------------------------

    def _parseHookDecl(self) -> HookDeclNode:
        tok = self._consume(TokenType.KEYWORD, "hook")
        nameTok = self._expect(TokenType.STRING, "expected hook name string after 'hook'")
        return HookDeclNode(hookName=nameTok.value, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # functions
    # ------------------------------------------------------------------

    def _parseFun(self) -> FunNode:
        tok = self._consume(TokenType.KEYWORD, "fun")
        name = self._expect(TokenType.IDENTIFIER, "expected function name").value
        params, body, inline = self._parseFunFull()
        return FunNode(name=name, params=params, body=body, inlineExpr=inline,
                       line=tok.line, col=tok.col)

    def _parseFunFull(self):
        params = self._parseParamList()
        if self._check(TokenType.ASSIGN):
            self._advance()
            expr = self._parseExpr()
            return params, [], expr
        body = self._parseBlock()
        return params, body, None
