"""
Shared error formatting for Reunion compiler.

Produces output like:

  error: Expected '}' but got 'fun' (got 'fun')
  --> myfile.reu:12:5
     |
  12 |     fun on_load() {
     |     ^^^
"""
import os
import sys

_ANSI = sys.stderr.isatty() and os.getenv("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if _ANSI else text


def bold(t: str) -> str:   return _c("1", t)
def red(t: str) -> str:    return _c("1;31", t)
def yellow(t: str) -> str: return _c("1;33", t)
def cyan(t: str) -> str:   return _c("36", t)
def dim(t: str) -> str:    return _c("2", t)


def formatDiagnostic(
    *,
    kind: str,           # "error" | "warning"
    message: str,
    filename: str,
    line: int,
    col: int,
    source_line: str = "",
    length: int = 1,     # underline length
) -> str:
    label = red(f"{kind}: ") if kind == "error" else yellow(f"{kind}: ")
    header = f"{label}{bold(message)}"
    location = f"  {dim('-->')} {cyan(filename)}:{line}:{col}"

    if not source_line:
        return f"{header}\n{location}"

    gutter_w = len(str(line)) + 2   # "  12 | " -> width of left gutter
    gutter   = " " * gutter_w

    # align underline: col is 1-based
    underline_pad = col - 1
    underline     = "^" * max(length, 1)
    if kind == "error":
        underline = red(underline)
    else:
        underline = yellow(underline)

    lines = [
        header,
        location,
        f"  {dim(gutter[2:])}|",
        f"  {bold(str(line))} | {source_line}",
        f"  {dim(gutter[2:])}| {' ' * underline_pad}{underline}",
    ]
    return "\n".join(lines)
