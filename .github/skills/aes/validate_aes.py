#!/usr/bin/env python3
"""Standalone AES validator — no external dependencies required.

Usage:
    python validate_aes.py                        # validates scripts/ralph/aes.json
    python validate_aes.py path/to/aes.json       # validates a specific file

Exit codes:
    0 — validation passed
    1 — validation failed (errors printed to stdout)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_DEFAULT_AES_PATH = Path("scripts/ralph/aes.json")

_ID_PATTERN = re.compile(r"^[A-Z]+-[0-9]+$")
_VALID_COMPLEXITY = {"trivial", "standard", "complex"}
_VALID_RISK = {"low", "medium", "high"}
_STORY_REQUIRED_FIELDS = (
    "id",
    "title",
    "description",
    "priority",
    "complexity",
    "riskLevel",
    "preferredModel",
    "dependsOn",
    "implementationNotes",
    "acceptanceCriteria",
    "passes",
)


def _validate(aes: dict) -> list[str]:
    errors: list[str] = []

    # ── Top-level required fields ──────────────────────────────────────────
    for field in ("project", "branchName", "description", "userStories"):
        if field not in aes:
            errors.append(f"Missing required top-level field: '{field}'")
        elif not aes[field] and aes[field] is not False:
            errors.append(f"Top-level field '{field}' must not be empty")

    stories = aes.get("userStories", [])
    if not isinstance(stories, list) or len(stories) == 0:
        errors.append("'userStories' must be a non-empty array")
        return errors  # cannot validate individual stories without a list

    # ── Duplicate IDs ──────────────────────────────────────────────────────
    ids = [s.get("id") for s in stories if isinstance(s, dict)]
    seen: set = set()
    dupes = [i for i in ids if i in seen or seen.add(i)]  # type: ignore[func-returns-value]
    if dupes:
        errors.append(f"Duplicate story IDs: {dupes}")
    known_ids = {i for i in ids if i}

    # ── Per-story validation ───────────────────────────────────────────────
    for i, story in enumerate(stories):
        if not isinstance(story, dict):
            errors.append(f"Story {i + 1} is not an object")
            continue

        sid = story.get("id", f"story[{i + 1}]")

        for field in _STORY_REQUIRED_FIELDS:
            if field not in story:
                errors.append(f"{sid}: missing required field '{field}'")

        story_id = story.get("id")
        if story_id is not None and not _ID_PATTERN.match(str(story_id)):
            errors.append(
                f"{sid}: 'id' must match pattern [A-Z]+-[0-9]+ (got '{story_id}')"
            )

        priority = story.get("priority")
        if priority is not None and (not isinstance(priority, int) or priority < 1):
            errors.append(
                f"{sid}: 'priority' must be an integer ≥ 1 (got {priority!r})"
            )

        complexity = story.get("complexity")
        if complexity is not None and complexity not in _VALID_COMPLEXITY:
            errors.append(
                f"{sid}: 'complexity' must be one of trivial/standard/complex"
                f" (got '{complexity}')"
            )

        risk = story.get("riskLevel")
        if risk is not None and risk not in _VALID_RISK:
            errors.append(
                f"{sid}: 'riskLevel' must be one of low/medium/high (got '{risk}')"
            )

        preferred = story.get("preferredModel")
        if preferred is not None and (
            not isinstance(preferred, str) or not preferred.strip()
        ):
            errors.append(f"{sid}: 'preferredModel' must be a non-empty string")

        impl_notes = story.get("implementationNotes")
        if impl_notes is not None:
            if not isinstance(impl_notes, list):
                errors.append(f"{sid}: 'implementationNotes' must be an array")
            elif len(impl_notes) == 0:
                errors.append(f"{sid}: 'implementationNotes' must be a non-empty array")
            else:
                for item in impl_notes:
                    if not isinstance(item, str) or not item.strip():
                        errors.append(
                            f"{sid}: each 'implementationNotes' item must be a"
                            " non-empty string"
                        )

        ac = story.get("acceptanceCriteria")
        if ac is not None and (not isinstance(ac, list) or len(ac) == 0):
            errors.append(
                f"{sid}: 'acceptanceCriteria' must be a non-empty array"
            )

        deps = story.get("dependsOn")
        if deps is not None:
            if not isinstance(deps, list):
                errors.append(f"{sid}: 'dependsOn' must be an array")
            else:
                for dep in deps:
                    if dep == story_id:
                        errors.append(f"{sid}: story cannot depend on itself")
                    elif dep not in known_ids:
                        errors.append(
                            f"{sid}: 'dependsOn' references unknown story '{dep}'"
                        )

        passes = story.get("passes")
        if passes is not None and not isinstance(passes, bool):
            errors.append(f"{sid}: 'passes' must be a boolean (got {passes!r})")

    return errors


def main() -> None:
    aes_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_AES_PATH

    if not aes_path.exists():
        print(f"❌ File not found: {aes_path}")
        sys.exit(1)

    try:
        aes = json.loads(aes_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ {aes_path} is not valid JSON: {exc}")
        sys.exit(1)

    errors = _validate(aes)

    if errors:
        print(f"❌ aes.json validation failed ({len(errors)} error(s)):")
        for err in errors:
            print(f"   • {err}")
        print(f"\n   Fix the errors above in {aes_path} and re-run validation.")
        sys.exit(1)

    story_count = len(aes.get("userStories", []))
    print(
        f"✅ {aes_path} is valid"
        f" ({story_count} {'story' if story_count == 1 else 'stories'})"
    )


if __name__ == "__main__":
    main()
