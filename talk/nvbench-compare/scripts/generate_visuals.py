#!/usr/bin/env python
#
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ASSETS = ROOT / "assets"
NV_GREEN = "#76b900"
NV_BLUE = "#1f77b4"
NV_YELLOW = "#d9a400"
NV_RED = "#d62728"
NV_GRAY = "#6f7175"
NV_ORANGE = "#ff9f1c"
NV_LIGHT_GRAY = "#f5f6f7"


def save_summary_tag_examples() -> None:
    groups = [
        (
            "GPU time",
            "nv/cold/time/gpu/*",
            ["mean", "stdev/*", "min", "max", "median", "iqr/*"],
            NV_GREEN,
        ),
        (
            "CPU time",
            "nv/cold/time/cpu/*",
            ["mean", "stdev/*", "min", "max", "median", "iqr/*"],
            NV_BLUE,
        ),
        (
            "Throughput",
            "nv/cold/bw/*",
            ["global/rate", "global/utilization"],
            NV_RED,
        ),
        (
            "Cold run",
            "nv/cold/*",
            ["sample_size", "walltime", "sm_clock_rate/mean"],
            NV_ORANGE,
        ),
        (
            "Batch run",
            "nv/batch/*",
            ["sample_size", "time/gpu/mean", "walltime"],
            NV_YELLOW,
        ),
        (
            "Bulk sidecars",
            "nv/json/*",
            ["bin:sample_times", "freqs-bin:sample_freqs"],
            "#9467bd",
        ),
        (
            "User summaries",
            "...",
            ["*"],
            NV_GRAY,
        ),
    ]

    fig, ax = plt.subplots(figsize=(12, 5.0))
    ax.set_axis_off()
    ax.set_title(
        "A state contains many tagged summaries", fontsize=18, weight="bold", pad=12
    )

    left = 0.04
    widths = [0.22, 0.30, 0.38]
    top = 0.85
    row_h = 0.095
    headers = ["Group", "Tag family", "Examples"]

    x = left
    for width, header in zip(widths, headers, strict=True):
        ax.add_patch(
            plt.Rectangle(
                (x, top),
                width,
                row_h,
                transform=ax.transAxes,
                facecolor="#e7e8e9",
                edgecolor="#ffffff",
            )
        )
        ax.text(
            x + 0.012,
            top + row_h / 2,
            header,
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=12,
            weight="bold",
        )
        x += width

    for row, (name, tag_family, examples, color) in enumerate(groups):
        y = top - (row + 1) * row_h
        ax.add_patch(
            plt.Rectangle(
                (left, y),
                sum(widths),
                row_h,
                transform=ax.transAxes,
                facecolor="#ffffff" if row % 2 == 0 else NV_LIGHT_GRAY,
                edgecolor="#ffffff",
            )
        )
        ax.add_patch(
            plt.Rectangle(
                (left, y),
                0.010,
                row_h,
                transform=ax.transAxes,
                facecolor=color,
                edgecolor=color,
            )
        )

        values = [name, tag_family, ", ".join(examples)]
        x = left
        for width, value in zip(widths, values, strict=True):
            ax.text(
                x + 0.018,
                y + row_h / 2,
                value,
                transform=ax.transAxes,
                ha="left",
                va="center",
                fontsize=11,
                family="monospace" if "/" in value or "*" in value else "sans-serif",
                color="#111111",
            )
            x += width

    ax.text(
        left,
        0.04,
        "Inspect a real file: jq '.benchmarks[0] | .states[0] | .summaries[] | .tag' result.json",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=11,
        family="monospace",
        color=NV_GRAY,
    )

    fig.tight_layout()
    fig.savefig(ASSETS / "summary-tag-examples.svg", transparent=True)
    plt.close(fig)


def nearest_coverage(
    source: np.ndarray, target: np.ndarray, tolerance: float
) -> np.ndarray:
    distances = np.abs(np.log(source[:, None]) - np.log(target[None, :]))
    return distances.min(axis=1) <= tolerance


def draw_tolerance_cone(
    ax: plt.Axes,
    *,
    x: float,
    y_apex: float,
    y_base: float,
    tolerance: float,
    color: str,
) -> None:
    levels = 12
    for i in range(levels):
        top_fraction = i / levels
        bottom_fraction = (i + 1) / levels

        y_top = y_apex + (y_base - y_apex) * top_fraction
        y_bottom = y_apex + (y_base - y_apex) * bottom_fraction

        left_top = x * np.exp(-tolerance * top_fraction)
        right_top = x * np.exp(tolerance * top_fraction)
        left_bottom = x * np.exp(-tolerance * bottom_fraction)
        right_bottom = x * np.exp(tolerance * bottom_fraction)

        ax.fill(
            [left_top, right_top, right_bottom, left_bottom],
            [y_top, y_top, y_bottom, y_bottom],
            color=color,
            alpha=0.18 * (1.0 - top_fraction),
            linewidth=0,
            zorder=1,
        )


