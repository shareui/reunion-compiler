from typing import Any
from ..ast import (
    ProgramNode, MetainfoNode, ImportNode, RawNode,
    PluginNode, HookDeclNode, HookSendMessageDeclNode,
    FunNode, ParamNode, SettingsNode,
    SwitchSettingNode, InputSettingNode, SelectorSettingNode,
    EditTextNode, HeaderNode, DividerNode, TextItemNode,
    MenuItemNode, MethodHookNode, MethodReplaceNode,
    ValNode, VarNode, AssignNode, ReturnNode,
    BreakNode, ContinueNode, RaiseNode,
    CancelNode, ModifyNode, DefaultNode,
    IfNode, SwitchNode, SwitchCaseNode, ForNode, WhileNode,
    SusNode, SusHandlerNode, ExprStmtNode,
    IdentNode, NumberNode, StringNode, BoolNode, NullNode,
    ListNode, DictNode, SetNode,
    BinaryOpNode, UnaryOpNode, CallNode, ArgNode,
    IndexNode, SliceNode, MemberNode, LambdaNode,
    IfExprNode, SwitchExprNode,
)


# python keywords that need escaping if used as identifiers
_PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
}

# reunion builtin calls that map to self.* methods
_SELF_CALLS = {"log", "get_setting", "add_hook", "add_on_send_message_hook", "hook_method", "hook_all_methods"}


