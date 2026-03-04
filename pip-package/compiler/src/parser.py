from typing import List, Any
from .token import Token
from .tokenTypes import TokenType
from .parseError import ReunionParseError
from .ast import (
    ProgramNode, MetainfoNode, ImportNode, RawNode, FunNode, ParamNode,
    PluginNode, HookDeclNode, HookSendMessageDeclNode,
    PreRequestNode, PostRequestNode, OnSendMessageNode,
    MethodHookNode, MethodReplaceNode, MenuItemNode,
    SettingsNode, SwitchSettingNode, InputSettingNode,
    SelectorSettingNode, EditTextNode, HeaderNode, DividerNode, TextItemNode,
    ValNode, VarNode, AssignNode, ReturnNode, BreakNode, ContinueNode,
    RaiseNode, CancelNode, ModifyNode, DefaultNode,
    IfNode, SwitchNode, SwitchCaseNode, ForNode, WhileNode,
    SusNode, SusHandlerNode, ExprStmtNode,
    IdentNode, NumberNode, StringNode, BoolNode, NullNode,
    ListNode, DictNode, SetNode,
    BinaryOpNode, UnaryOpNode, CallNode, ArgNode,
    IndexNode, SliceNode, MemberNode, LambdaNode,
    IfExprNode, SwitchExprNode,
)
# fixes from claude