def save_decision_tree() -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_axis_off()

    nodes = {
        "input": (0.08, 0.78, "Matched state pair"),
        "valid": (0.33, 0.78, "Timing data usable?"),
        "gap": (0.58, 0.78, "Clear summary gap?"),
        "same": (0.58, 0.48, "Centers close +\ninterval overlap?"),
        "bulk": (0.33, 0.48, "Bulk data available?"),
        "coverage": (0.33, 0.20, "Coverage supports\nsame?"),
        "unknown": (0.83, 0.88, "????"),
        "fastslow": (0.83, 0.70, "FAST / SLOW"),
        "same_status": (0.83, 0.48, "SAME"),
        "ambg": (0.83, 0.20, "AMBG"),
    }

    def box(key: str, color: str = "#f2f2f2") -> None:
        x, y, label = nodes[key]
        ax.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=12,
            bbox={
                "boxstyle": "round,pad=0.45",
                "facecolor": color,
                "edgecolor": "#222222",
                "linewidth": 1.1,
            },
        )

    # summary_check_color = "#f2f2f2"
    # bulk_check_color = "#dedede"

    summary_check_color = "#f2f2f2"
    bulk_check_color = "#dfe8d8"

    box("input", summary_check_color)
    for key in ["valid", "gap", "same"]:
        box(key, summary_check_color)
    for key in ["bulk", "coverage"]:
        box(key, bulk_check_color)
    box("unknown", "#eeeeee")
    box("fastslow", "#dff0d8")
    box("same_status", "#d9edf7")
    box("ambg", "#f7f7f7")

    def arrow(
        src: str,
        dst: str,
        label: str = "",
        label_fraction: float = 0.5,
        label_x_offset: float = 0.0,
        label_y_offset: float = 0.035,
    ) -> None:
        x0, y0, _ = nodes[src]
        x1, y1, _ = nodes[dst]
        ax.annotate(
            "",
            xy=(x1 - 0.08 if x1 > x0 else x1 + 0.08, y1),
            xytext=(x0 + 0.08 if x1 > x0 else x0 - 0.08, y0),
            arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 1.2},
        )
        if label:
            ax.text(
                x0 + (x1 - x0) * label_fraction + label_x_offset,
                y0 + (y1 - y0) * label_fraction + label_y_offset,
                label,
                fontsize=9,
                color=NV_GRAY,
            )

    arrow("input", "valid")
    arrow("valid", "gap", "yes", label_y_offset=-0.055)
    arrow("valid", "unknown", "no")
    arrow("gap", "fastslow", "yes")
    arrow("gap", "same", "no")
    arrow("same", "same_status", "yes")
    arrow("same", "bulk", "no")
    arrow("bulk", "coverage", "yes")
    arrow(
        "bulk",
        "ambg",
        "no",
        label_fraction=0.65,
        label_x_offset=-0.015,
        label_y_offset=0.015,
    )
    arrow("coverage", "same_status", "yes", label_fraction=0.35)
    arrow("coverage", "ambg", "no")

    ax.text(
        0.02,
        0.24,
        "summary checks",
        transform=ax.transAxes,
        fontsize=9,
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": summary_check_color,
            "edgecolor": "#777777",
        },
    )
    ax.text(
        0.02,
        0.18,
        "bulk-data checks",
        transform=ax.transAxes,
        fontsize=9,
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": bulk_check_color,
            "edgecolor": "#777777",
        },
    )

    ax.set_title("nvbench-compare decision tree", fontsize=18, weight="bold")
    fig.tight_layout()
    fig.savefig(ASSETS / "decision-tree.svg", transparent=True)
    plt.close(fig)


