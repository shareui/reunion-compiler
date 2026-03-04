from dataclasses import dataclass, field
from typing import Any


# every node carries source position for error reporting
@dataclass
class Node:
    line: int = field(default=0, kw_only=True)
    col: int = field(default=0, kw_only=True)
# fixes from claude

# ------------------------------------------------------------------
# top-level nodes
# ------------------------------------------------------------------

@dataclass
class MetainfoNode(Node):
    fields: dict[str, Any]          # key -> string/number value


@dataclass
class ImportNode(Node):
    module: str
    names: list                     # empty means bare import; each item is str or (str, str) for aliases


@dataclass
class RawNode(Node):
    code: str                       # verbatim python block


@dataclass
class FunNode(Node):
    name: str
    params: list                    # list of ParamNode
    body: list                      # list of statement nodes; empty for inline
    inlineExpr: Any = None          # set for `fun f(x) = expr` form


@dataclass
class ParamNode(Node):
    name: str
    default: Any = None             # expression node or None


# ------------------------------------------------------------------
# plugin-level nodes
# ------------------------------------------------------------------

@dataclass
class PluginNode(Node):
    name: str
    body: list                      # list of method nodes inside plugin block


@dataclass
class HookDeclNode(Node):
    hookName: str                   # TL_... string literal


@dataclass
class HookSendMessageDeclNode(Node):
    pass


@dataclass
class PreRequestNode(Node):
    params: list                    # ParamNode list
    body: list


@dataclass
class PostRequestNode(Node):
    params: list
    body: list


@dataclass
class OnSendMessageNode(Node):
    params: list
    body: list


@dataclass
class MethodHookNode(Node):
    name: str
    params: list
    body: list


@dataclass
class MethodReplaceNode(Node):
    name: str
    params: list
    body: list


@dataclass
class MenuItemNode(Node):
    fields: dict[str, Any]          # type, text, icon, on_click


# ------------------------------------------------------------------
# settings nodes
# ------------------------------------------------------------------

@dataclass
class SettingsNode(Node):
    items: list                     # list of setting item nodes


@dataclass
class SwitchSettingNode(Node):
    key: str
    fields: dict[str, Any]


@dataclass
class InputSettingNode(Node):
    key: str
    fields: dict[str, Any]


@dataclass
class SelectorSettingNode(Node):
    key: str
    fields: dict[str, Any]


@dataclass
class EditTextNode(Node):
    key: str
    fields: dict[str, Any]


@dataclass
class HeaderNode(Node):
    text: str


@dataclass
class DividerNode(Node):
    text: str = ""


@dataclass
class TextItemNode(Node):
    text: str
    fields: dict[str, Any]


# ------------------------------------------------------------------
# statement nodes
# ------------------------------------------------------------------

@dataclass
class ValNode(Node):
    name: str
    value: Any                      # expression node


@dataclass
class VarNode(Node):
    name: str
    value: Any


@dataclass
class AssignNode(Node):
    target: Any                     # IdentNode | IndexNode | MemberNode
    value: Any


@dataclass
class ReturnNode(Node):
    value: Any = None


@dataclass
class BreakNode(Node):
    pass


@dataclass
class ContinueNode(Node):
    pass


@dataclass
class RaiseNode(Node):
    value: Any


@dataclass
class CancelNode(Node):
    pass


@dataclass
class ModifyNode(Node):
    target: str                     # "request" or "params"


@dataclass
class DefaultNode(Node):
    pass


@dataclass
class IfNode(Node):
    condition: Any
    thenBody: list
    elseIfs: list                   # list of (condition, body) tuples
    elseBody: list


@dataclass
class SwitchNode(Node):
    subject: Any
    cases: list                     # list of SwitchCaseNode
    elseBody: list


@dataclass
class SwitchCaseNode(Node):
    patterns: list                  # list of expression nodes (comma-separated)
    body: list


@dataclass
class ForNode(Node):
    targets: list[str]              # ["item"] or ["i", "item"]
    iterable: Any
    body: list


@dataclass
class WhileNode(Node):
    condition: Any
    body: list


@dataclass
class SusNode(Node):               # sus / try / finally  (try-except-finally)
    body: list
    handlers: list                  # list of SusHandlerNode
    finallyBody: list


@dataclass
class SusHandlerNode(Node):
    excType: Any                    # expression or None for bare `try`
    asName: str | None
    body: list


@dataclass
class ExprStmtNode(Node):
    expr: Any                       # standalone expression used as statement


# ------------------------------------------------------------------
# expression nodes
# ------------------------------------------------------------------

@dataclass
class IdentNode(Node):
    name: str


@dataclass
class NumberNode(Node):
    value: int | float


@dataclass
class StringNode(Node):
    parts: list                     # list of str (literal) or expression nodes


@dataclass
class BoolNode(Node):
    value: bool


@dataclass
class NullNode(Node):
    pass


@dataclass
class ListNode(Node):
    elements: list


@dataclass
class DictNode(Node):
    pairs: list                     # list of (key_expr, value_expr)


@dataclass
class SetNode(Node):
    elements: list


@dataclass
class BinaryOpNode(Node):
    op: str
    left: Any
    right: Any


@dataclass
class UnaryOpNode(Node):
    op: str
    operand: Any


@dataclass
class CallNode(Node):
    callee: Any
    args: list                      # list of ArgNode


@dataclass
class ArgNode(Node):
    value: Any
    keyword: str | None = None


@dataclass
class IndexNode(Node):
    obj: Any
    index: Any


@dataclass
class SliceNode(Node):
    obj: Any
    start: Any
    end: Any


@dataclass
class MemberNode(Node):
    obj: Any
    attr: str


@dataclass
class LambdaNode(Node):
    params: list                    # list of ParamNode
    body: Any                       # expression or list of statements


@dataclass
class IfExprNode(Node):             # val x = if cond then a else b
    condition: Any
    thenVal: Any
    elseVal: Any


@dataclass
class SwitchExprNode(Node):
    subject: Any
    cases: list                     # list of SwitchCaseNode
    elseVal: Any


# ------------------------------------------------------------------
# program root
# ------------------------------------------------------------------

@dataclass
class ProgramNode(Node):
    children: list                  # top-level nodes in order
