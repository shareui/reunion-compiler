import argparse
import sys
from pathlib import Path
from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    _VERSION = _pkg_version("reuc")
except PackageNotFoundError:
    _VERSION = "0.1.0"  # fallback when running from source without install

from .lexer import Lexer
from .parser import Parser
from .analyzer import Analyzer
from .analyzer.semanticError import ReunionSemanticError
from .parseError import ReunionParseError
from .errors import ReunionLexError
from .codegen import CodeGenerator
from .errorFormat import bold, red, yellow, dim

def compile(src: str, filename: str, verbose: bool = False) -> str:
    """Compile Reunion source to Python. Raises on errors."""
    lexer = Lexer(src, filename)
    tokens = lexer.tokenize()

    if verbose:
        print("=== TOKENS ===", file=sys.stderr)
        for tok in tokens:
            print(f"  {tok}", file=sys.stderr)

    parser = Parser(tokens, filename, src)
    ast = parser.parse()

    if verbose:
        print("\n=== AST ===", file=sys.stderr)
        print(ast, file=sys.stderr)

    analyzer = Analyzer(filename, src)
    _, warnings = analyzer.analyze(ast)

    if warnings:
        for w in warnings:
            print(str(w), file=sys.stderr)
        _printSummary(errors=0, warnings=len(warnings))

    gen = CodeGenerator()
    return gen.generate(ast)


# ─────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────

def _printSummary(errors: int, warnings: int) -> None:
    parts = []
    if errors:
        parts.append(red(f"{errors} error{'s' if errors != 1 else ''}"))
    if warnings:
        parts.append(yellow(f"{warnings} warning{'s' if warnings != 1 else ''}"))
    if parts:
        print(f"\n{bold('Summary:')} {', '.join(parts)}", file=sys.stderr)


def _buildArgParser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reuc",
        description="Reunion compiler — .reu → .plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  reuc plugin.reu\n"
            "  reuc plugin.reu output.plugin\n"
            "  reuc --check plugin.reu\n"
            "  reuc --verbose plugin.reu\n"
        ),
    )
    p.add_argument("input",  nargs="?", help="Source .reu file")
    p.add_argument("output", nargs="?", help="Output .plugin file (default: <input>.plugin)")
    p.add_argument("--check",   action="store_true", help="Syntax/semantic check only, no output written")
    p.add_argument("--verbose", action="store_true", help="Print tokens and AST to stderr")
    return p


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main() -> None:
    args = _buildArgParser().parse_args()

    print(f"{bold('Reunion compiler')} v{_VERSION}", file=sys.stderr)

    if not args.input:
        sys.exit(0)

    inputPath = Path(args.input)
    if not inputPath.exists():
        print(f"{red('error:')} file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    outputPath = Path(args.output) if args.output else inputPath.with_suffix(".plugin")

    try:
        src = inputPath.read_text(encoding="utf-8")
        code = compile(src, str(inputPath), args.verbose)

    except ReunionLexError as e:
        print(str(e), file=sys.stderr)
        _printSummary(errors=1, warnings=0)
        sys.exit(1)

    except ReunionParseError as e:
        print(str(e), file=sys.stderr)
        _printSummary(errors=1, warnings=0)
        sys.exit(1)

    except ReunionSemanticError as e:
        for err in e.errors:
            print(str(err), file=sys.stderr)
            print(file=sys.stderr)
        for w in e.warnings:
            print(str(w), file=sys.stderr)
            print(file=sys.stderr)
        _printSummary(errors=len(e.errors), warnings=len(e.warnings))
        sys.exit(1)

    except Exception as e:
        print(f"{red('internal error:')} {e}", file=sys.stderr)
        print(
            dim("This is a compiler bug. Please report it at https://github.com/shareui/reunion-compiler"),
            file=sys.stderr,
        )
        sys.exit(2)

    if args.check:
        print(f"{bold('OK')} {dim(str(inputPath))}", file=sys.stderr)
        sys.exit(0)

    outputPath.write_text(code, encoding="utf-8")
    print(f"{inputPath} {dim('→')} {outputPath}")


if __name__ == "__main__":
    main()