class Parser:
    def __init__(self, tokens: List[Token], filename: str = "<stdin>", source: str = ""):
        # strip EOF for easier lookahead, keep it at end
        self.tokens = tokens
        self.pos = 0
        self.filename = filename
        self.srcLines = source.splitlines() if source else []

    # ------------------------------------------------------------------
    # public entry point
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        children = []
        self._skipNewlines()
        while not self._atEof():
            children.append(self._parseTopLevel())
            self._skipNewlines()
        return ProgramNode(children=children, line=1, col=1)

    # ------------------------------------------------------------------
    # top-level dispatching
    # ------------------------------------------------------------------

    def _parseTopLevel(self) -> Any:
        tok = self._peek()

        if self._isKw(tok, "metainfo"):
            return self._parseMetainfo()
        if self._isKw(tok, "import"):
            return self._parseImport()
        if self._isKw(tok, "raw"):
            return self._parseRaw()
        if self._isKw(tok, "plugin"):
            return self._parsePlugin()
        if self._isKw(tok, "settings"):
            return self._parseSettings()
        if self._isKw(tok, "fun"):
            return self._parseFun()
        if self._isKw(tok, "val"):
            return self._parseVal()
        if self._isKw(tok, "var"):
            return self._parseVar()
        if self._isKw(tok, "if"):
            return self._parseIf()
        if self._isKw(tok, "while"):
            return self._parseWhile()
        if self._isKw(tok, "for"):
            return self._parseFor()
        if self._isKw(tok, "sus"):
            return self._parseSus()
        if self._isKw(tok, "switch"):
            return self._parseSwitchStmt()

        return self._parseExprStmt()

    # ------------------------------------------------------------------
    # metainfo
    # ------------------------------------------------------------------

    def _parseMetainfo(self) -> MetainfoNode:
        tok = self._consume(TokenType.KEYWORD, "metainfo")
        self._consume(TokenType.LBRACE)
        self._skipNewlines()
        self._skipIndentDedent()
        fields = {}
        while not self._check(TokenType.RBRACE) and not self._atEof():
            keyTok = self._peek()
            if keyTok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                self._error("expected field name in metainfo", keyTok)
            self._advance()
            self._consume(TokenType.COLON)
            val = self._parseExpr()
            fields[keyTok.value] = val
            self._skipNewlines()
            self._skipIndentDedent()
        self._consume(TokenType.RBRACE)
        return MetainfoNode(fields=fields, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # import
    # ------------------------------------------------------------------

    def _parseImport(self) -> ImportNode:
        tok = self._consume(TokenType.KEYWORD, "import")
        # module name may contain dots: base_plugin, ui.settings etc
        # parts can be IDENTIFIER or KEYWORD (e.g. "settings")
        firstPart = self._peek()
        if firstPart.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
            self._error("expected module name", firstPart)
        module = self._advance().value
        while self._check(TokenType.DOT):
            self._advance()
            partTok = self._peek()
            if partTok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                self._error("expected identifier after '.'", partTok)
            module += "." + self._advance().value
        names = []
        if self._check(TokenType.LPAREN):
            self._advance()
            names.append(self._expect(TokenType.IDENTIFIER, "expected name").value)
            while self._check(TokenType.COMMA):
                self._advance()
                names.append(self._expect(TokenType.IDENTIFIER, "expected name").value)
            self._consume(TokenType.RPAREN)
        self._consumeNewline()
        return ImportNode(module=module, names=names, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # raw block
    # ------------------------------------------------------------------

    def _parseRaw(self) -> RawNode:
        tok = self._consume(TokenType.KEYWORD, "raw")
        self._consumeNewline()
        self._consume(TokenType.INDENT)
        lines = []
        while not self._check(TokenType.DEDENT) and not self._atEof():
            # collect everything until DEDENT as raw text
            lineParts = []
            while not self._check(TokenType.NEWLINE) and not self._check(TokenType.DEDENT) and not self._atEof():
                lineParts.append(str(self._advance().value))
            lines.append(" ".join(lineParts))
            if self._check(TokenType.NEWLINE):
                self._advance()
        self._consume(TokenType.DEDENT)
        return RawNode(code="\n".join(lines), line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # plugin block
    # ------------------------------------------------------------------

    def _parsePlugin(self) -> PluginNode:
        tok = self._consume(TokenType.KEYWORD, "plugin")
        name = self._expect(TokenType.IDENTIFIER, "expected plugin name").value
        self._consumeNewline()
        self._consume(TokenType.INDENT)
        self._skipNewlines()
        body = []
        while not self._check(TokenType.DEDENT) and not self._atEof():
            body.append(self._parsePluginMember())
            self._skipNewlines()
        self._consume(TokenType.DEDENT)
        return PluginNode(name=name, body=body, line=tok.line, col=tok.col)

    def _parsePluginMember(self) -> Any:
        tok = self._peek()
        if self._isKw(tok, "fun"):
            return self._parseFun()
        if self._isKw(tok, "hook"):
            return self._parseHookDecl()
        if self._isKw(tok, "hook_send_message"):
            t = self._advance()
            self._consumeNewline()
            return HookSendMessageDeclNode(line=t.line, col=t.col)
        if self._isKw(tok, "method_hook"):
            return self._parseMethodHook()
        if self._isKw(tok, "method_replace"):
            return self._parseMethodReplace()
        if self._isKw(tok, "menu_item"):
            return self._parseMenuItem()
        if self._isKw(tok, "val"):
            return self._parseVal()
        if self._isKw(tok, "var"):
            return self._parseVar()
        return self._parseExprStmt()

    def _parseHookDecl(self) -> HookDeclNode:
        tok = self._consume(TokenType.KEYWORD, "hook")
        nameTok = self._expect(TokenType.STRING, "expected hook name string after 'hook'")
        self._consumeNewline()
        return HookDeclNode(hookName=nameTok.value, line=tok.line, col=tok.col)

    def _parseMethodHook(self) -> MethodHookNode:
        tok = self._consume(TokenType.KEYWORD, "method_hook")
        name = self._expect(TokenType.IDENTIFIER, "expected method_hook class name").value
        params, body = self._parseFunParamsAndBody()
        return MethodHookNode(name=name, params=params, body=body, line=tok.line, col=tok.col)

    def _parseMethodReplace(self) -> MethodReplaceNode:
        tok = self._consume(TokenType.KEYWORD, "method_replace")
        name = self._expect(TokenType.IDENTIFIER, "expected method_replace class name").value
        params, body = self._parseFunParamsAndBody()
        return MethodReplaceNode(name=name, params=params, body=body, line=tok.line, col=tok.col)

    def _parseMenuItem(self) -> MenuItemNode:
        tok = self._consume(TokenType.KEYWORD, "menu_item")
        self._consumeNewline()
        self._consume(TokenType.INDENT)
        self._skipNewlines()
        fields = self._parseFieldBlock()
        self._consume(TokenType.DEDENT)
        return MenuItemNode(fields=fields, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # settings block
    # ------------------------------------------------------------------

    def _parseSettings(self) -> SettingsNode:
        tok = self._consume(TokenType.KEYWORD, "settings")
        self._consumeNewline()
        self._consume(TokenType.INDENT)
        self._skipNewlines()
        items = []
        while not self._check(TokenType.DEDENT) and not self._atEof():
            items.append(self._parseSettingItem())
            self._skipNewlines()
        self._consume(TokenType.DEDENT)
        return SettingsNode(items=items, line=tok.line, col=tok.col)

    def _parseSettingItem(self) -> Any:
        tok = self._peek()
        if self._isKw(tok, "switch"):
            return self._parseSwitchSetting()
        if self._isKw(tok, "input"):
            return self._parseInputSetting()
        if self._isKw(tok, "selector"):
            return self._parseSelectorSetting()
        if self._isKw(tok, "edit_text"):
            return self._parseEditText()
        if self._isKw(tok, "header"):
            return self._parseHeader()
        if self._isKw(tok, "divider"):
            return self._parseDivider()
        if self._isKw(tok, "text"):
            return self._parseTextItem()
        self._error(f"Unknown setting item: {tok.value!r}", tok)

    def _parseSwitchSetting(self) -> SwitchSettingNode:
        tok = self._consume(TokenType.KEYWORD, "switch")
        keyTok = self._expect(TokenType.STRING, "expected setting key string")
        fields = self._parseOptionalFieldBlock()
        return SwitchSettingNode(key=keyTok.value, fields=fields, line=tok.line, col=tok.col)

    def _parseInputSetting(self) -> InputSettingNode:
        tok = self._consume(TokenType.KEYWORD, "input")
        keyTok = self._expect(TokenType.STRING, "expected setting key string")
        fields = self._parseOptionalFieldBlock()
        return InputSettingNode(key=keyTok.value, fields=fields, line=tok.line, col=tok.col)

    def _parseSelectorSetting(self) -> SelectorSettingNode:
        tok = self._consume(TokenType.KEYWORD, "selector")
        keyTok = self._expect(TokenType.STRING, "expected setting key string")
        fields = self._parseOptionalFieldBlock()
        return SelectorSettingNode(key=keyTok.value, fields=fields, line=tok.line, col=tok.col)

    def _parseEditText(self) -> EditTextNode:
        tok = self._consume(TokenType.KEYWORD, "edit_text")
        keyTok = self._expect(TokenType.STRING, "expected setting key string")
        fields = self._parseOptionalFieldBlock()
        return EditTextNode(key=keyTok.value, fields=fields, line=tok.line, col=tok.col)

    def _parseHeader(self) -> HeaderNode:
        tok = self._consume(TokenType.KEYWORD, "header")
        text = self._expect(TokenType.STRING, "expected header text string").value
        self._consumeNewline()
        return HeaderNode(text=text, line=tok.line, col=tok.col)

    def _parseDivider(self) -> DividerNode:
        tok = self._consume(TokenType.KEYWORD, "divider")
        text = ""
        if self._check(TokenType.STRING):
            text = self._advance().value
        self._consumeNewline()
        return DividerNode(text=text, line=tok.line, col=tok.col)

    def _parseTextItem(self) -> TextItemNode:
        tok = self._consume(TokenType.KEYWORD, "text")
        textTok = self._expect(TokenType.STRING, "expected text string")
        fields = self._parseOptionalFieldBlock()
        return TextItemNode(text=textTok.value, fields=fields, line=tok.line, col=tok.col)

    # helper: parse indented key: value block
    def _parseOptionalFieldBlock(self) -> dict:
        self._consumeNewline()
        if not self._check(TokenType.INDENT):
            return {}
        self._consume(TokenType.INDENT)
        self._skipNewlines()
        fields = self._parseFieldBlock()
        self._consume(TokenType.DEDENT)
        return fields

    def _parseFieldBlock(self) -> dict:
        fields = {}
        while not self._check(TokenType.DEDENT) and not self._atEof():
            keyTok = self._peek()
            if keyTok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                self._error("expected field name", keyTok)
            self._advance()
            self._consume(TokenType.COLON)
            val = self._parseExpr()
            fields[keyTok.value] = val
            self._skipNewlines()
        return fields

    # ------------------------------------------------------------------
    # functions
    # ------------------------------------------------------------------

    def _parseFun(self) -> FunNode:
        tok = self._consume(TokenType.KEYWORD, "fun")
        name = self._expect(TokenType.IDENTIFIER, "expected function name").value
        params, body, inline = self._parseFunParamsAndBodyFull()
        return FunNode(name=name, params=params, body=body, inlineExpr=inline,
                       line=tok.line, col=tok.col)

    def _parseFunParamsAndBody(self):
        params, body, _ = self._parseFunParamsAndBodyFull()
        return params, body

    def _parseFunParamsAndBodyFull(self):
        params = self._parseParamList()
        # inline form: fun f(x) = expr
        if self._check(TokenType.ASSIGN):
            self._advance()
            expr = self._parseExpr()
            self._consumeNewline()
            return params, [], expr
        self._consumeNewline()
        body = self._parseBlock()
        return params, body, None

    def _parseParamList(self) -> list:
        self._consume(TokenType.LPAREN)
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._parseParam())
            while self._check(TokenType.COMMA):
                self._advance()
                params.append(self._parseParam())
        self._consume(TokenType.RPAREN)
        return params

    def _parseParam(self) -> ParamNode:
        tok = self._expect(TokenType.IDENTIFIER, "expected parameter name")
        default = None
        if self._check(TokenType.ASSIGN):
            self._advance()
            default = self._parseExpr()
        return ParamNode(name=tok.value, default=default, line=tok.line, col=tok.col)

    def _parseBlock(self) -> list:
        self._consume(TokenType.INDENT)
        self._skipNewlines()
        stmts = []
        while not self._check(TokenType.DEDENT) and not self._atEof():
            stmts.extend(self._parseStatement())
            self._skipNewlines()
        self._consume(TokenType.DEDENT)
        return stmts

    # ------------------------------------------------------------------
    # statements
    # ------------------------------------------------------------------

    def _parseStatement(self) -> list:
        # semicolon-separated multiple statements on one line
        stmts = [self._parseSingleStatement()]
        while self._check(TokenType.SEMICOLON):
            self._advance()
            if self._check(TokenType.NEWLINE) or self._check(TokenType.DEDENT) or self._atEof():
                break
            stmts.append(self._parseSingleStatement())
        self._consumeNewline()
        return stmts

    def _parseSingleStatement(self) -> Any:
        tok = self._peek()

        if self._isKw(tok, "val"):
            return self._parseVal()
        if self._isKw(tok, "var"):
            return self._parseVar()
        if self._isKw(tok, "return"):
            return self._parseReturn()
        if self._isKw(tok, "break"):
            self._advance()
            return BreakNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "continue"):
            self._advance()
            return ContinueNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "raise"):
            return self._parseRaise()
        if self._isKw(tok, "cancel"):
            self._advance()
            return CancelNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "modify"):
            return self._parseModify()
        if self._isKw(tok, "default"):
            self._advance()
            return DefaultNode(line=tok.line, col=tok.col)
        if self._isKw(tok, "if"):
            return self._parseIf()
        if self._isKw(tok, "switch"):
            return self._parseSwitchStmt()
        if self._isKw(tok, "for"):
            return self._parseFor()
        if self._isKw(tok, "while"):
            return self._parseWhile()
        if self._isKw(tok, "sus"):
            return self._parseSus()
        if self._isKw(tok, "hook"):
            return self._parseHookDecl()
        if self._isKw(tok, "hook_send_message"):
            t = self._advance()
            return HookSendMessageDeclNode(line=t.line, col=t.col)
        if self._isKw(tok, "fun"):
            return self._parseFun()
        if self._isKw(tok, "log"):
            return self._parseExprStmt()

        return self._parseAssignOrExpr()

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

    def _parseReturn(self) -> ReturnNode:
        tok = self._consume(TokenType.KEYWORD, "return")
        value = None
        if not self._check(TokenType.NEWLINE) and not self._check(TokenType.DEDENT) and not self._atEof():
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

    def _parseAssignOrExpr(self) -> Any:
        expr = self._parseExpr()
        # assignment: target = value (but not ==)
        if self._check(TokenType.ASSIGN):
            self._advance()
            value = self._parseExpr()
            return AssignNode(target=expr, value=value, line=expr.line, col=expr.col)
        return ExprStmtNode(expr=expr, line=expr.line, col=expr.col)

    def _parseExprStmt(self) -> ExprStmtNode:
        expr = self._parseExpr()
        return ExprStmtNode(expr=expr, line=expr.line, col=expr.col)

    # ------------------------------------------------------------------
    # control flow
    # ------------------------------------------------------------------

    def _parseIf(self) -> IfNode:
        tok = self._consume(TokenType.KEYWORD, "if")
        cond = self._parseExpr()
        self._consumeNewline()
        thenBody = self._parseBlock()
        elseIfs = []
        elseBody = []
        while self._isKw(self._peek(), "else"):
            self._advance()
            if self._isKw(self._peek(), "if"):
                self._advance()
                eic = self._parseExpr()
                self._consumeNewline()
                eib = self._parseBlock()
                elseIfs.append((eic, eib))
            else:
                self._consumeNewline()
                elseBody = self._parseBlock()
                break
        return IfNode(condition=cond, thenBody=thenBody, elseIfs=elseIfs,
                      elseBody=elseBody, line=tok.line, col=tok.col)

    def _parseSwitchStmt(self) -> SwitchNode:
        tok = self._consume(TokenType.KEYWORD, "switch")
        subject = self._parseExpr()
        self._consumeNewline()
        self._consume(TokenType.INDENT)
        self._skipNewlines()
        cases, elseBody = self._parseSwitchCases()
        self._consume(TokenType.DEDENT)
        return SwitchNode(subject=subject, cases=cases, elseBody=elseBody,
                          line=tok.line, col=tok.col)

    def _parseSwitchCases(self):
        cases = []
        elseBody = []
        while not self._check(TokenType.DEDENT) and not self._atEof():
            tok = self._peek()
            if self._isKw(tok, "else"):
                self._advance()
                self._consume(TokenType.ARROW)
                if self._check(TokenType.NEWLINE):
                    self._consumeNewline()
                    elseBody = self._parseBlock()
                else:
                    stmt = self._parseSingleStatement()
                    elseBody = [stmt]
                self._skipNewlines()
                break
            # pattern list
            patterns = [self._parseExpr()]
            while self._check(TokenType.COMMA):
                self._advance()
                patterns.append(self._parseExpr())
            self._consume(TokenType.ARROW)
            if self._check(TokenType.NEWLINE):
                self._consumeNewline()
                body = self._parseBlock()
            else:
                stmt = self._parseSingleStatement()
                body = [stmt]
            cases.append(SwitchCaseNode(patterns=patterns, body=body,
                                        line=tok.line, col=tok.col))
            self._skipNewlines()
        return cases, elseBody

    def _parseFor(self) -> ForNode:
        tok = self._consume(TokenType.KEYWORD, "for")
        targets = [self._expect(TokenType.IDENTIFIER, "expected loop variable").value]
        if self._check(TokenType.COMMA):
            self._advance()
            targets.append(self._expect(TokenType.IDENTIFIER, "expected second loop variable").value)
        self._consume(TokenType.KEYWORD, "in")
        iterable = self._parseExpr()
        self._consumeNewline()
        body = self._parseBlock()
        return ForNode(targets=targets, iterable=iterable, body=body,
                       line=tok.line, col=tok.col)

    def _parseWhile(self) -> WhileNode:
        tok = self._consume(TokenType.KEYWORD, "while")
        cond = self._parseExpr()
        self._consumeNewline()
        body = self._parseBlock()
        return WhileNode(condition=cond, body=body, line=tok.line, col=tok.col)

    def _parseSus(self) -> SusNode:
        tok = self._consume(TokenType.KEYWORD, "sus")
        self._consumeNewline()
        body = self._parseBlock()
        handlers = []
        finallyBody = []
        while self._isKw(self._peek(), "try"):
            self._advance()
            excType = None
            asName = None
            if not self._check(TokenType.NEWLINE) and not self._atEof():
                excType = self._parseExpr()
                if self._isKw(self._peek(), "as"):
                    self._advance()
                    asName = self._expect(TokenType.IDENTIFIER, "expected name after 'as'").value
            self._consumeNewline()
            hBody = self._parseBlock()
            handlers.append(SusHandlerNode(excType=excType, asName=asName,
                                           body=hBody, line=tok.line, col=tok.col))
        if self._isKw(self._peek(), "finally"):
            self._advance()
            self._consumeNewline()
            finallyBody = self._parseBlock()
        return SusNode(body=body, handlers=handlers, finallyBody=finallyBody,
                       line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # expressions (Pratt-style precedence climbing)
    # ------------------------------------------------------------------

    def _parseExpr(self) -> Any:
        return self._parseOr()

    def _parseOr(self) -> Any:
        left = self._parseAnd()
        while self._isKw(self._peek(), "or"):
            op = self._advance().value
            right = self._parseAnd()
            left = BinaryOpNode(op=op, left=left, right=right,
                                line=left.line, col=left.col)
        return left

    def _parseAnd(self) -> Any:
        left = self._parseNot()
        while self._isKw(self._peek(), "and"):
            op = self._advance().value
            right = self._parseNot()
            left = BinaryOpNode(op=op, left=left, right=right,
                                line=left.line, col=left.col)
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
            TokenType.LT: "<", TokenType.GT: ">",
            TokenType.LTE: "<=", TokenType.GTE: ">=",
        }
        while self._peek().type in cmpOps:
            op = cmpOps[self._advance().type]
            right = self._parseIn()
            left = BinaryOpNode(op=op, left=left, right=right,
                                line=left.line, col=left.col)
        return left

    def _parseIn(self) -> Any:
        left = self._parseAddSub()
        tok = self._peek()
        if self._isKw(tok, "in"):
            self._advance()
            right = self._parseAddSub()
            return BinaryOpNode(op="in", left=left, right=right,
                                line=left.line, col=left.col)
        if self._isKw(tok, "not") and self._peekAt(1) and self._isKw(self._peekAt(1), "in"):
            self._advance(); self._advance()
            right = self._parseAddSub()
            return BinaryOpNode(op="not in", left=left, right=right,
                                line=left.line, col=left.col)
        return left

    def _parseAddSub(self) -> Any:
        left = self._parseMulDiv()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            right = self._parseMulDiv()
            left = BinaryOpNode(op=op, left=left, right=right,
                                line=left.line, col=left.col)
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
            left = BinaryOpNode(op=op, left=left, right=right,
                                line=left.line, col=left.col)
        return left

    def _parseUnary(self) -> Any:
        tok = self._peek()
        if tok.type == TokenType.MINUS:
            self._advance()
            operand = self._parseUnary()
            return UnaryOpNode(op="-", operand=operand, line=tok.line, col=tok.col)
        return self._parsePostfix()

    def _parsePostfix(self) -> Any:
        expr = self._parsePrimary()
        while True:
            tok = self._peek()
            if tok.type == TokenType.DOT:
                self._advance()
                attr = self._expect(TokenType.IDENTIFIER, "expected attribute name after '.'").value
                expr = MemberNode(obj=expr, attr=attr, line=tok.line, col=tok.col)
            elif tok.type == TokenType.LPAREN:
                args = self._parseArgList()
                expr = CallNode(callee=expr, args=args, line=tok.line, col=tok.col)
            elif tok.type == TokenType.LBRACKET:
                self._advance()
                idx = self._parseExpr()
                # slice check
                if self._check(TokenType.COLON):
                    self._advance()
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
        # keyword argument: name = value
        if tok.type == TokenType.IDENTIFIER and self._peekAt(1) and self._peekAt(1).type == TokenType.ASSIGN:
            name = self._advance().value
            self._advance()  # =
            val = self._parseExpr()
            return ArgNode(value=val, keyword=name, line=tok.line, col=tok.col)
        val = self._parseExpr()
        return ArgNode(value=val, keyword=None, line=tok.line, col=tok.col)

    def _parsePrimary(self) -> Any:
        tok = self._peek()

        # lambda: (params) -> expr or (params) -> \n block
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

        # if-expression: if cond then a else b
        if self._isKw(tok, "if"):
            return self._parseIfExpr()

        # switch-expression: switch x \n cases
        if self._isKw(tok, "switch"):
            return self._parseSwitchExpr()

        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return IdentNode(name=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.KEYWORD:
            # keywords that can appear as expression-like calls: log, setting, etc.
            self._advance()
            return IdentNode(name=tok.value, line=tok.line, col=tok.col)

        self._error(f"Unexpected token {tok.value!r} in expression", tok)

    def _parseStringLiteral(self) -> StringNode:
        tok = self._peek()
        parts = []
        # collect consecutive string / interp tokens that form one string
        while self._peek().type in (TokenType.STRING, TokenType.STRING_PART, TokenType.INTERP_EXPR):
            t = self._advance()
            if t.type == TokenType.INTERP_EXPR:
                # parse the expression inside interpolation
                innerLexer = __import__("src.lexer", fromlist=["Lexer"]).Lexer
                innerTokens = innerLexer(t.value, self.filename).tokenize()
                innerParser = Parser(innerTokens, self.filename)
                parts.append(innerParser._parseExpr())
            else:
                parts.append(t.value)
        return StringNode(parts=parts, line=tok.line, col=tok.col)

    def _parseList(self) -> ListNode:
        tok = self._consume(TokenType.LBRACKET)
        elements = []
        self._skipNewlines()
        if not self._check(TokenType.RBRACKET):
            elements.append(self._parseExpr())
            while self._check(TokenType.COMMA):
                self._advance()
                self._skipNewlines()
                if self._check(TokenType.RBRACKET):
                    break
                elements.append(self._parseExpr())
        self._skipNewlines()
        self._consume(TokenType.RBRACKET)
        return ListNode(elements=elements, line=tok.line, col=tok.col)

    def _parseDictOrSet(self) -> Any:
        tok = self._consume(TokenType.LBRACE)
        self._skipNewlines()
        if self._check(TokenType.RBRACE):
            self._advance()
            return DictNode(pairs=[], line=tok.line, col=tok.col)
        first = self._parseExpr()
        if self._check(TokenType.COLON):
            # dict
            self._advance()
            val = self._parseExpr()
            pairs = [(first, val)]
            while self._check(TokenType.COMMA):
                self._advance()
                self._skipNewlines()
                if self._check(TokenType.RBRACE):
                    break
                k = self._parseExpr()
                self._consume(TokenType.COLON)
                v = self._parseExpr()
                pairs.append((k, v))
            self._skipNewlines()
            self._consume(TokenType.RBRACE)
            return DictNode(pairs=pairs, line=tok.line, col=tok.col)
        else:
            # set
            elements = [first]
            while self._check(TokenType.COMMA):
                self._advance()
                self._skipNewlines()
                if self._check(TokenType.RBRACE):
                    break
                elements.append(self._parseExpr())
            self._skipNewlines()
            self._consume(TokenType.RBRACE)
            return SetNode(elements=elements, line=tok.line, col=tok.col)

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
        self._consumeNewline()
        self._consume(TokenType.INDENT)
        self._skipNewlines()
        cases, elseBody = self._parseSwitchCases()
        self._consume(TokenType.DEDENT)
        elseVal = elseBody[0] if elseBody else None
        return SwitchExprNode(subject=subject, cases=cases, elseVal=elseVal,
                              line=tok.line, col=tok.col)

    def _parseLambda(self) -> LambdaNode:
        tok = self._peek()
        params = self._parseParamList()
        self._consume(TokenType.ARROW)
        # multi-line lambda: arrow then newline + block
        if self._check(TokenType.NEWLINE):
            self._consumeNewline()
            body = self._parseBlock()
            return LambdaNode(params=params, body=body, line=tok.line, col=tok.col)
        body = self._parseExpr()
        return LambdaNode(params=params, body=body, line=tok.line, col=tok.col)

    def _looksLikeLambda(self) -> bool:
        """
        Peek ahead to determine if (params) -> is ahead.
        Heuristic: find matching ) then check for ->
        """
        i = self.pos + 1  # skip (
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
    # token navigation helpers
    # ------------------------------------------------------------------

    def _peek(self) -> Token:
        while self.pos < len(self.tokens) and self.tokens[self.pos].type == TokenType.NEWLINE:
            # don't skip here — callers that need to skip call _skipNewlines
            pass
        if self.pos >= len(self.tokens):
            last = self.tokens[-1] if self.tokens else Token(TokenType.EOF, "", 1, 1)
            return Token(TokenType.EOF, "", last.line, last.col)
        return self.tokens[self.pos]

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

    def _skipNewlines(self) -> None:
        while self._check(TokenType.NEWLINE):
            self._advance()

    def _skipIndentDedent(self) -> None:
        while self._peek().type in (TokenType.INDENT, TokenType.DEDENT):
            self._advance()

    def _consumeNewline(self) -> None:
        # newline is optional at EOF
        if self._check(TokenType.NEWLINE):
            self._advance()
        elif not self._atEof() and not self._check(TokenType.DEDENT):
            pass  # tolerate missing newline before DEDENT

    def _consume(self, ttype: TokenType, value: str | None = None) -> Token:
        tok = self._peek()
        if tok.type != ttype:
            expected = value or ttype.name
            self._error(f"Expected {expected!r} but got {tok.value!r}", tok)
        if value is not None and tok.value != value:
            self._error(f"Expected {value!r} but got {tok.value!r}", tok)
        return self._advance()

    def _expect(self, ttype: TokenType, msg: str) -> Token:
        tok = self._peek()
        if tok.type != ttype:
            self._error(msg + f" (got {tok.value!r})", tok)
        return self._advance()

    def _error(self, msg: str, tok: Token | None = None) -> None:
        t = tok or self._peek()
        srcLine = self.srcLines[t.line - 1] if 0 < t.line <= len(self.srcLines) else ""
        raise ReunionParseError(msg, self.filename, t.line, t.col, srcLine)
