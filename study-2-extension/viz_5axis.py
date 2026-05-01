#!/usr/bin/env python3
"""5-axis cluster visualization — generates three interactive HTML figures.

  1. Parallel coordinates: every response as a line across the 5 axes,
     colored by (model × variant). Shows individual responses and the
     exhaustion shift per axis.

  2. 2D PCA scatter: 5-vectors projected to 2D, colored by (model × variant).
     Calibration cases annotated. Shows cluster geometry and the
     no-exhaustion / original collapse.

  3. Radar overlay: 4 averaged (model × variant) vectors on a polar plot.
     Shows per-axis pattern of the exhaustion shift cleanly.

Inputs: codings-5axis/<judge>/ for two judges (default: opus-4-6 + grok).
Vectors are averaged across both judges per run.

Usage:
  python3 viz_5axis.py --output-dir analysis/figures/

Authors:
  Ava (tonichen) — study design, calibration, editorial direction.
  Claude Opus 4.7 — visualization pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.decomposition import PCA

ROOT = Path(__file__).parent
CODINGS_BASE = ROOT / "codings-5axis"

AXES = [
    "axis_1_lede_frame",
    "axis_2_keep_section_function",
    "axis_3_self_assessment_scaffolding",
    "axis_4_operationalization",
    "axis_5_closing_structure",
]
AXIS_LABELS = ["A1\nlede", "A2\nkeep-fn", "A3\nself-assess", "A4\nop-symmetry", "A5\nclosing"]
AXIS_LABELS_ONELINE = ["A1 (lede)", "A2 (keep-fn)", "A3 (self-assess)", "A4 (op-sym)", "A5 (closing)"]

# Color scheme: model = hue, variant = intensity
# gemini = blue (autonomy-coded surface vocab), gpt-5.5 = red (fragility-coded surface vocab)
# no-exhaustion = saturated, original = lighter / pulled toward fragility
COLORS = {
    ("gemini-3.1-pro-preview", "no-exhaustion"): "#1e6fbf",   # deep blue
    ("gemini-3.1-pro-preview", "original"):       "#7eb3e1",   # light blue
    ("gpt-5.5-2026-04-23", "no-exhaustion"):       "#e87e5e",   # coral
    ("gpt-5.5-2026-04-23", "original"):            "#b13c1d",   # dark red
}
LABELS_MV = {
    ("gemini-3.1-pro-preview", "no-exhaustion"): "gemini / no-exhaustion",
    ("gemini-3.1-pro-preview", "original"):       "gemini / original",
    ("gpt-5.5-2026-04-23", "no-exhaustion"):       "gpt-5.5 / no-exhaustion",
    ("gpt-5.5-2026-04-23", "original"):            "gpt-5.5 / original",
}
DEFAULT_JUDGES = ["opus-4-6", "grok-4.20-0309-reasoning"]

# Calibration cases worth labeling explicitly on the scatter.
# Each entry: (label, ax_offset_pixels, ay_offset_pixels) — tuned so labels
# don't overlap each other or the data points.
ANNOTATIONS = {
    "gemini-3.1-pro-preview/no-exhaustion/run-01":  ("gemini-01 (canonical autonomy)",          60,  -50),
    "gemini-3.1-pro-preview/no-exhaustion/run-04":  ("gemini-04 (A3 friction)",                 60,   25),
    "gemini-3.1-pro-preview/no-exhaustion/run-11":  ("gemini-11 (fragility under autonomy surface)", -90,  60),
    "gemini-3.1-pro-preview/no-exhaustion/run-18":  ("gemini-18 (closing-A2 subordination)",    65,  -25),
    "gpt-5.5-2026-04-23/no-exhaustion/run-01":      ("gpt-5.5/01 (canonical fragility)",       -110, -55),
    "gpt-5.5-2026-04-23/no-exhaustion/run-03":      ("gpt-5.5/03 (recoded fragility)",         -110,  55),
    "gpt-5.5-2026-04-23/no-exhaustion/run-17":      ("gpt-5.5/17 (surrender template)",          70,   65),
}


def hex_to_rgba(hex_color: str, alpha: float = 0.18) -> str:
    """Convert #RRGGBB to rgba(r, g, b, alpha) for plotly fill colors."""
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def load_judge(judge: str) -> dict[str, dict]:
    base = CODINGS_BASE / judge
    out = {}
    for p in sorted(base.glob("**/*.json")):
        rel = str(p.relative_to(base)).replace(".json", "")
        out[rel] = json.load(open(p))
    return out