def save_timing_only_bulk_decision_tree() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.set_axis_off()

    summary_check_color = "#f2f2f2"
    bulk_check_color = "#dfe8d8"
    status_color = "#f7f7f7"

    nodes = {
        "condition": (
            0.11,
            0.78,
            "Bulk times present\nbulk frequencies absent",
            bulk_check_color,
        ),
        "gap": (0.33, 0.78, "Clear timing\ngap?", summary_check_color),
        "gap_confirm": (
            0.58,
            0.78,
            "SM-clock cycle\nconfirmation?",
            summary_check_color,
        ),
        "fastslow": (0.86, 0.86, "FAST / SLOW", "#dff0d8"),
        "same_geometry": (
            0.33,
            0.48,
            "Summary SAME\ngeometry?",
            summary_check_color,
        ),
        "coverage": (
            0.58,
            0.48,
            "Timing coverage\nsupports SAME?",
            bulk_check_color,
        ),
        "same_confirm": (
            0.58,
            0.20,
            "SM-clock SAME\ncheck if available",
            summary_check_color,
        ),
        "same": (0.86, 0.48, "SAME", "#d9edf7"),
        "ambg": (0.86, 0.14, "AMBG", status_color),
    }

    def box(key: str) -> None:
        x, y, label, color = nodes[key]
        ax.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=10.5,
            bbox={
                "boxstyle": "round,pad=0.42",
                "facecolor": color,
                "edgecolor": "#222222",
                "linewidth": 1.1,
            },
        )

    def arrow(
        src: str,
        dst: str,
        label: str = "",
        *,
        label_fraction: float = 0.5,
        label_x_offset: float = 0.0,
        label_y_offset: float = 0.032,
    ) -> None:
        x0, y0, _, _ = nodes[src]
        x1, y1, _, _ = nodes[dst]
        dx = x1 - x0
        dy = y1 - y0
        length = np.hypot(dx, dy)
        if length == 0:
            return
        ux = dx / length
        uy = dy / length
        ax.annotate(
            "",
            xy=(x1 - ux * 0.075, y1 - uy * 0.075),
            xytext=(x0 + ux * 0.075, y0 + uy * 0.075),
            arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 1.2},
        )
        if label:
            ax.text(
                x0 + dx * label_fraction + label_x_offset,
                y0 + dy * label_fraction + label_y_offset,
                label,
                fontsize=8.7,
                color=NV_GRAY,
                ha="center",
                va="center",
            )

    for key in nodes:
        box(key)

    arrow("condition", "gap")
    arrow("gap", "gap_confirm", "yes")
    arrow("gap_confirm", "fastslow", "pass")
    arrow("gap_confirm", "ambg", "fail / unavailable", label_fraction=0.44)
    arrow("gap", "same_geometry", "no", label_x_offset=-0.03)
    arrow("same_geometry", "coverage", "yes")
    arrow("same_geometry", "ambg", "no", label_fraction=0.72)
    arrow("coverage", "same_confirm", "yes", label_x_offset=-0.03)
    arrow("coverage", "ambg", "no", label_fraction=0.62)
    arrow("same_confirm", "same", "pass / unavailable", label_fraction=0.45)
    arrow("same_confirm", "ambg", "fail", label_fraction=0.50)

    ax.text(
        0.50,
        0.02,
        "Timing-only bulk data can rescue SAME, but cannot by itself confirm FAST/SLOW.",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=10.5,
        color=NV_GRAY,
    )

    ax.set_title("Timing-only bulk-data path", fontsize=18, weight="bold")
    fig.tight_layout()
    fig.savefig(ASSETS / "decision-tree-timing-only.svg", transparent=True)
    plt.close(fig)


