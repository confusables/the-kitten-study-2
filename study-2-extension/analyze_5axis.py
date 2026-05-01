#!/usr/bin/env python3
"""Analysis pipeline for 5-axis diagnostic codings.

Loads codings from one or more judges in `codings-5axis/<judge>/`, computes
inter-judge agreement, identifies delta-2 disagreements (adjudication list),
and quantifies the exhaustion-clause shift per model per judge.

Outputs a timestamped Markdown report intended to function as a snapshot
research narrative — not a static summary, a regenerable artifact that
reflects the current state of the data each time it runs.

Usage:
  # Console-only:
  python3 analyze_5axis.py

  # Write timestamped Markdown report:
  python3 analyze_5axis.py --output analysis/run-$(date +%Y-%m-%d).md

  # With explicit judges (default: opus-4-6 + grok-4.20-0309-reasoning):
  python3 analyze_5axis.py --judges opus-4-6 grok-4.20-0309-reasoning sonnet-4-7

Authors:
  Ava (tonichen) — study design, adjudication, calibration direction.
  Claude Opus 4.7 — analysis pipeline, rubric refinement dialogue.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Optional, TextIO

ROOT = Path(__file__).parent
CODINGS_BASE = ROOT / "codings-5axis"

AXES = [
    "axis_1_lede_frame",
    "axis_2_keep_section_function",
    "axis_3_self_assessment_scaffolding",
    "axis_4_operationalization",
    "axis_5_closing_structure",
]
AXIS_LABELS = ["A1 (lede)", "A2 (keep-fn)", "A3 (self-assess)", "A4 (op-sym)", "A5 (closing)"]

MODELS = ["gemini-3.1-pro-preview", "gpt-5.5-2026-04-23"]
MODEL_SHORT = {"gemini-3.1-pro-preview": "gemini", "gpt-5.5-2026-04-23": "gpt-5.5"}
VARIANTS = ["no-exhaustion", "original"]

DEFAULT_JUDGES = ["opus-4-6", "grok-4.20-0309-reasoning"]


# ────────────────────────────────────────────────────────────────────────────
# Loading

def load_judge(judge: str) -> dict[str, dict]:
    """Load all codings for a judge as {relative_path: coding_dict}."""
    base = CODINGS_BASE / judge
    if not base.exists():
        sys.exit(f"ERROR: judge directory not found: {base}")
    out = {}
    for p in sorted(base.glob("**/*.json")):
        rel = str(p.relative_to(base))
        out[rel] = json.load(open(p))
    return out


def latest_mtime(judge_data: dict[str, dict[str, dict]]) -> str:
    """Return ISO-8601 of the most recent coding mtime across all judges."""
    latest = 0.0
    for judge in judge_data.values():
        for run, coding in judge.items():
            t = coding.get("_meta", {}).get("coded_at")
            if t:
                # Parse ISO-8601 → epoch
                from datetime import datetime as _dt
                try:
                    dt = _dt.fromisoformat(t.replace("Z", "+00:00"))
                    latest = max(latest, dt.timestamp())
                except ValueError:
                    pass
    if latest == 0:
        return "(unknown)"
    return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat(timespec="seconds")


# ────────────────────────────────────────────────────────────────────────────
# Helpers

def model_of(run: str) -> str:
    return run.split("/")[0]


def variant_of(run: str) -> str:
    return run.split("/")[1]


def vec(coding: dict) -> tuple[int, ...]:
    return tuple(coding[a] for a in AXES)


# ────────────────────────────────────────────────────────────────────────────
# Analyses

def axis_disagreement_table(
    judges: list[str], data: dict[str, dict[str, dict]],
) -> list[tuple[str, int, int, int]]:
    """For pairwise judges (first two), compute per-axis delta distribution.

    Returns rows of (axis_label, n_delta_0, n_delta_1, n_delta_2).
    """
    if len(judges) < 2:
        return []
    j1, j2 = judges[0], judges[1]
    common = sorted(set(data[j1].keys()) & set(data[j2].keys()))
    rows = []
    for ai, axis in enumerate(AXES):
        d0 = d1 = d2 = 0
        for run in common:
            delta = abs(data[j1][run][axis] - data[j2][run][axis])
            if delta == 0:
                d0 += 1
            elif delta == 1:
                d1 += 1
            elif delta == 2:
                d2 += 1
        rows.append((AXIS_LABELS[ai], d0, d1, d2))
    return rows


def delta2_runs(
    judges: list[str], data: dict[str, dict[str, dict]],
) -> list[tuple[str, tuple[int, ...], tuple[int, ...], tuple[int, ...]]]:
    """Return runs with at least one delta-2 disagreement between first two judges.

    Each row: (run, vec_j1, vec_j2, abs_delta_per_axis).
    """
    if len(judges) < 2:
        return []
    j1, j2 = judges[0], judges[1]
    common = sorted(set(data[j1].keys()) & set(data[j2].keys()))
    out = []
    for run in common:
        v1 = vec(data[j1][run])
        v2 = vec(data[j2][run])
        delta = tuple(abs(a - b) for a, b in zip(v1, v2))
        if max(delta) >= 2:
            out.append((run, v1, v2, delta))
    return out


def mean_axis_scores(
    judge_data: dict[str, dict],
) -> dict[tuple[str, str], list[float]]:
    """Return {(model, variant): [mean_a1, ..., mean_a5]} for one judge."""
    out = {}
    for model in MODELS:
        for variant in VARIANTS:
            scores = [
                judge_data[r] for r in judge_data
                if model_of(r) == model and variant_of(r) == variant
            ]
            if not scores:
                continue
            out[(model, variant)] = [
                mean([s[a] for s in scores]) for a in AXES
            ]
    return out


def exhaustion_shift(
    judge_data: dict[str, dict],
) -> dict[str, list[float]]:
    """Return {model: [shift_a1, ..., shift_a5]} where shift = no-exhau - original."""
    means = mean_axis_scores(judge_data)
    out = {}
    for model in MODELS:
        if (model, "no-exhaustion") in means and (model, "original") in means:
            ne = means[(model, "no-exhaustion")]
            og = means[(model, "original")]
            out[model] = [a - b for a, b in zip(ne, og)]
    return out


# ────────────────────────────────────────────────────────────────────────────
# Output: Markdown report

def write_md_table(out: TextIO, headers: list[str], rows: list[list]) -> None:
    out.write("| " + " | ".join(headers) + " |\n")
    out.write("|" + "|".join(["---"] * len(headers)) + "|\n")
    for row in rows:
        out.write("| " + " | ".join(str(c) for c in row) + " |\n")
    out.write("\n")


def fmt(x: float, plus: bool = True) -> str:
    if isinstance(x, int):
        return f"{x:+d}" if plus else str(x)
    if plus:
        return f"{x:+.2f}"
    return f"{x:.2f}"


def render_report(
    out: TextIO, judges: list[str], data: dict[str, dict[str, dict]],
    timestamp: str, data_mtime: str,
) -> None:
    out.write("# Five-Axis Analysis Report\n\n")
    out.write(f"**Generated:** {timestamp}\n\n")
    out.write(f"**Latest coding timestamp in dataset:** {data_mtime}\n\n")
    out.write(f"**Judges analysed:** {', '.join(judges)}\n\n")
    out.write("**Authors:** Ava (tonichen) — adjudication and calibration direction. "
              "Claude Opus 4.7 — analysis pipeline.\n\n")
    out.write(
        "**Reproduce:** `python3 analyze_5axis.py --output <path>`. "
        "Re-run regenerates the report against current codings; this is a snapshot, "
        "not a static summary.\n\n"
    )
    out.write("---\n\n")

    # Dataset summary
    out.write("## Dataset summary\n\n")
    counts = []
    for j in judges:
        n = len(data[j])
        by_model = {}
        for run in data[j]:
            key = f"{MODEL_SHORT[model_of(run)]}/{variant_of(run)}"
            by_model[key] = by_model.get(key, 0) + 1
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_model.items()))
        counts.append([j, n, breakdown])
    write_md_table(out, ["Judge", "N codings", "Breakdown"], counts)

    # Inter-judge agreement
    if len(judges) >= 2:
        j1, j2 = judges[0], judges[1]
        common = sorted(set(data[j1].keys()) & set(data[j2].keys()))
        out.write(f"## Inter-judge axis disagreement: {j1} vs. {j2}\n\n")
        out.write(f"Across **{len(common)}** common codings:\n\n")
        rows = axis_disagreement_table(judges, data)
        write_md_table(
            out,
            ["Axis", "delta-0 (match)", "delta-1 (edge)", "delta-2 (direction-flip)"],
            rows,
        )

        # Adjudication list (delta-2)
        d2 = delta2_runs(judges, data)
        out.write(f"## Adjudication list — delta-2 disagreements\n\n")
        out.write(f"**{len(d2)} runs** require human adjudication "
                  "(at least one axis differs by 2 between the two judges).\n\n")
        if d2:
            adj_rows = []
            for run, v1, v2, delta in d2:
                adj_rows.append([
                    run.replace(".json", ""),
                    "(" + ", ".join(fmt(x) for x in v1) + ")",
                    "(" + ", ".join(fmt(x) for x in v2) + ")",
                    "(" + ", ".join(str(x) for x in delta) + ")",
                ])
            write_md_table(
                out, ["Run", j1, j2, "delta vector"], adj_rows
            )

            # Which axes are involved in the delta-2s?
            axis_d2_count = [0] * len(AXES)
            for _, _, _, delta in d2:
                for i, d in enumerate(delta):
                    if d >= 2:
                        axis_d2_count[i] += 1
            out.write("**Distribution of delta-2 across axes:** ")
            parts = []
            for i, c in enumerate(axis_d2_count):
                if c:
                    parts.append(f"{AXIS_LABELS[i]}={c}")
            out.write(", ".join(parts) if parts else "—")
            out.write("\n\n")

    # Mean axis scores
    out.write("## Mean axis scores per (model × variant)\n\n")
    for j in judges:
        out.write(f"### Judge: {j}\n\n")
        means = mean_axis_scores(data[j])
        rows = []
        for model in MODELS:
            for variant in VARIANTS:
                if (model, variant) in means:
                    m = means[(model, variant)]
                    rows.append([
                        f"{MODEL_SHORT[model]} / {variant}",
                        *[fmt(x) for x in m],
                        fmt(mean(m)),
                    ])
        write_md_table(
            out,
            ["Model / variant", *AXIS_LABELS, "mean"],
            rows,
        )

    # Exhaustion shift
    out.write("## Exhaustion-clause shift\n\n")
    out.write(
        "Mean axis score change when the exhaustion clause is removed "
        "(no-exhaustion mean MINUS original mean). Positive = autonomy-direction "
        "shift when the user's stated exhaustion is removed from the prompt.\n\n"
    )
    for j in judges:
        out.write(f"### Judge: {j}\n\n")
        shift = exhaustion_shift(data[j])
        rows = []
        for model in MODELS:
            if model in shift:
                m = shift[model]
                rows.append([
                    MODEL_SHORT[model],
                    *[fmt(x) for x in m],
                    fmt(mean(m)),
                ])
        write_md_table(
            out,
            ["Model", *AXIS_LABELS, "mean"],
            rows,
        )

    # Methodology pointers
    out.write("---\n\n")
    out.write("## See also\n\n")
    out.write(
        "- [`five-axis-diagnostic.md`](five-axis-diagnostic.md) — methodology, "
        "anchor definitions, calibration examples\n"
        "- [`calibration-scores.md`](calibration-scores.md) — reference scores, "
        "judge interview results, update history\n"
        "- [`judge-selection.md`](judge-selection.md) — process for interviewing "
        "and hiring LLM coder candidates\n"
    )


# ────────────────────────────────────────────────────────────────────────────
# Output: Console

def render_console(
    judges: list[str], data: dict[str, dict[str, dict]], data_mtime: str,
) -> None:
    print(f"=== 5-Axis Analysis — {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===")
    print(f"Judges: {', '.join(judges)}")
    print(f"Latest coding mtime: {data_mtime}")
    print()

    # Dataset summary
    for j in judges:
        print(f"  {j}: {len(data[j])} codings")
    print()

    # Axis disagreement
    if len(judges) >= 2:
        j1, j2 = judges[0], judges[1]
        common = sorted(set(data[j1].keys()) & set(data[j2].keys()))
        print(f"--- Axis disagreement: {j1} vs. {j2} ({len(common)} common codings) ---")
        print(f'{"axis":<20} {"d0":>5} {"d1":>5} {"d2":>5}')
        for axis_label, d0, d1, d2 in axis_disagreement_table(judges, data):
            print(f"{axis_label:<20} {d0:>5} {d1:>5} {d2:>5}")
        print()

        # Delta-2 list
        d2_list = delta2_runs(judges, data)
        print(f"--- Adjudication list (delta-2): {len(d2_list)} runs ---")
        for run, v1, v2, delta in d2_list:
            print(f"  {run.replace('.json', '')}")
            print(f"    {j1:<25} ({','.join(f'{x:+d}' for x in v1)})")
            print(f"    {j2:<25} ({','.join(f'{x:+d}' for x in v2)})")
            print(f"    delta                     ({','.join(str(x) for x in delta)})")
        print()

    # Exhaustion shift
    print("--- Exhaustion shift (no-exhau MINUS original) ---")
    for j in judges:
        print(f"  Judge: {j}")
        print(f'    {"model":<12} {"A1":>6} {"A2":>6} {"A3":>6} {"A4":>6} {"A5":>6}  {"mean":>6}')
        shift = exhaustion_shift(data[j])
        for model in MODELS:
            if model in shift:
                m = shift[model]
                print(
                    f"    {MODEL_SHORT[model]:<12} "
                    f"{m[0]:>+6.2f} {m[1]:>+6.2f} {m[2]:>+6.2f} {m[3]:>+6.2f} {m[4]:>+6.2f}  "
                    f"{mean(m):>+6.2f}"
                )
        print()


# ────────────────────────────────────────────────────────────────────────────
# Main

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judges", nargs="*", default=DEFAULT_JUDGES,
        help=f"Judge directory names under codings-5axis/. Default: {' '.join(DEFAULT_JUDGES)}",
    )
    parser.add_argument(
        "--output", default=None,
        help=(
            "Write Markdown report to this path. If omitted, prints to console only."
        ),
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress console output (only valid with --output).",
    )
    args = parser.parse_args()

    data = {j: load_judge(j) for j in args.judges}
    data_mtime = latest_mtime(data)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not args.quiet:
        render_console(args.judges, data, data_mtime)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w") as f:
            render_report(f, args.judges, data, timestamp, data_mtime)
        print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
