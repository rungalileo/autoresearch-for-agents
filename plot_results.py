#!/usr/bin/env python3
"""
plot_results.py — Plot autoresearch experiment progress from results.tsv

Usage:
    python3 plot_results.py                          # default: experiments/results.tsv → experiments/progress.png
    python3 plot_results.py -i path/to/results.tsv   # custom input
    python3 plot_results.py -o plot.pdf               # custom output
    python3 plot_results.py --metric "lower_is_better" # flip y-axis for loss-style metrics
"""

import argparse
import csv
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


def load_results(tsv_path: str) -> list[dict]:
    """Load experiments from a TSV file."""
    rows = []
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(
                {
                    "experiment": row["experiment"],
                    "score": float(row["overall_score"]),
                    "status": row["status"].strip(),
                    "description": row["description"].strip(),
                }
            )
    return rows


def plot_progress(
    rows: list[dict],
    output_path: str,
    metric_label: str = "Overall Score (higher is better)",
    lower_is_better: bool = False,
):
    """Create the autoresearch progress plot."""

    n = len(rows)
    xs = list(range(n))
    scores = [r["score"] for r in rows]
    statuses = [r["status"] for r in rows]
    descriptions = [r["description"] for r in rows]

    # --- Compute running best ---
    running_best = []
    best_so_far = scores[0]
    for s in scores:
        if lower_is_better:
            best_so_far = min(best_so_far, s)
        else:
            best_so_far = max(best_so_far, s)
        running_best.append(best_so_far)

    # --- Determine kept vs discarded ---
    kept_x, kept_y, kept_desc = [], [], []
    disc_x, disc_y = [], []
    for i, (s, st, d) in enumerate(zip(scores, statuses, descriptions)):
        if st == "keep":
            kept_x.append(i)
            kept_y.append(s)
            kept_desc.append(d)
        else:
            disc_x.append(i)
            disc_y.append(s)

    # --- Figure setup ---
    fig, ax = plt.subplots(figsize=(max(14, n * 0.6), 7))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafafa")

    # Grid
    ax.grid(True, axis="y", color="#e0e0e0", linewidth=0.5, zorder=0)
    ax.grid(True, axis="x", color="#f0f0f0", linewidth=0.3, zorder=0)

    # --- Running best step line ---
    ax.step(
        xs,
        running_best,
        where="post",
        color="#2ecc71",
        linewidth=2.0,
        alpha=0.7,
        label="Running best",
        zorder=2,
    )

    # --- Discarded points ---
    if disc_x:
        ax.scatter(
            disc_x,
            disc_y,
            color="#cccccc",
            s=50,
            alpha=0.6,
            edgecolors="none",
            label="Discarded",
            zorder=3,
        )

    # --- Kept points ---
    if kept_x:
        ax.scatter(
            kept_x,
            kept_y,
            color="#2ecc71",
            s=90,
            edgecolors="white",
            linewidths=1.2,
            label="Kept",
            zorder=4,
        )

    # --- Labels for kept experiments ---
    y_range = max(scores) - min(scores) if max(scores) != min(scores) else 0.1
    label_offset = y_range * 0.03

    # Track label positions to avoid overlap
    placed_labels: list[tuple[float, float]] = []

    for i, (x, y, desc) in enumerate(zip(kept_x, kept_y, kept_desc)):
        # Truncate long descriptions
        label = textwrap.shorten(desc, width=48, placeholder="...")

        # Alternate label placement above/below to reduce overlap
        # Default: below-left
        va = "top"
        y_pos = y - label_offset
        ha = "left"
        x_pos = x + 0.15

        # Check for overlaps with previously placed labels
        for px, py in placed_labels:
            if abs(x_pos - px) < 3 and abs(y_pos - py) < y_range * 0.06:
                # Flip to above
                va = "bottom"
                y_pos = y + label_offset
                break

        placed_labels.append((x_pos, y_pos))

        ax.annotate(
            label,
            xy=(x, y),
            xytext=(x_pos, y_pos),
            fontsize=7.5,
            color="#2e7d32",
            fontstyle="italic",
            ha=ha,
            va=va,
            zorder=5,
        )

    # --- Axis labels and title ---
    n_kept = len(kept_x)
    ax.set_title(
        f"Autoresearch Progress: {n} Experiments, {n_kept} Kept Improvements",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Experiment #", fontsize=11)
    ax.set_ylabel(metric_label, fontsize=11)

    # X ticks
    ax.set_xticks(xs)
    ax.set_xlim(-0.5, n - 0.5)

    # Y axis formatting
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))
    y_min, y_max = min(scores), max(scores)
    y_pad = y_range * 0.15 if y_range > 0 else 0.05
    ax.set_ylim(y_min - y_pad, y_max + y_pad)

    if lower_is_better:
        ax.invert_yaxis()

    # Legend
    ax.legend(loc="upper left" if not lower_is_better else "lower left", fontsize=9, framealpha=0.9)

    # --- Save ---
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    print(f"Plot saved to {output_path}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot autoresearch experiment progress.")
    parser.add_argument(
        "-i", "--input",
        default="experiments/results.tsv",
        help="Path to results.tsv (default: experiments/results.tsv)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output image path (default: <input_dir>/progress.png)",
    )
    parser.add_argument(
        "--metric",
        choices=["higher_is_better", "lower_is_better"],
        default="higher_is_better",
        help="Whether higher or lower scores are better (default: higher_is_better)",
    )
    parser.add_argument(
        "--ylabel",
        default=None,
        help="Custom Y-axis label (default: auto from --metric)",
    )
    args = parser.parse_args()

    if args.output is None:
        args.output = str(Path(args.input).parent / "progress.png")

    lower_is_better = args.metric == "lower_is_better"
    ylabel = args.ylabel or (
        "Overall Score (higher is better)" if not lower_is_better else "Score (lower is better)"
    )

    rows = load_results(args.input)
    if not rows:
        print("No experiments found in TSV.")
        return

    plot_progress(rows, args.output, metric_label=ylabel, lower_is_better=lower_is_better)


if __name__ == "__main__":
    main()
