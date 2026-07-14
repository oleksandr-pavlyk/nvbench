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

ASSETS = ROOT / "assets"
SUMMARY_COLOR = "#f3f3f3"
BULK_COLOR = "#dedede"
UNKNOWN_COLOR = "#eeeeee"
FAST_SLOW_COLOR = "#dff0d8"
SAME_COLOR = "#d9edf7"
AMBG_COLOR = "#f7f7f7"
EDGE_COLOR = "#333333"
TEXT_GRAY = "#6f7175"


def draw_box(
    ax: plt.Axes,
    *,
    key: str,
    nodes: dict[str, tuple[float, float, str]],
    color: str,
    width: float = 0.15,
    fontsize: int = 10,
) -> None:
    x, y, label = nodes[key]
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=fontsize,
        bbox={
            "boxstyle": f"round,pad={width}",
            "facecolor": color,
            "edgecolor": "#222222",
            "linewidth": 1.1,
        },
    )


def draw_arrow(
    ax: plt.Axes,
    *,
    nodes: dict[str, tuple[float, float, str]],
    src: str,
    dst: str,
    label: str = "",
    label_fraction: float = 0.5,
    label_x_offset: float = 0.0,
    label_y_offset: float = 0.025,
) -> None:
    x0, y0, _ = nodes[src]
    x1, y1, _ = nodes[dst]
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops={
            "arrowstyle": "->",
            "color": EDGE_COLOR,
            "lw": 1.15,
            "shrinkA": 34,
            "shrinkB": 34,
        },
    )
    if label:
        ax.text(
            x0 + (x1 - x0) * label_fraction + label_x_offset,
            y0 + (y1 - y0) * label_fraction + label_y_offset,
            label,
            fontsize=9,
            color=TEXT_GRAY,
            ha="center",
            va="center",
        )


def draw_legend(ax: plt.Axes) -> None:
    for y, label, color in [
        (0.25, "summary checks", SUMMARY_COLOR),
        (0.19, "bulk-data checks", BULK_COLOR),
    ]:
        ax.text(
            0.02,
            y,
            label,
            transform=ax.transAxes,
            fontsize=9,
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": color,
                "edgecolor": "#777777",
            },
        )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12.8, 7.0))
    ax.set_axis_off()

    nodes = {
        "usable": (0.10, 0.60, "Timing data\nusable?"),
        "unknown": (0.10, 0.86, "????"),
        "clear_gap": (0.22, 0.60, "Clear timing\ngap?"),
        "bulk_cycles": (0.38, 0.82, "Bulk cycles\navailable?"),
        "bulk_cycle_confirm": (0.58, 0.82, "Bulk cycle gap\nconfirms?"),
        "summary_cycle_confirm": (0.58, 0.67, "Summary cycle gap\nconfirms?"),
        "fast_slow": (0.88, 0.76, "FAST / SLOW"),
        "bulk_samples": (0.38, 0.36, "Bulk samples\navailable?"),
        "bulk_same": (0.58, 0.40, "Bulk coverage\nsupports SAME?"),
        "summary_same": (0.58, 0.24, "Summary SAME\nchecks pass?"),
        "same": (0.88, 0.34, "SAME"),
        "ambg": (0.88, 0.55, "AMBG"),
    }

    for key in ["usable", "clear_gap", "summary_cycle_confirm", "summary_same"]:
        draw_box(ax, key=key, nodes=nodes, color=SUMMARY_COLOR)
    for key in ["bulk_cycles", "bulk_cycle_confirm", "bulk_samples", "bulk_same"]:
        draw_box(ax, key=key, nodes=nodes, color=BULK_COLOR)
    draw_box(ax, key="unknown", nodes=nodes, color=UNKNOWN_COLOR, width=0.22)
    draw_box(ax, key="fast_slow", nodes=nodes, color=FAST_SLOW_COLOR, width=0.22)
    draw_box(ax, key="same", nodes=nodes, color=SAME_COLOR, width=0.22)
    draw_box(ax, key="ambg", nodes=nodes, color=AMBG_COLOR, width=0.22)

    draw_arrow(ax, nodes=nodes, src="usable", dst="unknown", label="no")
    draw_arrow(ax, nodes=nodes, src="usable", dst="clear_gap", label="yes")

    draw_arrow(ax, nodes=nodes, src="clear_gap", dst="bulk_cycles", label="yes")
    draw_arrow(ax, nodes=nodes, src="clear_gap", dst="bulk_samples", label="no")

    draw_arrow(
        ax, nodes=nodes, src="bulk_cycles", dst="bulk_cycle_confirm", label="yes"
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="bulk_cycles",
        dst="summary_cycle_confirm",
        label="no",
        label_fraction=0.42,
        label_x_offset=0.015,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="bulk_cycle_confirm",
        dst="fast_slow",
        label="yes",
        label_fraction=0.45,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="bulk_cycle_confirm",
        dst="ambg",
        label="no",
        label_fraction=0.25,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="summary_cycle_confirm",
        dst="fast_slow",
        label="yes",
        label_fraction=0.25,
        label_y_offset=-0.02,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="summary_cycle_confirm",
        dst="ambg",
        label="no",
        label_fraction=0.25,
        label_y_offset=-0.02,
    )

    draw_arrow(ax, nodes=nodes, src="bulk_samples", dst="bulk_same", label="yes")
    draw_arrow(
        ax,
        nodes=nodes,
        src="bulk_samples",
        dst="summary_same",
        label="no",
        label_fraction=0.45,
        label_y_offset=-0.02,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="bulk_same",
        dst="same",
        label="yes",
        label_fraction=0.25,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="bulk_same",
        dst="ambg",
        label="no",
        label_fraction=0.45,
        label_y_offset=-0.02,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="summary_same",
        dst="same",
        label="yes",
        label_fraction=0.25,
    )
    draw_arrow(
        ax,
        nodes=nodes,
        src="summary_same",
        dst="ambg",
        label="no",
        label_fraction=0.25,
    )

    draw_legend(ax)
    ax.set_title("nvbench-compare decision tree", fontsize=18, weight="bold")
    fig.tight_layout()
    fig.savefig(ASSETS / "decision-tree-v2.svg", transparent=True)
    plt.close(fig)
    print(f"Wrote {ASSETS / 'decision-tree-v2.svg'}")


if __name__ == "__main__":
    main()