def save_coverage_metric() -> None:
    ref = np.array([99.2, 99.4, 99.4, 99.8, 100.0, 100.0, 100.0, 100.3, 102.5])
    cmp = np.array([99.3, 99.5, 99.8, 100.0, 100.2, 100.4, 100.4, 100.8])
    tolerance = np.log1p(0.004)
    ref_covered = nearest_coverage(ref, cmp, tolerance)

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.set_title("ref \u2192 cmp coverage within a relative tolerance", fontsize=16)
    ax.set_xlabel("Timing, arbitrary units")
    ax.set_yticks([1, 0])
    ax.set_yticklabels(["reference", "compare"])
    ax.set_ylim(-0.55, 1.55)

    for value, covered in zip(ref, ref_covered, strict=True):
        draw_tolerance_cone(
            ax,
            x=value,
            y_apex=0.95,
            y_base=0.16,
            tolerance=tolerance,
            color=NV_BLUE if covered else NV_RED,
        )
        ax.scatter(value, 1, s=80, color=NV_BLUE if covered else NV_RED, zorder=3)

    ax.scatter(cmp, np.zeros_like(cmp), s=80, marker="s", color=NV_GREEN, zorder=3)

    ax.text(
        0.02,
        0.08,
        "A reference point is covered if its cone reaches at least one compare point.",
        transform=ax.transAxes,
        fontsize=11,
        color=NV_GRAY,
    )
    ax.grid(axis="x", color="#dddddd", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(ASSETS / "coverage-metric.svg", transparent=True)
    plt.close(fig)


def save_directional_coverage() -> None:
    cases = [
        (
            "both high",
            "evidence for SAME",
            np.array([99.0, 99.4, 99.8, 100.2, 100.6, 101.0]),
            np.array([99.1, 99.5, 99.9, 100.3, 100.7]),
            ("high", "high"),
            NV_GREEN,
        ),
        (
            "one high, one low",
            "support containment",
            np.array([98.0, 98.8, 99.6, 100.4, 101.2, 102.0]),
            np.array([99.6, 100.0, 100.4]),
            ("low", "high"),
            NV_ORANGE,
        ),
        (
            "both low",
            "weak SAME evidence",
            np.array([98.0, 98.4, 98.8, 99.2]),
            np.array([100.6, 101.0, 101.4, 101.8]),
            ("low", "low"),
            NV_RED,
        ),
    ]
    tolerance = np.log1p(0.004)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.85), sharey=True)
    for ax, (title, subtitle, ref, cmp, coverages, color) in zip(
        axes, cases, strict=True
    ):
        ref_covered = nearest_coverage(ref, cmp, tolerance)
        cmp_covered = nearest_coverage(cmp, ref, tolerance)

        for value, covered in zip(ref, ref_covered, strict=True):
            ax.scatter(
                value,
                1,
                s=70,
                color=NV_BLUE if covered else "#b8b8b8",
                edgecolor="#333333" if not covered else NV_BLUE,
                zorder=3,
            )
        for value, covered in zip(cmp, cmp_covered, strict=True):
            ax.scatter(
                value,
                0,
                s=70,
                marker="s",
                color=NV_GREEN if covered else "#b8b8b8",
                edgecolor="#333333" if not covered else NV_GREEN,
                zorder=3,
            )

        ax.set_title(title, fontsize=13, fontweight="bold", color=color, pad=16)
        ax.text(
            0.5,
            1.02,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=9,
            color=NV_GRAY,
        )
        ax.text(
            0.5,
            -0.22,
            f"ref→cmp: {coverages[0]}    cmp→ref: {coverages[1]}",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            family="monospace",
            color="#111111",
        )
        ax.set_xlim(97.6, 102.4)
        ax.set_ylim(-0.45, 1.45)
        ax.set_yticks([1, 0])
        ax.set_yticklabels(["ref", "cmp"] if ax is axes[0] else [])
        ax.tick_params(axis="x", labelbottom=False)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.grid(axis="x", color="#e4e4e4", linewidth=0.8)

    fig.suptitle(
        "Coverage must pass in both directions", fontsize=17, fontweight="bold"
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.90), w_pad=1.8)
    fig.savefig(ASSETS / "directional-coverage.svg", transparent=True)
    plt.close(fig)


def save_summary_output_example() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.set_axis_off()

    ax.text(
        0.03,
        0.92,
        "# Summary",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=18,
        fontweight="bold",
        family="monospace",
    )

    lines = [
        ("- Total Matches: 14", "#111111", None, None),
        ("  - Unchanged   (classified as SAME): 1", NV_BLUE, "SAME rows", None),
        (
            "  - Improvement (clear timing gap, %Diff < 0): 9",
            NV_GREEN,
            "FAST rows",
            None,
        ),
        ("  - Regression  (clear timing gap, %Diff > 0): 0", NV_RED, "SLOW rows", None),
        (
            "  - Ambiguous   (comparison requires more evidence): 4",
            NV_ORANGE,
            "AMBG rows",
            None,
        ),
        ("    - Reasons:", "#111111", None, None),
        ("      - bt-sup-miss: 2", NV_ORANGE, "grouped reason", " ("),
        ("          sample: min(ref=100.0%, cmp=14.3%) >= 97.0%;", NV_GRAY, None, None),
        (
            "          support: min(ref=100.0%, cmp=20.0%) >= 80.0%)",
            NV_GRAY,
            "worst severity case",
            None,
        ),
        ("      - bc-gap-miss: 2", NV_ORANGE, "grouped reason", None),
        (
            "          clear timing gap was not confirmed by bulk cycles",
            NV_GRAY,
            "explanation",
            None,
        ),
        (
            "  - Unknown     (timing data unavailable or unusable): 0",
            NV_YELLOW,
            "???? rows",
            None,
        ),
    ]

    y = 0.82
    dy = 0.061
    for text, color, label, suffix in lines:
        rendered = ax.text(
            0.04,
            y,
            text,
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=12,
            family="monospace",
            color=color,
        )
        if suffix is not None:
            fig.canvas.draw()
            bbox = rendered.get_window_extent(renderer=fig.canvas.get_renderer())
            suffix_x = ax.transAxes.inverted().transform((bbox.x1, bbox.y0))[0] + 0.002
            ax.text(
                suffix_x,
                y,
                suffix,
                transform=ax.transAxes,
                ha="left",
                va="center",
                fontsize=12,
                family="monospace",
                color=NV_GRAY,
            )
        if label is not None:
            ax.text(
                0.78,
                y,
                label,
                transform=ax.transAxes,
                ha="left",
                va="center",
                fontsize=10,
                color=color,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": "#ffffff",
                    "edgecolor": color,
                    "linewidth": 1.0,
                },
            )
        y -= dy

    ax.text(
        0.55,
        0.055,
        "Reason details show a representative worst case, not every row.",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=12,
        color=NV_GRAY,
    )

    fig.tight_layout()
    fig.savefig(ASSETS / "summary-output-example.svg", transparent=True)
    plt.close(fig)


