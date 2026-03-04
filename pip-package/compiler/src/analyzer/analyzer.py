from typing import Any
from ..ast import (
    ProgramNode, MetainfoNode, ImportNode, RawNode,
    PluginNode, HookDeclNode, HookSendMessageDeclNode,
    PreRequestNode, PostRequestNode, OnSendMessageNode,
    SettingsNode, SwitchSettingNode, InputSettingNode,
    SelectorSettingNode, EditTextNode, HeaderNode, DividerNode, TextItemNode,
    FunNode, ValNode, VarNode, AssignNode, ReturnNode,
    BreakNode, ContinueNode, RaiseNode, CancelNode, ModifyNode, DefaultNode,
    IfNode, SwitchNode, SwitchCaseNode, ForNode, WhileNode,
    SusNode, SusHandlerNode, ExprStmtNode,
    IdentNode, CallNode, MemberNode, StringNode,
)
from .semanticError import SemanticError, SemanticWarning, ReunionSemanticError


# known metainfo keys from SYNTAX.md
_METAINFO_KEYS = {
    "id", "name", "version", "author", "description",
    "icon", "min_version", "requirements",
}

# hook handler method names
_REQUEST_HANDLERS = {"pre_request", "post_request", "on_send_message"}


class Analyzer:
    def __init__(self, filename: str = "<stdin>", source: str = ""):
        self.filename = filename
        self.srcLines = source.splitlines() if source else []

        self.errors: list[SemanticError] = []
        self.warnings: list[SemanticWarning] = []

        # collected during analysis
        self._declaredSettings: dict[str, Any] = {}   # key -> node
        self._registeredHooks: dict[str, Any] = {}    # hook name -> HookDeclNode
        self._hookSendMessageDeclared = False

        # val names in current scope stack (list of sets)
        self._valScopes: list[set[str]] = []

        # which handler methods are present
        self._handlerMethods: set[str] = set()

        # settings keys actually accessed via setting("key")
        self._usedSettingKeys: set[str] = set()

    # ------------------------------------------------------------------
    # public entry point
    # ------------------------------------------------------------------

    def analyze(self, program: ProgramNode) -> tuple[list[SemanticError], list[SemanticWarning]]:
        self._visitProgram(program)
        self._checkUnusedSettings()
        if self.errors:
            raise ReunionSemanticError(self.errors, self.warnings)
        return self.errors, self.warnings

    # ------------------------------------------------------------------
    # program
    # ------------------------------------------------------------------

    def _visitProgram(self, node: ProgramNode) -> None:
        # first pass: collect settings declarations and plugin structure
        for child in node.children:
            if isinstance(child, SettingsNode):
                self._collectSettings(child)

        # second pass: full analysis
        for child in node.children:
            self._visitNode(child)

    # ------------------------------------------------------------------
    # node dispatcher
    # ------------------------------------------------------------------

    def _visitNode(self, node: Any) -> None:
        if node is None:
            return
        t = type(node)
        visitor = _VISITORS.get(t)
        if visitor:
            visitor(self, node)
        # nodes with no semantic rules are silently accepted

    def _visitBody(self, stmts: list) -> None:
        for stmt in stmts:
            self._visitNode(stmt)

    # ------------------------------------------------------------------
    # settings collection
    # ------------------------------------------------------------------

    def _collectSettings(self, node: SettingsNode) -> None:
        for item in node.items:
            if isinstance(item, (SwitchSettingNode, InputSettingNode,
                                  SelectorSettingNode, EditTextNode)):
                self._declaredSettings[item.key] = item

    # ------------------------------------------------------------------
    # visitors
    # ------------------------------------------------------------------

    def _visitMetainfo(self, node: MetainfoNode) -> None:
        for key in node.fields:
            if key not in _METAINFO_KEYS:
                self._warn(
                    f"Unknown metainfo key {key!r}. "
                    f"Known keys: {', '.join(sorted(_METAINFO_KEYS))}",
                    node,
                )

    def _visitImport(self, node: ImportNode) -> None:
        pass  # no semantic rules for imports

    def _visitRaw(self, node: RawNode) -> None:
        pass

    def _visitPlugin(self, node: PluginNode) -> None:
        # collect hook declarations (live inside on_load body) and method names
        hookDecls: dict[str, HookDeclNode] = {}
        hasSendMessageDecl = False
        methodNames: set[str] = set()

        for member in node.body:
            if isinstance(member, HookSendMessageDeclNode):
                hasSendMessageDecl = True
            elif isinstance(member, FunNode):
                methodNames.add(member.name)
                # hooks and hook_send_message are declared inside on_load
                if member.name == "on_load":
                    for stmt in member.body:
                        if isinstance(stmt, HookDeclNode):
                            hookDecls[stmt.hookName] = stmt
                        elif isinstance(stmt, HookSendMessageDeclNode):
                            hasSendMessageDecl = True

        self._registeredHooks = hookDecls
        self._hookSendMessageDeclared = hasSendMessageDecl
        self._handlerMethods = methodNames

        # check hook declarations have handlers
        hasPreRequest = "pre_request" in methodNames
        hasPostRequest = "post_request" in methodNames

        for hookName, hookNode in hookDecls.items():
            if not hasPreRequest and not hasPostRequest:
                self._warn(
                    f'Hook "{hookName}" is registered but has no handler '
                    f'in pre_request or post_request.',
                    hookNode,
                )

        # check on_send_message used without hook_send_message
        if "on_send_message" in methodNames and not hasSendMessageDecl:
            self._error(
                "on_send_message handler defined but hook_send_message is not declared in on_load.",
                node,
            )

        # visit all members
        self._pushScope()
        for member in node.body:
            self._visitNode(member)
        self._popScope()

    def _visitSettings(self, node: SettingsNode) -> None:
        pass  # already collected in first pass

    def _visitFun(self, node: FunNode) -> None:
        self._pushScope()
        for param in node.params:
            self._declareVal(param.name, param)
        if node.inlineExpr is not None:
            self._visitNode(node.inlineExpr)
        else:
            name = node.name
            if name in _REQUEST_HANDLERS:
                self._checkHandlerTermination(node.body, name, node)
            self._visitBody(node.body)
        self._popScope()

    def _visitVal(self, node: ValNode) -> None:
        self._visitNode(node.value)
        self._declareVal(node.name, node)

    def _visitVar(self, node: VarNode) -> None:
        self._visitNode(node.value)
        # var can be reassigned — just visit, don't lock

    def _visitAssign(self, node: AssignNode) -> None:
        self._visitNode(node.value)
        # check val reassignment
        if isinstance(node.target, IdentNode):
            name = node.target.name
            if self._isVal(name):
                self._error(
                    f'Cannot reassign val "{name}". Use var if reassignment is needed.',
                    node,
                )
        self._visitNode(node.target)

    def _visitIf(self, node: IfNode) -> None:
        self._visitNode(node.condition)
        self._pushScope(); self._visitBody(node.thenBody); self._popScope()
        for cond, body in node.elseIfs:
            self._visitNode(cond)
            self._pushScope(); self._visitBody(body); self._popScope()
        if node.elseBody:
            self._pushScope(); self._visitBody(node.elseBody); self._popScope()

    def _visitSwitch(self, node: SwitchNode) -> None:
        self._visitNode(node.subject)
        for case in node.cases:
            for pat in case.patterns:
                self._visitNode(pat)
            self._pushScope(); self._visitBody(case.body); self._popScope()
        if node.elseBody:
            self._pushScope(); self._visitBody(node.elseBody); self._popScope()

    def _visitFor(self, node: ForNode) -> None:
        self._visitNode(node.iterable)
        self._pushScope()
        for t in node.targets:
            self._declareVal(t, node)
        self._visitBody(node.body)
        self._popScope()

    def _visitWhile(self, node: WhileNode) -> None:
        self._visitNode(node.condition)
        self._pushScope(); self._visitBody(node.body); self._popScope()

    def _visitSus(self, node: SusNode) -> None:
        self._pushScope(); self._visitBody(node.body); self._popScope()
        for handler in node.handlers:
            self._pushScope()
            if handler.asName:
                self._declareVal(handler.asName, handler)
            self._visitBody(handler.body)
            self._popScope()
        if node.finallyBody:
            self._pushScope(); self._visitBody(node.finallyBody); self._popScope()

    def _visitExprStmt(self, node: ExprStmtNode) -> None:
        self._visitNode(node.expr)

    def _visitCall(self, node: CallNode) -> None:
        # detect setting("key") calls
        callee = node.callee
        if isinstance(callee, IdentNode) and callee.name == "setting":
            if node.args:
                firstArg = node.args[0].value
                if isinstance(firstArg, StringNode) and len(firstArg.parts) == 1 and isinstance(firstArg.parts[0], str):
                    key = firstArg.parts[0]
                    self._usedSettingKeys.add(key)
                    if self._declaredSettings and key not in self._declaredSettings:
                        self._error(
                            f'Setting "{key}" is not declared in settings block.',
                            node,
                        )
        for arg in node.args:
            self._visitNode(arg.value)
        self._visitNode(callee)

    def _visitReturn(self, node: ReturnNode) -> None:
        if node.value is not None:
            self._visitNode(node.value)

    def _visitRaise(self, node: RaiseNode) -> None:
        self._visitNode(node.value)

    # terminal hook operators — no semantic checks needed beyond existence
    def _visitCancel(self, node: CancelNode) -> None:
        pass

    def _visitModify(self, node: ModifyNode) -> None:
        pass

    def _visitDefault(self, node: DefaultNode) -> None:
        pass

    # ------------------------------------------------------------------
    # handler termination check
    # ------------------------------------------------------------------

    def _checkHandlerTermination(self, body: list, handlerName: str, node: Any) -> None:
        """
        Every execution path in pre_request / post_request / on_send_message
        must end with cancel, modify, or default.
        """
        if not self._allPathsTerminate(body):
            self._error(
                f'Not all execution paths in "{handlerName}" end with a terminal '
                f'action (cancel / modify / default).',
                node,
            )

    def _allPathsTerminate(self, stmts: list) -> bool:
        if not stmts:
            return False
        last = stmts[-1]

        if isinstance(last, (CancelNode, ModifyNode, DefaultNode)):
            return True

        if isinstance(last, ReturnNode):
            # explicit return is not a hook terminal — flag as missing
            return False

        if isinstance(last, IfNode):
            # all branches must terminate; else branch must exist
            if not last.elseBody:
                return False
            thenOk = self._allPathsTerminate(last.thenBody)
            elseOk = self._allPathsTerminate(last.elseBody)
            elseIfsOk = all(self._allPathsTerminate(b) for _, b in last.elseIfs)
            return thenOk and elseOk and elseIfsOk

        if isinstance(last, SwitchNode):
            if not last.elseBody:
                return False
            casesOk = all(self._allPathsTerminate(c.body) for c in last.cases)
            elseOk = self._allPathsTerminate(last.elseBody)
            return casesOk and elseOk

        if isinstance(last, SusNode):
            bodyOk = self._allPathsTerminate(last.body)
            handlersOk = all(self._allPathsTerminate(h.body) for h in last.handlers)
            return bodyOk and handlersOk

        if isinstance(last, ExprStmtNode):
            return False

        return False

    # ------------------------------------------------------------------
    # unused settings warning (run after full traversal)
    # ------------------------------------------------------------------

    def _checkUnusedSettings(self) -> None:
        for key, settingNode in self._declaredSettings.items():
            if key not in self._usedSettingKeys:
                self._warn(
                    f'Setting "{key}" is declared but never accessed via setting("{key}").',
                    settingNode,
                )

    # ------------------------------------------------------------------
    # scope helpers for val tracking
    # ------------------------------------------------------------------

    def _pushScope(self) -> None:
        self._valScopes.append(set())

    def _popScope(self) -> None:
        if self._valScopes:
            self._valScopes.pop()

    def _declareVal(self, name: str, node: Any) -> None:
        if self._valScopes:
            self._valScopes[-1].add(name)

    def _isVal(self, name: str) -> bool:
        for scope in self._valScopes:
            if name in scope:
                return True
        return False

    # ------------------------------------------------------------------
    # error / warning helpers
    # ------------------------------------------------------------------

    def _error(self, msg: str, node: Any) -> None:
        line = getattr(node, "line", 0)
        col = getattr(node, "col", 0)
        srcLine = self.srcLines[line - 1] if 0 < line <= len(self.srcLines) else ""
        self.errors.append(SemanticError(msg, self.filename, line, col, srcLine))

    def _warn(self, msg: str, node: Any) -> None:
        line = getattr(node, "line", 0)
        col = getattr(node, "col", 0)
        srcLine = self.srcLines[line - 1] if 0 < line <= len(self.srcLines) else ""
        self.warnings.append(SemanticWarning(msg, self.filename, line, col, srcLine))


