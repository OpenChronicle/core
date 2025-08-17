from __future__ import annotations

import argparse
import sys

from openchronicle import __version__


def main(argv: list[str] | None = None) -> int:
    # Check only for --version flag, pass everything else to typer CLI
    if argv is None:
        argv = sys.argv[1:]

    if "--version" in argv:
        from rich.console import Console

        Console().print(__version__)
        return 0

    # Run modern CLI app directly for all other commands
    from openchronicle.interfaces.cli.main import run as cli_run

    cli_run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
