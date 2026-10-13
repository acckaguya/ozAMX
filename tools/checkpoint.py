#!/usr/bin/env python3
"""Append a small, factual recovery checkpoint for the paper reproduction."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "traces" / "continuity-state.md"
KNOWN_EVIDENCE = (
    "traces/STATE.md",
    "traces/paper-state.md",
    "traces/environment-state.md",
    "docs/paper-study.md",
    "docs/reproduction-spec.md",
    "docs/environment.md",
)

SECRET_PATTERNS = (
    re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{8,})\b"),
    re.compile(r"(?i)\b(authorization\s*:\s*bearer|api[_ -]?key\s*[=:]|access[_ -]?token\s*[=:]|password\s*[=:])\s*\S+"),
)


def clean(value: str) -> str:
    value = value.strip()
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value.replace("\r", " ").replace("\n", " ")


def project_path(value: str) -> str:
    candidate = Path(value)
    resolved = (ROOT / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"path must remain inside project: {value}")
    return resolved.relative_to(ROOT).as_posix() or "."


def bullet_block(label: str, items: list[str]) -> list[str]:
    if not items:
        return [f"- {label}: (none supplied)"]
    return [f"- {label}:", *(f"  - {item}" for item in items)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--done", action="append", default=[], help="Completed evidence/result; repeatable")
    parser.add_argument("--pending", action="append", default=[], help="Next work item; repeatable")
    parser.add_argument("--command", action="append", default=[], help="Command run or intended; label status in text")
    parser.add_argument("--path", action="append", default=[], help="Project-relative path involved; repeatable")
    parser.add_argument("--note", action="append", default=[], help="Short factual note; repeatable")
    args = parser.parse_args()

    try:
        paths = [project_path(item) for item in args.path]
    except ValueError as exc:
        parser.error(str(exc))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    available = [f"`{path}`" for path in KNOWN_EVIDENCE if (ROOT / path).is_file()]
    sections = [
        f"\n## Checkpoint — {timestamp}\n",
        *bullet_block("Completed", [clean(x) for x in args.done]),
        *bullet_block("Pending", [clean(x) for x in args.pending]),
        *bullet_block("Commands", [f"`{clean(x)}`" for x in args.command]),
        *bullet_block("Paths", [f"`{x}`" for x in paths]),
        *bullet_block("Notes", [clean(x) for x in args.note]),
        f"- Known project evidence present: {', '.join(available) if available else '(none found)'}",
        "",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(sections))
    print(f"Checkpoint appended to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