class CodeGenerator:
    def __init__(self):
        self._lines: list[str] = []
        self._indent = 0
        self._importedNames: set[str] = set()  # tracks what we've emitted

    # ------------------------------------------------------------------
    # public entry point
    # ------------------------------------------------------------------

    def generate(self, program: ProgramNode) -> str:
        self._lines = []
        self._indent = 0

        self._emit("# Скомпилировано с использованием Reunion Native — лёгкого языка для разработки плагинов для exteraGram/AyuGram.")
        self._emit("# Больше информации о Reunion: https://github.com/shareui/reunion-compiler")
        self._emit("")
        self._emit("# Compiled using Reunion Native, a lightweight language for developing plugins for exteraGram/AyuGram.")
        self._emit("# More information about Reunion: https://github.com/shareui/reunion-compiler")
        self._emit("")

        imports, metainfo, plugin, settings, raws, others = self._splitTopLevel(program)

        self._emitFileHeader(metainfo, imports, plugin)
        for raw in raws:
            self._emitRaw(raw)
        if plugin:
            self._emitPlugin(plugin, settings, metainfo)
        # top-level funs/vals outside plugin (rare but valid)
        for node in others:
            self._emitNode(node)

        return "\n".join(self._lines) + "\n"

    # ------------------------------------------------------------------
    # top-level splitting
    # ------------------------------------------------------------------

    def _splitTopLevel(self, program: ProgramNode):
        imports: list[ImportNode] = []
        metainfo: MetainfoNode | None = None
        plugin: PluginNode | None = None
        settings: SettingsNode | None = None
        raws: list[RawNode] = []
        others: list = []

        for node in program.children:
            if isinstance(node, MetainfoNode):
                metainfo = node
            elif isinstance(node, ImportNode):
                imports.append(node)
            elif isinstance(node, PluginNode):
                plugin = node
            elif isinstance(node, SettingsNode):
                settings = node
            elif isinstance(node, RawNode):
                raws.append(node)
            else:
                others.append(node)

        return imports, metainfo, plugin, settings, raws, others

    # ------------------------------------------------------------------
    # file header: metainfo attrs + imports
    # ------------------------------------------------------------------

    def _emitFileHeader(self, metainfo: MetainfoNode | None, imports: list[ImportNode], plugin: PluginNode | None = None) -> None:
        emittedLines: set[str] = set()

        def emitOnce(line: str) -> None:
            if line not in emittedLines:
                emittedLines.add(line)
                self._emit(line)

        # Collect what user already imports from base_plugin
        userBasePluginNames: set[str] = set()
        for imp in imports:
            if imp.module == "base_plugin" and imp.names:
                for n in imp.names:
                    userBasePluginNames.add(n if isinstance(n, str) else n[0])

        # always needed base imports — skip individual names already in user import
        _baseEssentials = ["BasePlugin", "HookResult", "HookStrategy"]
        missing = [n for n in _baseEssentials if n not in userBasePluginNames]
        if missing:
            emitOnce(f"from base_plugin import {', '.join(missing)}")
        emitOnce("from typing import Any")

        # auto-add MenuItemData/MenuItemType if menu_item is used
        if plugin and any(isinstance(m, MenuItemNode) for m in plugin.body):
            menuNames = [n for n in ["MenuItemData", "MenuItemType"] if n not in userBasePluginNames]
            if menuNames:
                emitOnce(f"from base_plugin import {', '.join(menuNames)}")

        # auto-add MethodHook/MethodReplacement if method_hook/method_replace is used
        if plugin:
            hasMethodHook = any(isinstance(m, MethodHookNode) for m in plugin.body)
            hasMethodReplace = any(isinstance(m, MethodReplaceNode) for m in plugin.body)
            extras = []
            if hasMethodHook and "MethodHook" not in userBasePluginNames:
                extras.append("MethodHook")
            if hasMethodReplace and "MethodReplacement" not in userBasePluginNames:
                extras.append("MethodReplacement")
            if extras:
                emitOnce(f"from base_plugin import {', '.join(extras)}")

        for imp in imports:
            if imp.names:
                parts = []
                for n in imp.names:
                    if isinstance(n, tuple):
                        parts.append(f"{n[0]} as {n[1]}")
                    else:
                        parts.append(n)
                emitOnce(f"from {imp.module} import {', '.join(parts)}")
            else:
                emitOnce(f"import {imp.module}")

        self._emit("")

        if metainfo:
            fields = metainfo.fields
            self._emitMetaConst("__id__", fields.get("id", ""))
            self._emitMetaConst("__name__", fields.get("name", ""))
            self._emitMetaConst("__version__", fields.get("version", "1.0.0"))
            self._emitMetaConst("__author__", fields.get("author", ""))
            self._emitMetaConst("__description__", fields.get("description", ""))
            if "icon" in fields:
                self._emitMetaConst("__icon__", fields["icon"])
            if "min_version" in fields:
                self._emitMetaConst("__min_version__", fields["min_version"])
            if "requirements" in fields:
                self._emitMetaConst("__requirements__", fields["requirements"])
            self._emit("")

    def _emitMetaConst(self, name: str, value: Any) -> None:
        if isinstance(value, str):
            self._emit(f'{name} = {self._exprStr(StringNode(parts=[value], line=0, col=0))}')
        else:
            self._emit(f"{name} = {self._exprNode(value)}")

    # ------------------------------------------------------------------
    # raw block
    # ------------------------------------------------------------------

    def _emitRaw(self, node: RawNode) -> None:
        for line in node.code.splitlines():
            self._emit(line)
        self._emit("")

    # ------------------------------------------------------------------
    # plugin class
    # ------------------------------------------------------------------

    def _emitPlugin(self, plugin: PluginNode, settings: SettingsNode | None, metainfo: MetainfoNode | None) -> None:
        self._emit(f"class {plugin.name}(BasePlugin):")
        self._push()

        # separate members by kind
        hookDecls: list[HookDeclNode] = []
        hasSendMessageDecl = False
        funs: list[FunNode] = []
        methodHooks: list[MethodHookNode] = []
        methodReplaces: list[MethodReplaceNode] = []
        menuItems: list[MenuItemNode] = []
        fieldDecls: list = []  # val/var at class level (will be in __init__)

        for member in plugin.body:
            if isinstance(member, HookDeclNode):
                hookDecls.append(member)
            elif isinstance(member, HookSendMessageDeclNode):
                hasSendMessageDecl = True
            elif isinstance(member, FunNode):
                funs.append(member)
            elif isinstance(member, MethodHookNode):
                methodHooks.append(member)
            elif isinstance(member, MethodReplaceNode):
                methodReplaces.append(member)
            elif isinstance(member, MenuItemNode):
                menuItems.append(member)
            elif isinstance(member, (ValNode, VarNode)):
                fieldDecls.append(member)

        # also collect hook decls nested inside on_load body
        onLoad = next((f for f in funs if f.name == "on_load"), None)
        if onLoad:
            for stmt in onLoad.body:
                if isinstance(stmt, HookDeclNode):
                    hookDecls.append(stmt)
                elif isinstance(stmt, HookSendMessageDeclNode):
                    hasSendMessageDecl = True

        funNames = {f.name for f in funs}

        for fun in funs:
            if fun.name == "on_load":
                self._emitOnLoad(fun, hookDecls, hasSendMessageDecl, menuItems)
            elif fun.name == "on_unload":
                self._emitMethod("on_plugin_unload", fun.params, fun.body)
            elif fun.name == "pre_request":
                self._emitHookMethod("pre_request_hook", fun.params, fun.body, "DEFAULT")
            elif fun.name == "post_request":
                self._emitHookMethod("post_request_hook", fun.params, fun.body, "DEFAULT")
            elif fun.name == "on_send_message":
                self._emitHookMethod("on_send_message_hook", fun.params, fun.body, "DEFAULT")
            else:
                self._emitMethod(fun.name, fun.params, fun.body, fun.inlineExpr)

        if settings:
            self._emitCreateSettings(settings)

        self._pop()
        self._emit("")

        for mh in methodHooks:
            self._emitMethodHookClass(mh)
        for mr in methodReplaces:
            self._emitMethodReplaceClass(mr)

    # ------------------------------------------------------------------
    # on_plugin_load
    # ------------------------------------------------------------------

    def _emitOnLoad(self, fun: FunNode, hookDecls: list, hasSendMessageDecl: bool, menuItems: list) -> None:
        self._emit("def on_plugin_load(self):")
        self._push()

        # emit hook registrations
        for decl in hookDecls:
            self._emit(f'self.add_hook("{decl.hookName}")')

        if hasSendMessageDecl:
            self._emit("self.add_on_send_message_hook()")

        for mi in menuItems:
            self._emitMenuItemCall(mi)

        # emit user body, skipping hook/send_message decls (already handled)
        for stmt in fun.body:
            if isinstance(stmt, (HookDeclNode, HookSendMessageDeclNode)):
                continue
            self._emitNode(stmt)

        if not fun.body and not hookDecls and not hasSendMessageDecl:
            self._emit("pass")

        self._pop()
        self._emit("")

    # ------------------------------------------------------------------
    # hook handler methods (pre_request_hook / post_request_hook / on_send_message_hook)
    # ------------------------------------------------------------------

    def _emitHookMethod(self, pyName: str, params: list, body: list, fallback: str) -> None:
        paramStr = self._buildParams(params, selfPrefix=True)
        self._emit(f"def {pyName}(self{paramStr}) -> HookResult:")
        self._push()
        if body:
            for stmt in body:
                self._emitNode(stmt)
            # check if last stmt is already a terminal
            if not self._bodyEndsWithTerminal(body):
                self._emit(f"return HookResult(strategy=HookStrategy.{fallback})")
        else:
            self._emit(f"return HookResult(strategy=HookStrategy.{fallback})")
        self._pop()
        self._emit("")

    def _bodyEndsWithTerminal(self, body: list) -> bool:
        if not body:
            return False
        last = body[-1]
        if isinstance(last, (CancelNode, ModifyNode, DefaultNode, ReturnNode)):
            return True
        # switch with else — all paths covered
        if isinstance(last, SwitchNode) and last.elseBody:
            all_cases = all(self._bodyEndsWithTerminal(c.body) for c in last.cases)
            else_ok = self._bodyEndsWithTerminal(last.elseBody)
            return all_cases and else_ok
        # if with else and no else-ifs, or else-ifs all covered
        if isinstance(last, IfNode) and last.elseBody:
            then_ok = self._bodyEndsWithTerminal(last.thenBody)
            else_ok = self._bodyEndsWithTerminal(last.elseBody)
            elseifs_ok = all(self._bodyEndsWithTerminal(b) for _, b in last.elseIfs)
            return then_ok and else_ok and elseifs_ok
        return False

    # ------------------------------------------------------------------
    # generic method
    # ------------------------------------------------------------------

    def _emitMethod(self, name: str, params: list, body: list, inlineExpr: Any = None) -> None:
        paramStr = self._buildParams(params, selfPrefix=True)
        self._emit(f"def {name}(self{paramStr}):")
        self._push()
        if inlineExpr is not None:
            self._emit(f"return {self._exprNode(inlineExpr)}")
        elif body:
            for stmt in body:
                self._emitNode(stmt)
        else:
            self._emit("pass")
        self._pop()
        self._emit("")

    def _buildParams(self, params: list, selfPrefix: bool = False) -> str:
        if not params:
            return ""
        parts = []
        for p in params:
            if isinstance(p, ParamNode):
                if p.default is not None:
                    parts.append(f"{p.name}={self._exprNode(p.default)}")
                else:
                    parts.append(p.name)
            else:
                parts.append(str(p))
        sep = ", " if selfPrefix else ""
        return sep + ", ".join(parts)

    # ------------------------------------------------------------------
    # settings -> create_settings
    # ------------------------------------------------------------------

    def _emitCreateSettings(self, settings: SettingsNode) -> None:
        self._emit("def create_settings(self) -> list:")
        self._push()
        self._emit("return [")
        self._push()
        for item in settings.items:
            self._emitSettingItem(item)
        self._pop()
        self._emit("]")
        self._pop()
        self._emit("")

    def _emitSettingItem(self, item: Any) -> None:
        if isinstance(item, HeaderNode):
            self._emit(f'Header(text={self._strLit(item.text)}),')
        elif isinstance(item, DividerNode):
            if item.text:
                self._emit(f'Divider(text={self._strLit(item.text)}),')
            else:
                self._emit("Divider(),")
        elif isinstance(item, SwitchSettingNode):
            self._emit(self._buildSettingCall("Switch", item.key, item.fields) + ",")
        elif isinstance(item, InputSettingNode):
            self._emit(self._buildSettingCall("Input", item.key, item.fields) + ",")
        elif isinstance(item, SelectorSettingNode):
            self._emit(self._buildSettingCall("Selector", item.key, item.fields) + ",")
        elif isinstance(item, EditTextNode):
            self._emit(self._buildSettingCall("EditText", item.key, item.fields) + ",")
        elif isinstance(item, TextItemNode):
            self._emit(self._buildTextItem(item) + ",")

    def _buildSettingCall(self, cls: str, key: str, fields: dict) -> str:
        args = [f"key={self._strLit(key)}"]
        for fname, fval in fields.items():
            args.append(f"{fname}={self._exprNode(fval)}")
        return f"{cls}({', '.join(args)})"

    def _buildTextItem(self, item: TextItemNode) -> str:
        args = [f"text={self._strLit(item.text)}"]
        for fname, fval in item.fields.items():
            args.append(f"{fname}={self._exprNode(fval)}")
        return f"Text({', '.join(args)})"

    # ------------------------------------------------------------------
    # menu_item
    # ------------------------------------------------------------------

    def _emitMenuItemCall(self, node: MenuItemNode) -> None:
        fields = node.fields
        args = []
        for k, v in fields.items():
            pyKey = "menu_type" if k == "type" else k
            # qualify bare identifiers in type field as MenuItemType.X
            if k == "type" and isinstance(v, IdentNode):
                valStr = f"MenuItemType.{v.name}"
            else:
                valStr = self._exprNode(v)
            args.append(f"{pyKey}={valStr}")
        self._emit(f"self.add_menu_item(MenuItemData({', '.join(args)}))")

    # ------------------------------------------------------------------
    # method_hook / method_replace classes
    # ------------------------------------------------------------------

    def _emitMethodHookClass(self, node: MethodHookNode) -> None:
        self._emit(f"class {node.name}(MethodHook):")
        self._push()
        # body contains FunNode(s) named before/after; emit each as proper method
        hasMethods = False
        for stmt in node.body:
            if isinstance(stmt, FunNode):
                hasMethods = True
                if stmt.name == "before":
                    self._emitMethod("before_hooked_method", stmt.params, stmt.body)
                elif stmt.name == "after":
                    self._emitMethod("after_hooked_method", stmt.params, stmt.body)
                else:
                    self._emitMethod(stmt.name, stmt.params, stmt.body)
        if not hasMethods:
            self._emit("pass")
        self._pop()
        self._emit("")

    def _emitMethodReplaceClass(self, node: MethodReplaceNode) -> None:
        self._emit(f"class {node.name}(MethodReplacement):")
        self._push()
        hasMethods = False
        for stmt in node.body:
            if isinstance(stmt, FunNode):
                hasMethods = True
                if stmt.name == "replace":
                    self._emitMethod("replace_hooked_method", stmt.params, stmt.body)
                else:
                    self._emitMethod(stmt.name, stmt.params, stmt.body)
        if not hasMethods:
            self._emit("pass")
        self._pop()
        self._emit("")

    # ------------------------------------------------------------------
    # statement emitters
    # ------------------------------------------------------------------

    def _emitNode(self, node: Any) -> None:
        if node is None:
            return

        if isinstance(node, ValNode):
            self._emit(f"{node.name} = {self._exprNode(node.value)}")
        elif isinstance(node, VarNode):
            self._emit(f"{node.name} = {self._exprNode(node.value)}")
        elif isinstance(node, AssignNode):
            self._emit(f"{self._exprNode(node.target)} = {self._exprNode(node.value)}")
        elif isinstance(node, ReturnNode):
            if node.value is not None:
                self._emit(f"return {self._exprNode(node.value)}")
            else:
                self._emit("return")
        elif isinstance(node, BreakNode):
            self._emit("break")
        elif isinstance(node, ContinueNode):
            self._emit("continue")
        elif isinstance(node, RaiseNode):
            self._emit(f"raise {self._exprNode(node.value)}")
        elif isinstance(node, CancelNode):
            self._emit("return HookResult(strategy=HookStrategy.CANCEL)")
        elif isinstance(node, ModifyNode):
            self._emit(f"return HookResult(strategy=HookStrategy.MODIFY, {node.target}={node.target})")
        elif isinstance(node, DefaultNode):
            self._emit("return HookResult(strategy=HookStrategy.DEFAULT)")
        elif isinstance(node, IfNode):
            self._emitIf(node)
        elif isinstance(node, SwitchNode):
            self._emitSwitch(node)
        elif isinstance(node, ForNode):
            self._emitFor(node)
        elif isinstance(node, WhileNode):
            self._emitWhile(node)
        elif isinstance(node, SusNode):
            self._emitSus(node)
        elif isinstance(node, ExprStmtNode):
            self._emit(self._exprNode(node.expr))
        elif isinstance(node, FunNode):
            self._emitNestedFun(node)
        elif isinstance(node, HookDeclNode):
            pass  # handled in on_load
        elif isinstance(node, HookSendMessageDeclNode):
            pass
        else:
            # fallback: try to emit as expression
            self._emit(f"# unhandled node: {type(node).__name__}")

    def _emitIf(self, node: IfNode) -> None:
        self._emit(f"if {self._exprNode(node.condition)}:")
        self._push()
        self._emitBody(node.thenBody)
        self._pop()
        for cond, body in node.elseIfs:
            self._emit(f"elif {self._exprNode(cond)}:")
            self._push()
            self._emitBody(body)
            self._pop()
        if node.elseBody:
            self._emit("else:")
            self._push()
            self._emitBody(node.elseBody)
            self._pop()

    def _emitSwitch(self, node: SwitchNode) -> None:
        # translate switch to if/elif chain (match not available in all Python versions)
        subject = self._exprNode(node.subject)
        first = True
        for case in node.cases:
            patterns = [self._exprNode(p) for p in case.patterns]
            if len(patterns) == 1:
                cond = f"{subject} == {patterns[0]}"
            else:
                joined = ", ".join(patterns)
                cond = f"{subject} in ({joined})"
            kw = "if" if first else "elif"
            self._emit(f"{kw} {cond}:")
            self._push()
            self._emitBody(case.body)
            self._pop()
            first = False
        if node.elseBody:
            kw = "else" if not first else "if True"
            self._emit(f"else:")
            self._push()
            self._emitBody(node.elseBody)
            self._pop()

    def _emitFor(self, node: ForNode) -> None:
        targets = ", ".join(node.targets)
        self._emit(f"for {targets} in {self._exprNode(node.iterable)}:")
        self._push()
        self._emitBody(node.body)
        self._pop()

    def _emitWhile(self, node: WhileNode) -> None:
        self._emit(f"while {self._exprNode(node.condition)}:")
        self._push()
        self._emitBody(node.body)
        self._pop()

    def _emitSus(self, node: SusNode) -> None:
        self._emit("try:")
        self._push()
        self._emitBody(node.body)
        self._pop()
        for handler in node.handlers:
            if handler.excType is not None and handler.asName:
                self._emit(f"except {self._exprNode(handler.excType)} as {handler.asName}:")
            elif handler.excType is not None:
                # bare `try e` means catch any exception as variable e
                if isinstance(handler.excType, IdentNode):
                    self._emit(f"except Exception as {handler.excType.name}:")
                else:
                    self._emit(f"except {self._exprNode(handler.excType)}:")
            else:
                self._emit("except Exception:")
            self._push()
            self._emitBody(handler.body)
            self._pop()
        if node.finallyBody:
            self._emit("finally:")
            self._push()
            self._emitBody(node.finallyBody)
            self._pop()

    def _emitNestedFun(self, node: FunNode) -> None:
        paramStr = self._buildParams(node.params, selfPrefix=False)
        self._emit(f"def {node.name}({paramStr}):")
        self._push()
        if node.inlineExpr is not None:
            self._emit(f"return {self._exprNode(node.inlineExpr)}")
        elif node.body:
            for stmt in node.body:
                self._emitNode(stmt)
        else:
            self._emit("pass")
        self._pop()

    def _emitBody(self, stmts: list) -> None:
        if not stmts:
            self._emit("pass")
            return
        for stmt in stmts:
            self._emitNode(stmt)

    # ------------------------------------------------------------------
    # expression stringification
    # ------------------------------------------------------------------

    def _exprNode(self, node: Any) -> str:
        if node is None:
            return "None"
        if isinstance(node, IdentNode):
            return node.name
        if isinstance(node, NumberNode):
            return repr(node.value)
        if isinstance(node, StringNode):
            return self._exprStr(node)
        if isinstance(node, BoolNode):
            return "True" if node.value else "False"
        if isinstance(node, NullNode):
            return "None"
        if isinstance(node, ListNode):
            items = ", ".join(self._exprNode(e) for e in node.elements)
            return f"[{items}]"
        if isinstance(node, DictNode):
            pairs = ", ".join(f"{self._exprNode(k)}: {self._exprNode(v)}" for k, v in node.pairs)
            return "{" + pairs + "}"
        if isinstance(node, SetNode):
            items = ", ".join(self._exprNode(e) for e in node.elements)
            return "{" + items + "}"
        if isinstance(node, BinaryOpNode):
            return f"({self._exprNode(node.left)} {node.op} {self._exprNode(node.right)})"
        if isinstance(node, UnaryOpNode):
            return f"({node.op} {self._exprNode(node.operand)})"
        if isinstance(node, CallNode):
            return self._exprCall(node)
        if isinstance(node, IndexNode):
            return f"{self._exprNode(node.obj)}[{self._exprNode(node.index)}]"
        if isinstance(node, SliceNode):
            start = self._exprNode(node.start) if node.start else ""
            end = self._exprNode(node.end) if node.end else ""
            return f"{self._exprNode(node.obj)}[{start}:{end}]"
        if isinstance(node, MemberNode):
            return f"{self._exprNode(node.obj)}.{node.attr}"
        if isinstance(node, LambdaNode):
            return self._exprLambda(node)
        if isinstance(node, IfExprNode):
            return f"({self._exprNode(node.thenVal)} if {self._exprNode(node.condition)} else {self._exprNode(node.elseVal)})"
        if isinstance(node, SwitchExprNode):
            return self._exprSwitchExpr(node)
        # fallback for raw string values (from metainfo fields)
        if isinstance(node, str):
            return repr(node)
        return f"# unknown expr: {type(node).__name__}"

    def _exprStr(self, node: StringNode) -> str:
        # if all parts are plain strings, emit as regular string literal
        allPlain = all(isinstance(p, str) for p in node.parts)
        if allPlain:
            raw = "".join(node.parts)
            if "\n" in raw and len(raw.split("\n")) > 1 and any(line.strip() for line in raw.split("\n")):
                # real multiline content: use triple-quoted string
                escaped = raw.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
                return f'"""{escaped}"""'
            return repr(raw)
        # mixed: emit as f-string
        inner = ""
        for part in node.parts:
            if isinstance(part, str):
                inner += part.replace("{", "{{").replace("}", "}}")
            else:
                inner += "{" + self._exprNode(part) + "}"
        if "\n" in inner and len(inner.split("\n")) > 1 and any(line.strip() for line in inner.split("\n")):
            inner = inner.replace('"""', '\\"\\"\\"')
            return f'f"""{inner}"""'
        inner = inner.replace('"', '\\"')
        return f'f"{inner}"'

    def _exprCall(self, node: CallNode) -> str:
        # map Reunion builtins to self.* where needed
        callee = node.callee
        calleeStr = self._exprNode(callee)

        # setting("key") -> self.get_setting("key", default)
        if isinstance(callee, IdentNode) and callee.name == "setting":
            return self._emitSettingCall(node)

        # builtins that map to self.method(...)
        if isinstance(callee, IdentNode) and callee.name in _SELF_CALLS:
            argsStr = self._buildArgs(node.args)
            return f"self.{callee.name}({argsStr})"

        argsStr = self._buildArgs(node.args)
        return f"{calleeStr}({argsStr})"

    def _emitSettingCall(self, node: CallNode) -> str:
        args = node.args
        if not args:
            return "self.get_setting()"
        key = self._exprNode(args[0].value)
        if len(args) >= 2:
            default = self._exprNode(args[1].value)
            return f"self.get_setting({key}, {default})"
        return f"self.get_setting({key})"

    def _buildArgs(self, args: list) -> str:
        parts = []
        for arg in args:
            if isinstance(arg, ArgNode):
                if arg.keyword:
                    parts.append(f"{arg.keyword}={self._exprNode(arg.value)}")
                else:
                    parts.append(self._exprNode(arg.value))
            else:
                parts.append(self._exprNode(arg))
        return ", ".join(parts)

    def _exprLambda(self, node: LambdaNode) -> str:
        params = ", ".join(
            p.name if isinstance(p, ParamNode) else str(p)
            for p in node.params
        )
        if isinstance(node.body, list):
            # multi-line lambda: wrap in nested def (rare but valid)
            # for code gen purposes emit as lambda with last expr if possible
            if len(node.body) == 1 and isinstance(node.body[0], ExprStmtNode):
                return f"lambda {params}: {self._exprNode(node.body[0].expr)}"
            if len(node.body) == 1 and isinstance(node.body[0], ReturnNode):
                return f"lambda {params}: {self._exprNode(node.body[0].value)}"
            # fallback: can't express multi-stmt lambda inline, emit placeholder
            return f"lambda {params}: None  # multi-statement lambda requires def"
        return f"lambda {params}: {self._exprNode(node.body)}"

    def _exprSwitchExpr(self, node: SwitchExprNode) -> str:
        # express as nested ternary: (a if cond else (b if cond2 else c))
        subject = self._exprNode(node.subject)
        result = self._exprNode(node.elseVal) if node.elseVal else "None"
        for case in reversed(node.cases):
            patterns = [self._exprNode(p) for p in case.patterns]
            if len(patterns) == 1:
                cond = f"{subject} == {patterns[0]}"
            else:
                joined = ", ".join(patterns)
                cond = f"{subject} in ({joined})"
            val = self._exprNode(case.body) if not isinstance(case.body, list) else (
                self._exprNode(case.body[0]) if len(case.body) == 1 else "None"
            )
            result = f"({val} if {cond} else {result})"
        return result

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _strLit(self, s: str) -> str:
        return repr(s)

    def _emit(self, line: str) -> None:
        if line == "":
            self._lines.append("")
        else:
            self._lines.append("    " * self._indent + line)

    def _push(self) -> None:
        self._indent += 1

    def _pop(self) -> None:
        self._indent = max(0, self._indent - 1)