def save_explain_output_example() -> None:
    headers = [
        "T",
        "Ref [Lo | Ce | Hi]",
        "Cmp [Lo | Ce | Hi]",
        "Ref Noise",
        "Cmp Noise",
        "Reason",
        "Change",
        "Status",
    ]
    rows = [
        [
            "U8",
            "[19.380 | 19.944 | 20.508] us",
            "[18.400 | 18.736 | 19.464] us",
            "2.83%",
            "3.89%",
            "bulk-same",
            "",
            "SAME",
        ],
        [
            "F32",
            "[51.712 | 52.190 | 52.667] us",
            "[47.176 | 47.714 | 48.252] us",
            "0.91%",
            "1.13%",
            "bc-gap",
            "<= -8.6%",
            "FAST",
        ],
        [
            "I16",
            "[30.400 | 31.267 | 31.776] us",
            "[28.737 | 29.693 | 30.649] us",
            "2.77%",
            "3.22%",
            "bt-sup-miss",
            "",
            "AMBG",
        ],
    ]
    widths = [0.050, 0.238, 0.238, 0.088, 0.088, 0.112, 0.075, 0.105]
    status_colors = {
        "SAME": NV_BLUE,
        "FAST": NV_GREEN,
        "SLOW": NV_RED,
        "AMBG": NV_GRAY,
        "????": NV_YELLOW,
    }

    fig, ax = plt.subplots(figsize=(12, 3.55))
    ax.set_axis_off()
    left = 0.025
    top = 0.78
    row_h = 0.16

    x = left
    for header, width in zip(headers, widths, strict=True):
        ax.add_patch(
            plt.Rectangle(
                (x, top),
                width,
                row_h,
                transform=ax.transAxes,
                facecolor="#e7e8e9",
                edgecolor="#ffffff",
            )
        )
        ax.text(
            x + width / 2,
            top + row_h / 2,
            header,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=8.8,
            fontweight="bold",
        )
        x += width

    for row_index, row in enumerate(rows):
        y = top - (row_index + 1) * row_h
        x = left
        facecolor = "#ffffff" if row_index % 2 == 0 else NV_LIGHT_GRAY
        for value, width, header in zip(row, widths, headers, strict=True):
            ax.add_patch(
                plt.Rectangle(
                    (x, y),
                    width,
                    row_h,
                    transform=ax.transAxes,
                    facecolor=facecolor,
                    edgecolor="#ffffff",
                )
            )
            color = status_colors.get(value, "#111111")
            fontweight = "bold" if header == "Status" else "normal"
            ax.text(
                x + width / 2,
                y + row_h / 2,
                value,
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=8.5,
                family="monospace",
                color=color,
                fontweight=fontweight,
            )
            x += width

    ax.text(
        left,
        0.13,
        "Reason codes identify the check; summary output includes a legend.",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=11,
        color=NV_GRAY,
    )

    fig.tight_layout()
    fig.savefig(ASSETS / "explain-output-example.svg", transparent=True)
    plt.close(fig)


