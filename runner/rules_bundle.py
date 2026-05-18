"""Build the rules-bundle text that gets injected via --append-system-prompt.

The bundle is a snapshot of the tile's rules/*.md taken from
~/.tessl/tiles/jbaruch/coding-policy/rules/. Snapshot is stored in
runner/rules_bundle.snapshot.md and committed; refresh by running this module
as __main__.
"""

from __future__ import annotations

import sys
from pathlib import Path

TILE_RULES_DIR = Path.home() / ".tessl" / "tiles" / "jbaruch" / "coding-policy" / "rules"
SNAPSHOT_PATH = Path(__file__).parent / "rules_bundle.snapshot.md"


def build_from_tile() -> str:
    """Read tile rules from disk and concatenate them with separators."""
    if not TILE_RULES_DIR.is_dir():
        raise FileNotFoundError(
            f"Tile rules directory not found at {TILE_RULES_DIR}. "
            "Run `tessl install jbaruch/coding-policy` to populate it."
        )

    rules = sorted(TILE_RULES_DIR.glob("*.md"))
    if not rules:
        raise FileNotFoundError(f"No *.md rule files in {TILE_RULES_DIR}")

    parts = [
        "# Coding Policy Rules",
        "",
        "The following rules from jbaruch/coding-policy apply to all actions in this session.",
        "",
    ]
    for rule_path in rules:
        parts.append(f"\n<!-- source: {rule_path.name} -->\n")
        parts.append(rule_path.read_text())
    return "\n".join(parts)


def load_snapshot() -> str:
    """Return the committed snapshot used for actual experiment runs."""
    if not SNAPSHOT_PATH.is_file():
        raise FileNotFoundError(
            f"Snapshot {SNAPSHOT_PATH} missing. Run `python -m runner.rules_bundle` to build it."
        )
    return SNAPSHOT_PATH.read_text()


def refresh_snapshot() -> Path:
    bundle = build_from_tile()
    SNAPSHOT_PATH.write_text(bundle)
    return SNAPSHOT_PATH


if __name__ == "__main__":
    path = refresh_snapshot()
    print(f"Wrote {path} ({path.stat().st_size} bytes)", file=sys.stderr)