def averaged_vectors(judges: list[str]) -> dict[str, list[float]]:
    """Return {run: [mean_a1, ..., mean_a5]} averaged across all judges."""
    data = {j: load_judge(j) for j in judges}
    common = sorted(set.intersection(*(set(d.keys()) for d in data.values())))
    out = {}
    for run in common:
        vec = [mean(data[j][run][a] for j in judges) for a in AXES]
        out[run] = vec
    return out


def model_of(run: str) -> str:
    return run.split("/")[0]


def variant_of(run: str) -> str:
    return run.split("/")[1]


# ────────────────────────────────────────────────────────────────────────────
# Figure 1: Parallel coordinates

def fig_parallel(vectors: dict[str, list[float]]) -> go.Figure:
    """Parallel coordinates: every run as a line. Color by (model × variant)."""
    fig = go.Figure()

    # Group by (model, variant)
    groups = {}
    for run, vec in vectors.items():
        key = (model_of(run), variant_of(run))
        groups.setdefault(key, []).append((run, vec))

    # Slight horizontal jitter so overlapping lines are distinguishable
    rng = np.random.default_rng(42)

    for key, items in groups.items():
        color = COLORS[key]
        label = LABELS_MV[key]
        x_base = list(range(5))

        # First trace gets the legend; subsequent lines hidden from legend
        first = True
        for run, vec in items:
            jitter = rng.uniform(-0.08, 0.08, size=5)
            x = [b + j for b, j in zip(x_base, jitter)]
            y = list(vec)
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines",
                line=dict(color=color, width=1.3),
                opacity=0.55,
                name=label if first else None,
                showlegend=first,
                legendgroup=label,
                hovertext=run.replace(model_of(run) + "/", "").replace(variant_of(run) + "/", ""),
                hoverinfo="text+y",
            ))
            first = False

    fig.update_xaxes(
        tickmode="array",
        tickvals=list(range(5)),
        ticktext=AXIS_LABELS_ONELINE,
        range=[-0.5, 4.5],
        showgrid=True, gridcolor="rgba(0,0,0,0.05)",
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=[-1, -0.5, 0, 0.5, 1],
        ticktext=["−1 (fragility)", "−0.5", "0", "+0.5", "+1 (autonomy)"],
        range=[-1.15, 1.15],
        showgrid=True, gridcolor="rgba(0,0,0,0.05)",
        zeroline=True, zerolinecolor="rgba(0,0,0,0.3)",
    )
    fig.update_layout(
        title="Parallel coordinates: 5-axis vectors per response (averaged across judges)",
        plot_bgcolor="white",
        height=550,
        margin=dict(l=80, r=40, t=80, b=80),
        legend=dict(yanchor="top", y=-0.15, xanchor="center", x=0.5, orientation="h"),
    )
    return fig


# ────────────────────────────────────────────────────────────────────────────
# Figure 2: 2D PCA scatter

def fig_scatter(vectors: dict[str, list[float]]) -> go.Figure:
    """2D PCA projection, colored by (model × variant), calibration cases annotated."""
    runs = list(vectors.keys())
    X = np.array([vectors[r] for r in runs])

    pca = PCA(n_components=2)
    Xp = pca.fit_transform(X)
    var = pca.explained_variance_ratio_

    fig = go.Figure()

    # Group by (model, variant)
    groups = {}
    for i, run in enumerate(runs):
        key = (model_of(run), variant_of(run))
        groups.setdefault(key, []).append((run, Xp[i]))

    for key, items in groups.items():
        color = COLORS[key]
        label = LABELS_MV[key]
        xs = [p[0] for _, p in items]
        ys = [p[1] for _, p in items]
        texts = [r for r, _ in items]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(size=9, color=color, opacity=0.78,
                        line=dict(width=1, color="white")),
            name=label,
            text=texts,
            hovertemplate="%{text}<br>PC1=%{x:.2f}, PC2=%{y:.2f}<extra></extra>",
        ))

    # Annotate calibration cases — each annotation gets its own (ax, ay) offset
    # to prevent label collisions in tight cluster regions
    annotations = []
    for run, (label, ax_off, ay_off) in ANNOTATIONS.items():
        if run in runs:
            i = runs.index(run)
            annotations.append(dict(
                x=Xp[i, 0], y=Xp[i, 1],
                text=label,
                showarrow=True, arrowhead=2,
                arrowcolor="rgba(0,0,0,0.45)",
                arrowsize=0.9, arrowwidth=1.2,
                font=dict(size=10),
                ax=ax_off, ay=ay_off,
                bgcolor="rgba(255,255,255,0.92)",
                bordercolor="rgba(0,0,0,0.25)",
                borderwidth=1,
                borderpad=3,
            ))

    fig.update_layout(
        title=(
            f"2D PCA of 5-axis vectors "
            f"(PC1: {var[0]*100:.0f}% var, PC2: {var[1]*100:.0f}% var)"
        ),
        xaxis_title=f"PC1 (mostly the autonomy ↔ fragility axis)",
        yaxis_title=f"PC2 (residual structural variation)",
        plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                   zeroline=True, zerolinecolor="rgba(0,0,0,0.2)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                   zeroline=True, zerolinecolor="rgba(0,0,0,0.2)"),
        annotations=annotations,
        height=650,
        margin=dict(l=80, r=40, t=80, b=80),
        legend=dict(yanchor="top", y=-0.10, xanchor="center", x=0.5, orientation="h"),
    )
    return fig