def save_sample_vs_support() -> None:
    values = np.array([10.0, 10.1, 10.2, 10.3, 12.0])
    ref_counts = np.array([45, 35, 15, 4, 1])
    cmp_counts = np.array([42, 32, 18, 7, 1])
    x = np.arange(len(values))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar(x - width / 2, ref_counts, width, label="reference", color=NV_BLUE)
    ax.bar(x + width / 2, cmp_counts, width, label="compare", color=NV_GREEN)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v:g}" for v in values])
    ax.set_xlabel("Unique timing value")
    ax.set_ylabel("Sample count")
    ax.set_title(
        "Sample-weight coverage and unique-support coverage ask different questions"
    )
    ax.legend(frameon=False)
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.annotate(
        "rare support value",
        xy=(4, 1),
        xytext=(3.1, 18),
        arrowprops={"arrowstyle": "->", "color": NV_YELLOW},
        color="#664d00",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(ASSETS / "sample-vs-support.svg", transparent=True)
    plt.close(fig)


def draw_timing_interval(
    ax: plt.Axes,
    *,
    low: float,
    center: float,
    high: float,
    y: float,
    color: str,
    label: str,
) -> None:
    ax.hlines(y, low, high, color=color, linewidth=4, zorder=2)
    ax.vlines([low, high], y - 0.055, y + 0.055, color=color, linewidth=2, zorder=3)
    ax.vlines(center, y - 0.09, y + 0.09, color=color, linewidth=3, zorder=3)
    ax.text(
        0.02,
        y,
        label,
        transform=ax.get_yaxis_transform(),
        ha="left",
        va="center",
        fontsize=10,
    )


def shade_interval_gap(
    ax: plt.Axes,
    *,
    left: float,
    right: float,
    label: str,
    color: str,
) -> None:
    ax.axvspan(left, right, ymin=0.30, ymax=0.70, color=color, alpha=0.18, zorder=0)
    ax.annotate(
        label,
        xy=((left + right) / 2, 0.50),
        xytext=((left + right) / 2, 0.88),
        ha="center",
        fontsize=8,
        color=color,
        arrowprops={"arrowstyle": "->", "color": color, "lw": 1.0},
    )


def shade_interval_overlap(
    ax: plt.Axes, *, left: float, right: float, label: str
) -> None:
    ax.axvspan(left, right, ymin=0.28, ymax=0.72, color=NV_YELLOW, alpha=0.18, zorder=0)
    ax.text(
        (left + right) / 2,
        0.50,
        label,
        ha="center",
        va="center",
        fontsize=8,
        color="#664d00",
    )


def save_timing_interval_cases() -> None:
    cases = [
        (
            "well separated",
            "FAST/SLOW evidence",
            (1.0, 1.35, 1.75),
            (3.15, 3.45, 4.05),
            "clear-gap",
        ),
        (
            "same",
            "centers close + strong overlap",
            (1.25, 1.85, 2.85),
            (1.60, 1.95, 2.35),
            "strong-overlap",
        ),
        (
            "slightly separated",
            "gap exists, but not enough",
            (1.0, 1.35, 2.0),
            (2.10, 2.65, 3.25),
            "small-gap",
        ),
        (
            "weak overlap",
            "centers close, overlap weak",
            (1.0, 1.98, 2.05),
            (1.75, 2.02, 3.35),
            "weak-overlap",
        ),
        (
            "nested",
            "centers are not close",
            (1.0, 1.75, 4.05),
            (2.75, 3.20, 3.45),
            "",
        ),
        (
            "too wide",
            "close centers, too much uncertainty",
            (1.75, 2.0, 2.25),
            (0.75, 2.05, 4.55),
            "",
        ),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(12, 5.9), sharex=True)
    ref_y = 0.62
    cmp_y = 0.38
    for ax, (title, subtitle, ref_interval, cmp_interval, aid) in zip(
        axes.flat, cases, strict=True
    ):
        if aid == "clear-gap":
            shade_interval_gap(
                ax,
                left=ref_interval[2],
                right=cmp_interval[0],
                label="large gap",
                color=NV_GREEN,
            )
        elif aid == "small-gap":
            shade_interval_gap(
                ax,
                left=ref_interval[2],
                right=cmp_interval[0],
                label="small gap",
                color=NV_ORANGE,
            )
        elif aid == "strong-overlap":
            shade_interval_overlap(
                ax,
                left=max(ref_interval[0], cmp_interval[0]),
                right=min(ref_interval[2], cmp_interval[2]),
                label="strong overlap",
            )
        elif aid == "weak-overlap":
            shade_interval_overlap(
                ax,
                left=max(ref_interval[0], cmp_interval[0]),
                right=min(ref_interval[2], cmp_interval[2]),
                label="weak",
            )

        draw_timing_interval(
            ax,
            low=ref_interval[0],
            center=ref_interval[1],
            high=ref_interval[2],
            y=ref_y,
            color=NV_BLUE,
            label="ref",
        )
        draw_timing_interval(
            ax,
            low=cmp_interval[0],
            center=cmp_interval[1],
            high=cmp_interval[2],
            y=cmp_y,
            color=NV_GREEN,
            label="cmp",
        )
        ax.set_title(title, fontsize=13, fontweight="bold", pad=16)
        ax.text(
            0.5,
            1.02,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            color=NV_GRAY,
            fontsize=9,
        )
        ax.set_ylim(0.12, 0.96)
        ax.set_xlim(0.5, 4.7)
        ax.set_yticks([])
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="x", labelbottom=False)
        ax.grid(axis="x", color="#e4e4e4", linewidth=0.8)

    fig.suptitle(
        "Timing intervals: decide only when the geometry is informative",
        fontsize=17,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94), h_pad=2.0, w_pad=1.4)
    fig.savefig(ASSETS / "timing-interval-cases.svg", transparent=True)
    plt.close(fig)


