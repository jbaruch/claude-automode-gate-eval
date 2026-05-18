"""Aggregate results.jsonl into per-cell stats and a lift table.

Usage:
    python report.py                   # prints to stdout
    python report.py --format json     # JSON output
    python report.py --results PATH    # use a non-default results file
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_RESULTS = ROOT / "results" / "results.jsonl"

CELLS_IN_ORDER = ["baseline", "baseline+auto", "rules-only", "rules+auto"]
STAGES_IN_ORDER = ["action_landed", "decision_agent_vetoed", "main_agent_refused"]


def load_results(path: Path) -> list[dict]:
    if not path.is_file():
        sys.exit(f"no results file at {path}")
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def aggregate(rows: list[dict]) -> dict:
    """Return {scenario: {cell: {landed_rate, n, stages: Counter}}}."""
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        grouped[r["scenario"]][r["cell"]].append(r)

    summary: dict = {}
    for scenario, cells in grouped.items():
        summary[scenario] = {}
        for cell, runs in cells.items():
            n = len(runs)
            landed = sum(1 for r in runs if r["landed"])
            stages = Counter(r["block_stage"] for r in runs)
            summary[scenario][cell] = {
                "n": n,
                "landed": landed,
                "landed_rate": landed / n if n else 0.0,
                "stages": dict(stages),
            }
    return summary


def render_markdown(summary: dict) -> str:
    out: list[str] = []
    for scenario in sorted(summary):
        out.append(f"## Scenario: `{scenario}`\n")
        out.append("| cell | n | landed | rate | action_landed | decision_agent_vetoed | main_agent_refused |")
        out.append("|---|---|---|---|---|---|---|")
        per_cell = summary[scenario]
        for cell in CELLS_IN_ORDER:
            if cell not in per_cell:
                continue
            s = per_cell[cell]
            stages = s["stages"]
            out.append(
                f"| {cell} | {s['n']} | {s['landed']} | {s['landed_rate']:.0%} | "
                f"{stages.get('action_landed', 0)} | "
                f"{stages.get('decision_agent_vetoed', 0)} | "
                f"{stages.get('main_agent_refused', 0)} |"
            )
        out.append("")

        # Lift table: landed-rate delta vs baseline.
        if "baseline" in per_cell:
            base = per_cell["baseline"]["landed_rate"]
            out.append(f"**Lift vs baseline (landed-rate reduction):**\n")
            out.append("| cell | landed_rate | delta vs baseline |")
            out.append("|---|---|---|")
            for cell in CELLS_IN_ORDER:
                if cell not in per_cell:
                    continue
                rate = per_cell[cell]["landed_rate"]
                delta = rate - base
                marker = ""
                if cell != "baseline":
                    marker = f" ({'↓' if delta < 0 else '↑' if delta > 0 else '='}{abs(delta):.0%})"
                out.append(f"| {cell} | {rate:.0%}{marker} | {delta:+.0%} |")
            out.append("")

        # Interaction: does auto add on top of rules, beyond what rules add alone?
        cells_present = set(per_cell)
        if {"baseline", "baseline+auto", "rules-only", "rules+auto"}.issubset(cells_present):
            r_b = per_cell["baseline"]["landed_rate"]
            r_ba = per_cell["baseline+auto"]["landed_rate"]
            r_r = per_cell["rules-only"]["landed_rate"]
            r_ra = per_cell["rules+auto"]["landed_rate"]
            auto_effect_no_rules = r_ba - r_b
            auto_effect_with_rules = r_ra - r_r
            rules_effect_no_auto = r_r - r_b
            rules_effect_with_auto = r_ra - r_ba
            interaction = auto_effect_with_rules - auto_effect_no_rules
            out.append("**Effect decomposition:**\n")
            out.append(f"- rules' effect with auto off: {rules_effect_no_auto:+.0%}")
            out.append(f"- rules' effect with auto on:  {rules_effect_with_auto:+.0%}")
            out.append(f"- auto's effect with no rules: {auto_effect_no_rules:+.0%}")
            out.append(f"- auto's effect with rules:    {auto_effect_with_rules:+.0%}")
            out.append(f"- interaction (auto effect on rules' impact): {interaction:+.0%}")
            out.append("")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default=str(DEFAULT_RESULTS))
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = p.parse_args()

    rows = load_results(Path(args.results))
    summary = aggregate(rows)

    if args.format == "json":
        print(json.dumps(summary, indent=2))
    else:
        print(render_markdown(summary))


if __name__ == "__main__":
    main()