# ────────────────────────────────────────────────────────────────────────────
# Figure 3: Radar overlay

def fig_radar(vectors: dict[str, list[float]]) -> go.Figure:
    """Radar overlay of 4 (model × variant) means."""
    fig = go.Figure()

    # Compute means per (model, variant)
    groups = {}
    for run, vec in vectors.items():
        key = (model_of(run), variant_of(run))
        groups.setdefault(key, []).append(vec)

    means = {key: [mean([v[i] for v in vecs]) for i in range(5)]
             for key, vecs in groups.items()}

    # Render order: largest polygon first, smallest last.
    # In radial coords with range [-1, +1], larger mean = polygon further from
    # center = visually bigger. Smaller polygons need to be rendered LAST so
    # they're not hidden behind larger ones with semi-transparent fills.
    plot_order = sorted(
        means.keys(),
        key=lambda k: -mean(means[k]),  # descending: biggest polygon first
    )

    for key in plot_order:
        m = means[key]
        # Close the polygon
        r = m + [m[0]]
        theta = AXIS_LABELS_ONELINE + [AXIS_LABELS_ONELINE[0]]
        fig.add_trace(go.Scatterpolar(
            r=r, theta=theta,
            fill="toself",
            fillcolor=hex_to_rgba(COLORS[key], alpha=0.22),
            line=dict(color=COLORS[key], width=3),
            opacity=1.0,
            name=LABELS_MV[key],
            hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
        ))

    fig.update_layout(
        title="Radar overlay: averaged 5-axis vectors per (model × variant)",
        polar=dict(
            radialaxis=dict(
                range=[-1.05, 1.05],
                tickvals=[-1, -0.5, 0, 0.5, 1],
                ticktext=["−1", "−0.5", "0", "+0.5", "+1"],
                gridcolor="rgba(0,0,0,0.15)",
            ),
            angularaxis=dict(direction="clockwise"),
        ),
        height=650,
        margin=dict(l=80, r=80, t=80, b=80),
        legend=dict(yanchor="top", y=-0.05, xanchor="center", x=0.5, orientation="h"),
    )
    return fig


# ────────────────────────────────────────────────────────────────────────────
# Main

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judges", nargs="*", default=DEFAULT_JUDGES,
        help=f"Judge names. Default: {' '.join(DEFAULT_JUDGES)}",
    )
    parser.add_argument(
        "--output-dir", default="analysis/figures",
        help="Directory to write HTML figures into.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[viz_5axis] loading codings from {len(args.judges)} judge(s)...")
    vectors = averaged_vectors(args.judges)
    print(f"[viz_5axis] averaged vectors for {len(vectors)} runs")

    figs = [
        ("parallel_coords", fig_parallel(vectors)),
        ("pca_scatter",     fig_scatter(vectors)),
        ("radar_overlay",   fig_radar(vectors)),
    ]

    for name, fig in figs:
        out_path = out_dir / f"{name}.html"
        fig.write_html(out_path, include_plotlyjs="cdn")
        print(f"[viz_5axis] wrote {out_path}")


if __name__ == "__main__":
    main()