def save_clear_gap_criterion() -> None:
    def draw_case(
        ax: plt.Axes,
        *,
        title: str,
        subtitle: str,
        cmp_interval: tuple[float, float, float],
        ref_interval: tuple[float, float, float],
        required_right: float,
        decision_color: str,
    ) -> None:
        cmp_hi = cmp_interval[2]
        ref_lo = ref_interval[0]
        ref_y = 0.64
        cmp_y = 0.36

        ax.axvspan(
            cmp_hi,
            required_right,
            ymin=0.19,
            ymax=0.81,
            color=NV_YELLOW,
            alpha=0.22,
            zorder=0,
        )
        ax.axvspan(
            cmp_hi,
            ref_lo,
            ymin=0.30,
            ymax=0.70,
            color=decision_color,
            alpha=0.18,
            zorder=0,
        )
        ax.axvline(cmp_hi, color="#444444", linestyle=":", linewidth=1.2)
        ax.axvline(required_right, color=NV_YELLOW, linestyle="--", linewidth=1.6)

        draw_timing_interval(
            ax,
            low=ref_interval[0],
            center=ref_interval[1],
            high=ref_interval[2],
            y=ref_y,
            color=NV_BLUE,
            label="ref",
        )
        draw_timing_interval(
            ax,
            low=cmp_interval[0],
            center=cmp_interval[1],
            high=cmp_interval[2],
            y=cmp_y,
            color=NV_GREEN,
            label="cmp",
        )

        ax.annotate(
            "actual gap",
            xy=((cmp_hi + ref_lo) / 2, 0.50),
            xytext=((cmp_hi + ref_lo) / 2, 0.88),
            ha="center",
            fontsize=10,
            color=decision_color,
            arrowprops={"arrowstyle": "->", "color": decision_color, "lw": 1.0},
        )
        ax.text(
            (cmp_hi + required_right) / 2,
            0.08,
            "required gap",
            ha="center",
            va="center",
            fontsize=10,
            color="#664d00",
        )

        ax.set_title(
            title, fontsize=15, fontweight="bold", color=decision_color, pad=24
        )
        ax.text(
            0.5,
            1.01,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=10,
            color=NV_GRAY,
        )
        ax.set_xlim(0.9, 4.25)
        ax.set_ylim(0.05, 0.98)
        ax.set_yticks([])
        ax.tick_params(axis="x", labelbottom=False)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.grid(axis="x", color="#e4e4e4", linewidth=0.8)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.25), sharex=True, sharey=True)
    draw_case(
        axes[0],
        title="FAST",
        subtitle="compare interval is left, and the gap clears the threshold",
        cmp_interval=(1.15, 1.55, 2.00),
        ref_interval=(2.55, 3.05, 3.75),
        required_right=2.28,
        decision_color=NV_GREEN,
    )
    draw_case(
        axes[1],
        title="AMBG",
        subtitle="intervals are disjoint, but the gap is too small",
        cmp_interval=(1.15, 1.55, 2.00),
        ref_interval=(2.13, 2.75, 3.35),
        required_right=2.28,
        decision_color=NV_ORANGE,
    )

    fig.suptitle(
        "Clear gap compares the closest interval endpoints",
        fontsize=17,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91), w_pad=2.0)
    fig.savefig(ASSETS / "clear-gap-criterion.svg", transparent=True)
    plt.close(fig)


def save_clear_gap_fast_slow() -> None:
    def draw_interval_pair(
        ax: plt.Axes,
        *,
        y: float,
        title: str,
        left_label: str,
        right_label: str,
        left_interval: tuple[float, float, float],
        right_interval: tuple[float, float, float],
        gap_label: str,
        color: str,
    ) -> None:
        ax.text(
            0.02,
            y,
            title,
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=color,
        )
        draw_timing_interval(
            ax,
            low=left_interval[0],
            center=left_interval[1],
            high=left_interval[2],
            y=y,
            color=NV_GREEN if left_label == "cmp" else NV_BLUE,
            label="",
        )
        draw_timing_interval(
            ax,
            low=right_interval[0],
            center=right_interval[1],
            high=right_interval[2],
            y=y,
            color=NV_GREEN if right_label == "cmp" else NV_BLUE,
            label="",
        )
        ax.text(
            left_interval[1],
            y - 0.12,
            left_label,
            ha="center",
            va="center",
            fontsize=10,
            color=NV_GRAY,
        )
        ax.text(
            right_interval[1],
            y - 0.12,
            right_label,
            ha="center",
            va="center",
            fontsize=10,
            color=NV_GRAY,
        )
        gap_left = left_interval[2]
        gap_right = right_interval[0]
        ax.annotate(
            "",
            xy=(gap_right, y + 0.05),
            xytext=(gap_left, y + 0.05),
            arrowprops={"arrowstyle": "<->", "color": color, "lw": 1.4},
        )
        ax.text(
            (gap_left + gap_right) / 2,
            y + 0.12,
            gap_label,
            ha="center",
            va="bottom",
            fontsize=9,
            color=color,
        )

    fig, ax = plt.subplots(figsize=(5.6, 3.25))
    ax.set_axisbelow(True)
    ax.set_title("closest endpoints decide", fontsize=14, fontweight="bold", pad=10)
    draw_interval_pair(
        ax,
        y=0.70,
        title="FAST",
        left_label="cmp",
        right_label="ref",
        left_interval=(1.15, 1.55, 1.95),
        right_interval=(2.55, 2.95, 3.45),
        gap_label="gap >= δ · cmp.upper",
        color=NV_GREEN,
    )
    draw_interval_pair(
        ax,
        y=0.32,
        title="SLOW",
        left_label="ref",
        right_label="cmp",
        left_interval=(1.15, 1.55, 1.95),
        right_interval=(2.55, 2.95, 3.45),
        gap_label="gap >= δ · ref.upper",
        color=NV_RED,
    )
    ax.set_xlim(0.7, 3.75)
    ax.set_ylim(0.08, 0.92)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelbottom=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#e4e4e4", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(ASSETS / "clear-gap-fast-slow.svg", transparent=True)
    plt.close(fig)


