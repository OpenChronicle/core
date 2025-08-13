import argparse
import re
import sys
from pathlib import Path


BROAD_PATTERNS = [
    re.compile(r"except\s+Exception\s*:"),
    re.compile(r"except\s*:"),
]

# Optional in-code allowlist (prefer baseline file for CI)
ALLOWLIST: dict[str, set[int]] = {
    # "relative/path/to/file.py": {10, 42},
}

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
REPO_ROOT = SRC_ROOT.parent


def find_violations() -> tuple[list[str], dict[str, str]]:
    violations: list[str] = []
    details: dict[str, str] = {}
    for py_file in SRC_ROOT.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except OSError:
            continue

        rel_path = py_file.resolve().relative_to(REPO_ROOT).as_posix()
        for idx, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pat in BROAD_PATTERNS:
                if pat.search(stripped):
                    if rel_path in ALLOWLIST and idx in ALLOWLIST[rel_path]:
                        continue
                    key = f"{rel_path}:{idx}"
                    violations.append(key)
                    details[key] = (
                        f"{rel_path}:{idx}: broad or bare except detected -> {stripped}"
                    )
                    break
    violations.sort()
    return violations, details


def load_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {line.strip() for line in content.splitlines() if line.strip()}


def save_baseline(path: Path, violations: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(violations) + ("\n" if violations else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for broad/bare except usage.")
    parser.add_argument(
        "--baseline",
        type=str,
        default=str(Path(__file__).resolve().parent / "exception_hygiene_baseline.txt"),
        help="Path to baseline file (relative paths).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["hard", "baseline-create", "check-new"],
        default="hard",
        help="hard = fail on any violations; baseline-create = write current"
            "to baseline; check-new = fail only on new vs baseline",    )
    args = parser.parse_args()

    violations, details = find_violations()
    baseline_path = Path(args.baseline)

    if args.mode == "baseline-create":
        save_baseline(baseline_path, violations)
        print(f"Baseline written to {baseline_path} with {len(violations)} entries.")
        return 0

    if args.mode == "check-new":
        baseline = load_baseline(baseline_path)
        current = set(violations)
        new_items = sorted(current - baseline)
        if new_items:
            print("New exception hygiene violations detected (not in baseline):")
            for key in new_items:
                print(details.get(key, key))
            return 1
        print(
            f"No new violations compared to baseline. Existing violations: {len(current)} (tracked)."
        )
        return 0

    # hard mode
    if violations:
        print("Exception hygiene violations found (replace with specific exceptions):")
        for key in violations:
            print(details[key])
        return 1
    print("No broad/bare except patterns detected. Hygiene OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