# ------------------------------------------------------------------
# visitor dispatch table  (avoids if/elif chains)
# ------------------------------------------------------------------

from ..ast import (
    BinaryOpNode, UnaryOpNode, ArgNode, IndexNode, SliceNode,
    LambdaNode, IfExprNode, SwitchExprNode, NumberNode,
    BoolNode, NullNode, ListNode, DictNode, SetNode,
    BreakNode, ContinueNode, HookDeclNode, HookSendMessageDeclNode,
    MenuItemNode,
)

_VISITORS: dict[type, Any] = {
    MetainfoNode:           Analyzer._visitMetainfo,
    ImportNode:             Analyzer._visitImport,
    RawNode:                Analyzer._visitRaw,
    PluginNode:             Analyzer._visitPlugin,
    SettingsNode:           Analyzer._visitSettings,
    FunNode:                Analyzer._visitFun,
    ValNode:                Analyzer._visitVal,
    VarNode:                Analyzer._visitVar,
    AssignNode:             Analyzer._visitAssign,
    IfNode:                 Analyzer._visitIf,
    SwitchNode:             Analyzer._visitSwitch,
    ForNode:                Analyzer._visitFor,
    WhileNode:              Analyzer._visitWhile,
    SusNode:                Analyzer._visitSus,
    ExprStmtNode:           Analyzer._visitExprStmt,
    CallNode:               Analyzer._visitCall,
    ReturnNode:             Analyzer._visitReturn,
    RaiseNode:              Analyzer._visitRaise,
    CancelNode:             Analyzer._visitCancel,
    ModifyNode:             Analyzer._visitModify,
    DefaultNode:            Analyzer._visitDefault,
    # nodes with children that need visiting
    BinaryOpNode:           lambda self, n: (self._visitNode(n.left), self._visitNode(n.right)),
    UnaryOpNode:            lambda self, n: self._visitNode(n.operand),
    IndexNode:              lambda self, n: (self._visitNode(n.obj), self._visitNode(n.index)),
    SliceNode:              lambda self, n: (self._visitNode(n.obj), self._visitNode(n.start), self._visitNode(n.end)),
    MemberNode:             lambda self, n: self._visitNode(n.obj),
    IfExprNode:             lambda self, n: (self._visitNode(n.condition), self._visitNode(n.thenVal), self._visitNode(n.elseVal)),
    SwitchExprNode:         lambda self, n: (self._visitNode(n.subject), [self._visitNode(c) for c in n.cases]),
    LambdaNode:             lambda self, n: (
                                self._pushScope() or
                                [self._declareVal(p.name, p) for p in n.params] or
                                (self._visitNode(n.body) if not isinstance(n.body, list) else self._visitBody(n.body)) or
                                self._popScope()
                            ),
    SwitchCaseNode:         lambda self, n: ([self._visitNode(p) for p in n.patterns], self._visitBody(n.body)),
    ListNode:               lambda self, n: [self._visitNode(e) for e in n.elements],
    DictNode:               lambda self, n: [(self._visitNode(k), self._visitNode(v)) for k, v in n.pairs],
    SetNode:                lambda self, n: [self._visitNode(e) for e in n.elements],
    # leaf nodes
    IdentNode:              lambda self, n: None,
    NumberNode:             lambda self, n: None,
    StringNode:             lambda self, n: None,
    BoolNode:               lambda self, n: None,
    NullNode:               lambda self, n: None,
    BreakNode:              lambda self, n: None,
    ContinueNode:           lambda self, n: None,
    HookDeclNode:           lambda self, n: None,
    HookSendMessageDeclNode: lambda self, n: None,
    MenuItemNode:           lambda self, n: None,
}