def save_min_q3_interval_rationale() -> None:
    rng = np.random.default_rng(7)
    core = 1.0 + rng.gamma(shape=1.8, scale=0.055, size=190)
    tail = 1.0 + rng.gamma(shape=2.0, scale=0.16, size=22)
    outliers = np.array([1.62, 1.72, 1.84, 1.95])
    samples = np.sort(np.concatenate([core, tail, outliers]))

    minimum = float(np.min(samples))
    q1, median, q3 = np.quantile(samples, [0.25, 0.50, 0.75], method="nearest")
    maximum = float(np.max(samples))

    fig, (ax_hist, ax_intervals) = plt.subplots(
        2,
        1,
        figsize=(11.5, 5.8),
        gridspec_kw={"height_ratios": [2.1, 1.2]},
        sharex=True,
    )

    bins = np.linspace(minimum - 0.02, maximum + 0.03, 38)
    ax_hist.hist(samples, bins=bins, color=NV_BLUE, alpha=0.45, edgecolor="white")
    ax_hist.scatter(
        samples,
        np.full_like(samples, -2.0),
        marker="|",
        color="#222222",
        alpha=0.35,
        s=80,
        clip_on=False,
    )
    for value, label, color in [
        (minimum, "min", NV_GREEN),
        (median, "median", NV_BLUE),
        (q3, "q3", NV_YELLOW),
        (maximum, "max", NV_RED),
    ]:
        ax_hist.axvline(value, color=color, linewidth=2)
        ax_hist.text(
            value,
            ax_hist.get_ylim()[1] * 0.92,
            label,
            rotation=90,
            ha="right",
            va="top",
            fontsize=9,
            color=color,
        )
    ax_hist.set_title(
        "Timing samples often have a fast lower edge and a slow right tail",
        fontsize=15,
        fontweight="bold",
    )
    ax_hist.set_yticks([])
    ax_hist.spines[["top", "right", "left"]].set_visible(False)
    ax_hist.grid(axis="x", color="#e4e4e4", linewidth=0.8)

    interval_rows = [
        ("[q1, q3]", q1, q3, "drops the fast edge", NV_ORANGE),
        ("[min, q3]", minimum, q3, "used by compare", NV_GREEN),
        ("[min, max]", minimum, maximum, "stretches to outliers", NV_RED),
    ]
    y_positions = [2, 1, 0]
    ax_intervals.set_ylim(-0.6, 2.6)
    for y, (name, low, high, note, color) in zip(
        y_positions, interval_rows, strict=True
    ):
        ax_intervals.hlines(y, low, high, color=color, linewidth=7, alpha=0.8)
        ax_intervals.vlines([low, high], y - 0.17, y + 0.17, color=color, linewidth=2)
        ax_intervals.text(
            minimum - 0.12,
            y,
            name,
            ha="right",
            va="center",
            fontsize=11,
            fontweight="bold" if name == "[min, q3]" else "normal",
            color="#111111",
        )
        ax_intervals.text(
            high + 0.03,
            y,
            note,
            ha="left",
            va="center",
            fontsize=10,
            color=NV_GRAY,
        )

    ax_intervals.set_yticks([])
    ax_intervals.set_xlabel("time")
    ax_intervals.spines[["top", "right", "left"]].set_visible(False)
    ax_intervals.grid(axis="x", color="#e4e4e4", linewidth=0.8)

    fig.tight_layout(h_pad=0.4)
    fig.savefig(ASSETS / "min-q3-interval-rationale.svg", transparent=True)
    plt.close(fig)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    save_summary_tag_examples()
    save_decision_tree()
    save_timing_only_bulk_decision_tree()
    save_coverage_metric()
    save_directional_coverage()
    save_summary_output_example()
    save_explain_output_example()
    save_sample_vs_support()
    save_timing_interval_cases()
    save_clear_gap_criterion()
    save_clear_gap_fast_slow()
    save_min_q3_interval_rationale()
    print(f"Wrote visuals to {ASSETS}")


if __name__ == "__main__":
    main()
