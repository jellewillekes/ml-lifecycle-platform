from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def _should_skip(target: str) -> bool:
    return (
        target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
        or target.startswith("#")
    )


def _normalize_target(raw: str) -> str:
    target = raw.strip()
    if " " in target and not target.startswith("<"):
        target = target.split(" ", 1)[0]
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return target.split("#", 1)[0]


def main() -> int:
    failures: list[str] = []
    for doc_file in DOC_FILES:
        content = doc_file.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(content):
            raw_target = match.group(1).strip()
            if _should_skip(raw_target):
                continue
            target = _normalize_target(raw_target)
            if not target:
                continue
            resolved = (doc_file.parent / target).resolve()
            if not resolved.exists():
                failures.append(
                    f"{doc_file.relative_to(REPO_ROOT)} -> missing path: {raw_target}"
                )

    if failures:
        print("Docs link/path check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Docs link/path check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
