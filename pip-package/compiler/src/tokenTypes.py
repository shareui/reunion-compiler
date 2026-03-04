from enum import Enum, auto
# fixes from claude

class TokenType(Enum):
    # literals
    NUMBER = auto()
    STRING = auto()
    BOOL = auto()
    NULL = auto()
    STRING_PART = auto()       # raw text segment inside interpolated string
    INTERP_EXPR = auto()       # ${...} or $ident expression text

    # identifiers and keywords
    IDENTIFIER = auto()
    KEYWORD = auto()

    # structural
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()

    # delimiters
    LPAREN = auto()            # (
    RPAREN = auto()            # )
    LBRACKET = auto()          # [
    RBRACKET = auto()          # ]
    LBRACE = auto()            # {
    RBRACE = auto()            # }
    COMMA = auto()             # ,
    COLON = auto()             # :
    SEMICOLON = auto()         # ;
    DOT = auto()               # .

    # operators
    ARROW = auto()             # ->
    ASSIGN = auto()            # =
    PLUS = auto()              # +
    MINUS = auto()             # -
    STAR = auto()              # *
    SLASH = auto()             # /
    PERCENT = auto()           # %
    STARSTAR = auto()          # **
    SLASHSLASH = auto()        # //
    EQ = auto()                # ==
    NEQ = auto()               # !=
    LT = auto()                # <
    GT = auto()                # >
    LTE = auto()               # <=
    GTE = auto()               # >=


KEYWORDS = {
    "import", "val", "var", "fun", "return", "if", "else", "then",
    "switch", "for", "while", "break", "continue", "in", "and", "or",
    "not", "sus", "try", "raise", "finally", "plugin", "metainfo",
    "settings", "hook", "hook_send_message", "cancel", "modify", "default",
    "method_hook", "method_replace", "menu_item", "raw", "log", "null",
    "true", "false",
    # settings item keywords
    "header", "divider", "text", "input", "selector", "edit_text",
    # misc
    "as",
}
