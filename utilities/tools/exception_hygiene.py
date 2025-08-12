import argparse
import pathlib
import re
import sys
from typing import Iterable

PATTERNS = [
    re.compile(r"except\s*:\s*$"),           # bare except
    re.compile(r"except\s+Exception\b"),     # broad except Exception
]


def scan_file(path: pathlib.Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return hits
    for lineno, line in enumerate(text, start=1):
        for pat in PATTERNS:
            if pat.search(line):
                hits.append((lineno, line.rstrip()))
                break
    return hits


def iter_py_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for p in root.rglob("*.py"):
        if any(part in {"tests", "htmlcov"} for part in p.parts):
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="src/openchronicle", help="Root directory to scan")
    args = ap.parse_args()

    root = pathlib.Path(args.path).resolve()
    if not root.exists():
        print(f"Path not found: {root}")
        return 2

    total = 0
    failures: list[tuple[pathlib.Path, int, str]] = []
    for file in iter_py_files(root):
        hits = scan_file(file)
        total += len(hits)
        for lineno, line in hits:
            failures.append((file, lineno, line))

    if failures:
        print("Exception hygiene check FAILED. Offenders:")
        for f, ln, line in failures:
            print(f" - {f}:{ln}: {line}")
        return 1

    print("Exception hygiene check PASSED. No bare/broad except blocks found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
