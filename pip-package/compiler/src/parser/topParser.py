from typing import Any
from .stmtParser import StmtParser
from ..tokenTypes import TokenType
from ..ast import (
    ProgramNode, MetainfoNode, ImportNode, RawNode,
    PluginNode, HookDeclNode, HookSendMessageDeclNode,
    MethodHookNode, MethodReplaceNode, MenuItemNode,
    SettingsNode, SwitchSettingNode, InputSettingNode,
    SelectorSettingNode, EditTextNode, HeaderNode, DividerNode, TextItemNode,
    FunNode,
)


class TopParser(StmtParser):

    # ------------------------------------------------------------------
    # program entry point
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        children = []
        self._skipSemis()
        while not self._atEof():
            children.append(self._parseTopLevel())
            self._skipSemis()
        return ProgramNode(children=children, line=1, col=1)

    # ------------------------------------------------------------------
    # top-level dispatching
    # ------------------------------------------------------------------

    def _parseTopLevel(self) -> Any:
        tok = self._peek()

        if self._isKw(tok, "metainfo"):   return self._parseMetainfo()
        if self._isKw(tok, "import"):     return self._parseImport()
        if self._isKw(tok, "raw"):        return self._parseRaw()
        if self._isKw(tok, "plugin"):     return self._parsePlugin()
        if self._isKw(tok, "settings"):   return self._parseSettings()
        if self._isKw(tok, "fun"):        return self._parseFun()
        if self._isKw(tok, "val"):        return self._parseVal()
        if self._isKw(tok, "var"):        return self._parseVar()
        if self._isKw(tok, "if"):         return self._parseIf()
        if self._isKw(tok, "while"):      return self._parseWhile()
        if self._isKw(tok, "for"):        return self._parseFor()
        if self._isKw(tok, "sus"):        return self._parseSus()
        if self._isKw(tok, "switch"):     return self._parseSwitchStmt()

        # Unknown token at top level — give a clear error instead of looping forever
        self._error(
            f"Unexpected {tok.value!r} at top level — expected a declaration (plugin, fun, settings, metainfo, import, raw)",
            tok,
        )

    # ------------------------------------------------------------------
    # metainfo — already uses { } naturally
    # ------------------------------------------------------------------

    def _parseMetainfo(self) -> MetainfoNode:
        tok = self._consume(TokenType.KEYWORD, "metainfo")
        self._consume(TokenType.LBRACE)
        self._skipSemis()
        fields = {}
        while not self._check(TokenType.RBRACE) and not self._atEof():
            keyTok = self._peek()
            if keyTok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                self._error("expected field name in metainfo", keyTok)
            self._advance()
            self._consume(TokenType.COLON)
            val = self._parseExpr()
            fields[keyTok.value] = val
            self._skipSemis()
        self._consume(TokenType.RBRACE)
        return MetainfoNode(fields=fields, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # import
    # ------------------------------------------------------------------

    def _parseImport(self) -> ImportNode:
        tok = self._consume(TokenType.KEYWORD, "import")
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

            def _parseName():
                nameTok = self._peek()
                if nameTok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                    self._error("expected name", nameTok)
                name = self._advance().value
                if self._isKw(self._peek(), "as"):
                    self._advance()
                    aliasTok = self._peek()
                    if aliasTok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                        self._error("expected alias after 'as'", aliasTok)
                    alias = self._advance().value
                    return (name, alias)
                return name

            names.append(_parseName())
            while self._check(TokenType.COMMA):
                self._advance()
                if self._check(TokenType.RPAREN):
                    break
                names.append(_parseName())
            self._consume(TokenType.RPAREN)
        return ImportNode(module=module, names=names, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # raw block — contents captured verbatim up to matching }
    # ------------------------------------------------------------------

    def _parseRaw(self) -> RawNode:
        tok = self._consume(TokenType.KEYWORD, "raw")
        openBrace = self._consume(TokenType.LBRACE)

        if self.srcLines:
            src = "\n".join(self.srcLines)
            lines = self.srcLines
            startLine = openBrace.line - 1
            startCol = openBrace.col
            absPos = sum(len(lines[i]) + 1 for i in range(startLine)) + startCol
            depth = 1
            i = absPos
            while i < len(src) and depth > 0:
                if src[i] == "{":
                    depth += 1
                elif src[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            # strip common leading whitespace (dedent)
            import textwrap as _tw
            rawText = _tw.dedent(src[absPos:i]).strip()
        else:
            rawText = ""

        # advance parser tokens past all content until matching }
        depth = 1
        while not self._atEof():
            t = self._peek()
            if t.type == TokenType.LBRACE:
                depth += 1
            elif t.type == TokenType.RBRACE:
                depth -= 1
                if depth == 0:
                    self._advance()
                    break
            self._advance()

        return RawNode(code=rawText, line=tok.line, col=tok.col)


    def _parsePlugin(self) -> PluginNode:
        tok = self._consume(TokenType.KEYWORD, "plugin")
        name = self._expect(TokenType.IDENTIFIER, "expected plugin name").value
        self._consume(TokenType.LBRACE)
        self._skipSemis()
        body = []
        while not self._check(TokenType.RBRACE) and not self._atEof():
            body.append(self._parsePluginMember())
            self._skipSemis()
        self._consume(TokenType.RBRACE)
        return PluginNode(name=name, body=body, line=tok.line, col=tok.col)

    def _parsePluginMember(self) -> Any:
        tok = self._peek()
        if self._isKw(tok, "fun"):              return self._parseFun()
        if self._isKw(tok, "hook"):             return self._parseHookDecl()
        if self._isKw(tok, "hook_send_message"):
            t = self._advance()
            return HookSendMessageDeclNode(line=t.line, col=t.col)
        if self._isKw(tok, "method_hook"):      return self._parseMethodHook()
        if self._isKw(tok, "method_replace"):   return self._parseMethodReplace()
        if self._isKw(tok, "menu_item"):        return self._parseMenuItem()
        if self._isKw(tok, "val"):              return self._parseVal()
        if self._isKw(tok, "var"):              return self._parseVar()
        return self._parseExprStmt()

    def _parseMethodHook(self) -> MethodHookNode:
        tok = self._consume(TokenType.KEYWORD, "method_hook")
        name = self._expect(TokenType.IDENTIFIER, "expected method_hook class name").value
        body = self._parseBlock()
        return MethodHookNode(name=name, params=[], body=body, line=tok.line, col=tok.col)

    def _parseMethodReplace(self) -> MethodReplaceNode:
        tok = self._consume(TokenType.KEYWORD, "method_replace")
        name = self._expect(TokenType.IDENTIFIER, "expected method_replace class name").value
        body = self._parseBlock()
        return MethodReplaceNode(name=name, params=[], body=body, line=tok.line, col=tok.col)

    def _parseMenuItem(self) -> MenuItemNode:
        tok = self._consume(TokenType.KEYWORD, "menu_item")
        self._consume(TokenType.LBRACE)
        self._skipSemis()
        fields = self._parseFieldBlock()
        self._consume(TokenType.RBRACE)
        return MenuItemNode(fields=fields, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # settings block
    # ------------------------------------------------------------------

    def _parseSettings(self) -> SettingsNode:
        tok = self._consume(TokenType.KEYWORD, "settings")
        self._consume(TokenType.LBRACE)
        self._skipSemis()
        items = []
        while not self._check(TokenType.RBRACE) and not self._atEof():
            items.append(self._parseSettingItem())
            self._skipSemis()
        self._consume(TokenType.RBRACE)
        return SettingsNode(items=items, line=tok.line, col=tok.col)

    def _parseSettingItem(self) -> Any:
        tok = self._peek()
        if self._isKw(tok, "switch"):    return self._parseSwitchSetting()
        if self._isKw(tok, "input"):     return self._parseInputSetting()
        if self._isKw(tok, "selector"):  return self._parseSelectorSetting()
        if self._isKw(tok, "edit_text"): return self._parseEditText()
        if self._isKw(tok, "header"):    return self._parseHeader()
        if self._isKw(tok, "divider"):   return self._parseDivider()
        if self._isKw(tok, "text"):      return self._parseTextItem()
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
        textTok = self._expect(TokenType.STRING, "expected header text string")
        return HeaderNode(text=textTok.value, line=tok.line, col=tok.col)

    def _parseDivider(self) -> DividerNode:
        tok = self._consume(TokenType.KEYWORD, "divider")
        text = ""
        if self._check(TokenType.STRING):
            text = self._advance().value
        return DividerNode(text=text, line=tok.line, col=tok.col)

    def _parseTextItem(self) -> TextItemNode:
        tok = self._consume(TokenType.KEYWORD, "text")
        textTok = self._expect(TokenType.STRING, "expected text string")
        fields = self._parseOptionalFieldBlock()
        return TextItemNode(text=textTok.value, fields=fields, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # field block helpers
    # ------------------------------------------------------------------

    def _parseOptionalFieldBlock(self) -> dict:
        if not self._check(TokenType.LBRACE):
            return {}
        self._consume(TokenType.LBRACE)
        self._skipSemis()
        fields = self._parseFieldBlock()
        self._consume(TokenType.RBRACE)
        return fields

    def _parseFieldBlock(self) -> dict:
        fields = {}
        while not self._check(TokenType.RBRACE) and not self._atEof():
            keyTok = self._peek()
            if keyTok.type not in (TokenType.IDENTIFIER, TokenType.KEYWORD):
                self._error("expected field name", keyTok)
            self._advance()
            self._consume(TokenType.COLON)
            val = self._parseExpr()
            fields[keyTok.value] = val
            self._skipSemis()
        return fields
