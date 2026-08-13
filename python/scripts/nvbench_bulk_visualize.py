#!/usr/bin/env python
#
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .nvbench_tooling_deps import (
        MissingToolingDependencyError,
        ToolingDependency,
        require_tooling_dependency,
    )
else:
    from nvbench_tooling_deps import (  # type: ignore[no-redef]
        MissingToolingDependencyError,
        ToolingDependency,
        require_tooling_dependency,
    )


TOOL_NAME = "nvbench-bulk-visualize"

DEFAULT_COVERAGE_EPSILON = 0.005
DEFAULT_SAMPLE_COVERAGE_THRESHOLD = 0.97
DEFAULT_SUPPORT_COVERAGE_THRESHOLD = 0.80
DEFAULT_SUPPORT_RARE_SAMPLE_FRACTION = 0.001
DEFAULT_SUPPORT_MAX_REMOVED_SAMPLE_FRACTION = 0.01

AUTO_ASPECT_BY_REASON = {
    "bulk_cycle_data_unusable": "time-freq",
    "bulk_cycle_gap_not_confirmed": "cycle-box",
    "bulk_cycle_same": "cycle-coverage",
    "bulk_cycle_support_mismatch": "cycle-coverage",
    "bulk_data_unavailable": "time",
    "bulk_same": "time-cycle",
    "bulk_time_data_unusable": "time",
    "bulk_time_same": "time-coverage",
    "bulk_time_same_confirmed_by_summary_cycles": "time-coverage",
    "bulk_time_same_without_cycles": "time-coverage",
    "bulk_time_support_mismatch": "time-coverage",
    "centers_not_close": "time-box",
    "clear_gap_confirmed_by_bulk_cycles": "time-cycle",
    "clear_gap_confirmed_by_summary_cycles": "time-box",
    "cycle_same_not_confirmed": "cycle-box",
    "gpu_timing_summaries_missing": "time",
    "invalid_clock_rate": "time-box",
    "missing_clock_rate": "time-box",
    "missing_interval": "time",
    "no_clear_gap": "time-box",
    "noise_too_high": "time-box",
    "noise_unavailable": "time",
    "same_confirmed_by_cycles": "cycle-box",
    "same_summary": "time-box",
    "same_without_clock_rate": "time-box",
    "summary_cycle_gap_not_confirmed": "cycle-box",
}
DEFAULT_AUTO_ASPECT = "time-box"


np: Any = None


def load_numpy() -> Any:
    global np

    if np is None:
        np = require_tooling_dependency(
            ToolingDependency(
                "numpy", "numpy", "bulk data visualization", extra="plot"
            ),
            tool_name=TOOL_NAME,
        )
    return np


def load_pyplot() -> Any:
    return require_tooling_dependency(
        ToolingDependency(
            "matplotlib.pyplot", "matplotlib", "bulk data visualization", extra="plot"
        ),
        tool_name=TOOL_NAME,
    )


def load_ticker() -> Any:
    return require_tooling_dependency(
        ToolingDependency(
            "matplotlib.ticker",
            "matplotlib",
            "bulk data axis formatting",
            extra="plot",
        ),
        tool_name=TOOL_NAME,
    )


def load_seaborn() -> Any:
    return require_tooling_dependency(
        ToolingDependency(
            "seaborn", "seaborn", "bulk data visualization", extra="plot"
        ),
        tool_name=TOOL_NAME,
    )


def load_matplotlib_colors() -> Any:
    return require_tooling_dependency(
        ToolingDependency(
            "matplotlib.colors",
            "matplotlib",
            "bulk data color handling",
            extra="plot",
        ),
        tool_name=TOOL_NAME,
    )


def load_matplotlib_lines() -> Any:
    return require_tooling_dependency(
        ToolingDependency(
            "matplotlib.lines",
            "matplotlib",
            "bulk data legend construction",
            extra="plot",
        ),
        tool_name=TOOL_NAME,
    )


def load_loader_module(loader_path: Path) -> Any:
    loader_path = loader_path.resolve()
    spec = importlib.util.spec_from_file_location(
        "nvbench_bulk_debug_loader", loader_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load loader module from {str(loader_path)!r}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.__nvbench_bulk_loader_dir__ = loader_path.parent
    return module


def resolve_loader_relative_path(loader: Any, path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(loader.__nvbench_bulk_loader_dir__) / candidate


def anti_symmetric_frac_diff(delta_t1: float, delta_t2: float) -> float:
    return (delta_t1 - delta_t2) / min(delta_t1, delta_t2)


def duration_scale_and_label(*arrays: Any) -> tuple[float, str]:
    np = load_numpy()
    max_abs = max(float(np.max(np.abs(array))) for array in arrays if len(array) > 0)
    if max_abs >= 1.0:
        return 1.0, "s"
    if max_abs >= 1e-3:
        return 1e-3, "ms"
    if max_abs >= 1e-6:
        return 1e-6, "us"
    return 1e-9, "ns"


def format_scaled_value(value: float, unit: str) -> str:
    return f"{value:.2f} {unit}"


def format_cycles(cycles: float) -> str:
    if abs(cycles) >= 1e9:
        return f"{cycles / 1e9:.2f} Gcy"
    if abs(cycles) >= 1e6:
        return f"{cycles / 1e6:.2f} Mcy"
    if abs(cycles) >= 1e3:
        return f"{cycles / 1e3:.2f} kcy"
    return f"{cycles:.2f} cy"


def cycle_scale_and_label(*arrays: Any) -> tuple[float, str]:
    np = load_numpy()
    max_abs = max(float(np.max(np.abs(array))) for array in arrays if len(array) > 0)
    if max_abs >= 1e9:
        return 1e9, "Gcycles"
    if max_abs >= 1e6:
        return 1e6, "Mcycles"
    if max_abs >= 1e3:
        return 1e3, "kcycles"
    return 1.0, "cycles"


def frequency_scale_and_label(*arrays: Any) -> tuple[float, str]:
    np = load_numpy()
    max_abs = max(float(np.max(np.abs(array))) for array in arrays if len(array) > 0)
    if max_abs >= 1e9:
        return 1e9, "frequency [GHz]"
    if max_abs >= 1e6:
        return 1e6, "frequency [MHz]"
    if max_abs >= 1e3:
        return 1e3, "frequency [kHz]"
    return 1.0, "frequency [Hz]"


def make_title(loader: Any, bulk_row: dict[str, Any]) -> str:
    benchmark_json_fn = resolve_loader_relative_path(loader, bulk_row["reference_json"])
    with benchmark_json_fn.open("r", encoding="utf-8") as fh:
        json_root = json.load(fh)
    benchmark_name = os.path.basename(json_root["meta"]["argv"][0])
    state_key = bulk_row["state_key"]
    status = bulk_row["status"]
    status_reason = bulk_row["reason"]
    return f"{benchmark_name}:\n {state_key}; {status}({status_reason})"


def validate_log_scale(values: Any, axis_name: str) -> None:
    np = load_numpy()
    if np.any(np.asarray(values, dtype=np.float64) <= 0.0):
        raise ValueError(f"log {axis_name}-scale requires positive values")


def use_plain_numeric_ticks(axis: Any, values: Any = None) -> None:
    np = load_numpy()
    ticker = load_ticker()

    if values is not None:
        values = np.asarray(values, dtype=np.float64)
        values = values[np.isfinite(values) & (values > 0.0)]
        if len(values) > 0:
            value_min = float(np.min(values))
            value_max = float(np.max(values))
            if value_min == value_max:
                ticks = [value_min]
            elif value_max / value_min < 10.0:
                locator = ticker.MaxNLocator(nbins=6)
                ticks = [
                    tick
                    for tick in locator.tick_values(value_min, value_max)
                    if value_min <= tick <= value_max
                ]
                if len(ticks) < 2:
                    ticks = [value_min, value_max]
            else:
                ticks = None

            if ticks is not None:
                axis.set_major_locator(ticker.FixedLocator(ticks))

    axis.set_major_formatter(ticker.FuncFormatter(lambda value, _: f"{value:g}"))
    axis.set_minor_formatter(ticker.NullFormatter())


def format_percentage(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def format_epsilon(value: float) -> str:
    percentage = 100.0 * value
    if percentage == 0.0:
        return "0%"
    if abs(percentage) < 0.1:
        return f"{percentage:.3g}%"
    if abs(percentage) < 1.0:
        return f"{percentage:.2f}%"
    return f"{percentage:.1f}%"


def blend_color(color: Any, target: Any, amount: float) -> tuple[float, float, float]:
    np = load_numpy()
    mcolors = load_matplotlib_colors()

    base_rgb = np.asarray(mcolors.to_rgb(color), dtype=np.float64)
    target_rgb = np.asarray(mcolors.to_rgb(target), dtype=np.float64)
    return tuple((1.0 - amount) * base_rgb + amount * target_rgb)


def sorted_unique_counts(values: Any) -> tuple[Any, Any]:
    np = load_numpy()
    unique_values, unique_counts = np.unique(values, return_counts=True)
    order = np.argsort(unique_values)
    return unique_values[order], unique_counts[order]


def nearest_distances_to_sorted(target: Any, source: Any) -> Any:
    np = load_numpy()
    pos = np.searchsorted(source, target, side="left")
    left = np.clip(pos - 1, 0, len(source) - 1)
    right = np.clip(pos, 0, len(source) - 1)
    return np.minimum(
        np.abs(target - source[left]),
        np.abs(target - source[right]),
    )


def compute_effective_support_mask(counts: Any) -> Any:
    np = load_numpy()
    total_count = np.sum(counts)
    if (
        len(counts) == 0
        or total_count <= 0
        or DEFAULT_SUPPORT_RARE_SAMPLE_FRACTION <= 0.0
        or DEFAULT_SUPPORT_MAX_REMOVED_SAMPLE_FRACTION <= 0.0
    ):
        return np.ones(len(counts), dtype=bool)

    if np.all(counts == 1):
        return np.ones(len(counts), dtype=bool)

    min_count = max(
        2,
        int(np.ceil(DEFAULT_SUPPORT_RARE_SAMPLE_FRACTION * total_count)),
    )
    support_mask = counts >= min_count
    if np.all(support_mask) or not np.any(support_mask):
        return np.ones(len(counts), dtype=bool)

    removed_sample_fraction = np.sum(counts[~support_mask]) / total_count
    if removed_sample_fraction > DEFAULT_SUPPORT_MAX_REMOVED_SAMPLE_FRACTION:
        return np.ones(len(counts), dtype=bool)

    return support_mask


def compute_coverage_details(
    ref_values: Any, cmp_values: Any, epsilon: float = DEFAULT_COVERAGE_EPSILON
) -> dict[str, Any]:
    np = load_numpy()
    ref_values = np.asarray(ref_values, dtype=np.float64)
    cmp_values = np.asarray(cmp_values, dtype=np.float64)
    if len(ref_values) == 0 or len(cmp_values) == 0:
        raise ValueError("coverage plot requires non-empty reference and compare data")
    validate_log_scale(ref_values, "coverage")
    validate_log_scale(cmp_values, "coverage")

    ref_unique, ref_counts = sorted_unique_counts(ref_values)
    cmp_unique, cmp_counts = sorted_unique_counts(cmp_values)

    ref_distances = nearest_distances_to_sorted(np.log(ref_unique), np.log(cmp_unique))
    cmp_distances = nearest_distances_to_sorted(np.log(cmp_unique), np.log(ref_unique))
    tolerance = np.log1p(epsilon)
    ref_covered = ref_distances <= tolerance
    cmp_covered = cmp_distances <= tolerance
    ref_support_mask = compute_effective_support_mask(ref_counts)
    cmp_support_mask = compute_effective_support_mask(cmp_counts)

    return {
        "epsilon": epsilon,
        "ref_unique": ref_unique,
        "cmp_unique": cmp_unique,
        "ref_counts": ref_counts,
        "cmp_counts": cmp_counts,
        "ref_distances": ref_distances,
        "cmp_distances": cmp_distances,
        "ref_covered": ref_covered,
        "cmp_covered": cmp_covered,
        "ref_support_mask": ref_support_mask,
        "cmp_support_mask": cmp_support_mask,
        "ref_sample_coverage": np.sum(ref_counts[ref_covered]) / np.sum(ref_counts),
        "cmp_sample_coverage": np.sum(cmp_counts[cmp_covered]) / np.sum(cmp_counts),
        "ref_support_coverage": np.mean(ref_covered[ref_support_mask]),
        "cmp_support_coverage": np.mean(cmp_covered[cmp_support_mask]),
    }


def coverage_line_widths(counts: Any) -> Any:
    np = load_numpy()
    counts = np.asarray(counts, dtype=np.float64)
    if len(counts) == 0 or np.max(counts) <= 0.0:
        return np.ones(len(counts), dtype=np.float64)
    return 0.8 + 2.2 * np.sqrt(counts / np.max(counts))


def coverage_curve(distances: Any, weights: Any) -> tuple[Any, Any]:
    np = load_numpy()
    epsilons = np.expm1(np.asarray(distances, dtype=np.float64))
    weights = np.asarray(weights, dtype=np.float64)
    total_weight = np.sum(weights)
    if total_weight <= 0.0:
        raise ValueError("coverage curve requires positive total weight")
    return epsilons, weights


def evaluate_coverage_curve(epsilons: Any, weights: Any, points: Any) -> Any:
    np = load_numpy()
    return np.asarray(
        [np.sum(weights[epsilons <= point]) / np.sum(weights) for point in points],
        dtype=np.float64,
    )


def minimum_epsilon_for_coverage_threshold(
    epsilons: Any, weights: Any, threshold: float
) -> float | None:
    np = load_numpy()
    epsilons = np.asarray(epsilons, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    total_weight = np.sum(weights)
    if total_weight <= 0.0:
        raise ValueError("coverage threshold requires positive total weight")

    order = np.argsort(epsilons)
    epsilons = epsilons[order]
    cumulative_coverage = np.cumsum(weights[order]) / total_weight
    passing = np.flatnonzero(cumulative_coverage >= threshold)
    if len(passing) == 0:
        return None
    return float(epsilons[passing[0]])


def compute_cycles(samples: Any, frequencies: Any, label: str) -> Any:
    np = load_numpy()
    if samples is None or frequencies is None:
        raise ValueError(f"{label} cycle plot requires timing and frequency samples")

    if len(samples) != len(frequencies):
        raise ValueError(
            f"{label} cycle plot requires matching timing/frequency sample counts; "
            f"got {len(samples)} timings and {len(frequencies)} frequencies"
        )

    return np.asarray(samples, dtype=np.float64) * np.asarray(
        frequencies, dtype=np.float64
    )


def center_midpoint(center_r: float, center_c: float, xscale: str) -> float:
    if xscale == "log" and center_r > 0.0 and center_c > 0.0:
        return (center_r * center_c) ** 0.5
    return 0.5 * (center_r + center_c)


def set_padded_x_limits(ax: Any, values: Any, xscale: str) -> None:
    np = load_numpy()
    value_min = float(np.min(values))
    value_max = float(np.max(values))
    if xscale == "log":
        if value_min == value_max:
            ax.set_xlim(value_min / 1.05, value_max * 1.05)
        else:
            log_pad = 0.05 * (np.log(value_max) - np.log(value_min))
            ax.set_xlim(
                np.exp(np.log(value_min) - log_pad),
                np.exp(np.log(value_max) + log_pad),
            )
    else:
        value_pad = (
            0.05 * (value_max - value_min)
            if value_max != value_min
            else 0.05 * max(abs(value_min), 1.0)
        )
        ax.set_xlim(value_min - value_pad, value_max + value_pad)


def padded_limits(values: Any, scale: str) -> tuple[float, float]:
    np = load_numpy()
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        raise ValueError("cannot set plot limits from empty data")

    value_min = float(np.min(values))
    value_max = float(np.max(values))
    if scale == "log":
        validate_log_scale(values, "axis")
        if value_min == value_max:
            return value_min / 1.05, value_max * 1.05
        log_pad = 0.05 * (np.log(value_max) - np.log(value_min))
        return (
            np.exp(np.log(value_min) - log_pad),
            np.exp(np.log(value_max) + log_pad),
        )

    value_pad = (
        0.05 * (value_max - value_min)
        if value_max != value_min
        else 0.05 * max(abs(value_min), 1.0)
    )
    return value_min - value_pad, value_max + value_pad


def set_padded_limits(ax: Any, *, x_values: Any, y_values: Any) -> None:
    np = load_numpy()
    x_min = float(np.min(x_values))
    x_max = float(np.max(x_values))
    y_min = float(np.min(y_values))
    y_max = float(np.max(y_values))

    x_pad = 0.05 * (x_max - x_min) if x_max != x_min else 0.05 * max(abs(x_min), 1.0)
    y_pad = 0.05 * (y_max - y_min) if y_max != y_min else 0.05 * max(abs(y_min), 1.0)

    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)


def plot_distribution(
    loader: Any,
    bulk_row: dict[str, Any],
    data_r: Any,
    data_c: Any,
    center_r: float,
    center_c: float,
    *,
    center_formatter: Any,
    x_label: str,
    xscale: str,
    yscale: str,
) -> None:
    np = load_numpy()
    plt = load_pyplot()
    sns = load_seaborn()

    current_palette = sns.color_palette()
    color1 = current_palette[0]
    color2 = current_palette[1]

    fig, (ax1, ax_rug) = plt.subplots(
        2,
        1,
        figsize=(10, 6),
        sharex=True,
        gridspec_kw={"height_ratios": [5.0, 0.45], "hspace": 0.04},
    )

    sns.histplot(data_r, ax=ax1, color=color1, label="Ref")
    sns.histplot(data_c, ax=ax1, color=color2, label="Cmp")
    if xscale == "log":
        validate_log_scale(np.concatenate([data_r, data_c]), "x")
    if yscale == "log":
        _, ymax = ax1.get_ylim()
        validate_log_scale([ymax], "y")
    ax1.set_xscale(xscale)
    ax1.set_yscale(yscale)
    ax_rug.set_xscale(xscale)
    if xscale == "log":
        use_plain_numeric_ticks(ax_rug.xaxis, np.concatenate([data_r, data_c]))
    if yscale == "log":
        _, ymax = ax1.get_ylim()
        use_plain_numeric_ticks(ax1.yaxis, [1.0, ymax])

    ax1.axvline(
        center_r,
        color=color1,
        linestyle="--",
        linewidth=2,
        label=f"Center Ref: {center_formatter(center_r)}",
    )
    ax1.axvline(
        center_c,
        color=color2,
        linestyle="--",
        linewidth=2,
        label=f"Center Cmp: {center_formatter(center_c)}",
    )

    if center_r > 0 and center_c > 0 and center_r != center_c:
        _, ymax = ax1.get_ylim()
        arrow_y = ymax * 0.88
        label_y = ymax * 0.91
        ax1.set_ylim(top=ymax * 1.05)

        center_diff = anti_symmetric_frac_diff(center_c, center_r)
        ax1.annotate(
            "",
            xy=(center_c, arrow_y),
            xytext=(center_r, arrow_y),
            arrowprops={
                "arrowstyle": "<->",
                "color": "0.25",
                "linewidth": 1.5,
            },
        )
        ax1.text(
            center_midpoint(center_r, center_c, xscale),
            label_y,
            f"center diff: {100.0 * center_diff:+.2f}%",
            ha="center",
            va="bottom",
            color="0.25",
            fontsize=10,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 1.5},
        )

    ax1.legend(loc="upper right", fontsize=9)

    ax_rug.vlines(
        np.unique(data_r), 0.55, 0.95, color=color1, alpha=0.65, linewidth=1.0
    )
    ax_rug.vlines(
        np.unique(data_c), 0.05, 0.45, color=color2, alpha=0.65, linewidth=1.0
    )
    ax_rug.set_ylim(0.0, 1.0)
    ax_rug.set_yticks([0.25, 0.75])
    ax_rug.set_yticklabels(["Cmp", "Ref"])
    ax_rug.tick_params(axis="y", length=0)
    ax_rug.spines["top"].set_visible(False)
    ax_rug.spines["right"].set_visible(False)
    ax_rug.spines["left"].set_visible(False)
    ax_rug.set_xlabel(x_label)

    ax1.set_xlabel("")
    ax1.tick_params(axis="x", labelbottom=False)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    fig.suptitle(make_title(loader, bulk_row), fontsize=14, fontweight="bold", y=0.98)
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.12, top=0.80, hspace=0.05)
    plt.show()


def plot_time_distribution(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str, yscale: str
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    time_scale, time_unit = duration_scale_and_label(
        data["reference_samples"], data["compare_samples"]
    )
    plot_distribution(
        loader,
        bulk_row,
        np.asarray(data["reference_samples"], dtype=np.float64) / time_scale,
        np.asarray(data["compare_samples"], dtype=np.float64) / time_scale,
        bulk_row["reference_time"] / time_scale,
        bulk_row["compare_time"] / time_scale,
        center_formatter=lambda value: format_scaled_value(value, time_unit),
        x_label=f"Timing samples [{time_unit}]",
        xscale=xscale,
        yscale=yscale,
    )


def plot_cycle_distribution(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str, yscale: str
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    cycles_r = compute_cycles(
        data["reference_samples"], data["reference_frequencies"], "reference"
    )
    cycles_c = compute_cycles(
        data["compare_samples"], data["compare_frequencies"], "compare"
    )

    plot_distribution(
        loader,
        bulk_row,
        cycles_r,
        cycles_c,
        float(np.median(cycles_r)),
        float(np.median(cycles_c)),
        center_formatter=format_cycles,
        x_label="Cycle samples",
        xscale=xscale,
        yscale=yscale,
    )


def plot_box_rug(
    loader: Any,
    bulk_row: dict[str, Any],
    data_r: Any,
    data_c: Any,
    center_r: float,
    center_c: float,
    *,
    center_formatter: Any,
    x_label: str,
    title: str,
    xscale: str,
) -> None:
    np = load_numpy()
    plt = load_pyplot()
    sns = load_seaborn()
    Line2D = load_matplotlib_lines().Line2D

    if xscale == "log":
        validate_log_scale(np.concatenate([data_r, data_c]), "x")

    current_palette = sns.color_palette()
    color_ref = current_palette[0]
    color_cmp = current_palette[1]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    box = ax.boxplot(
        [data_c, data_r],
        orientation="horizontal",
        positions=[0.0, 1.0],
        widths=0.28,
        patch_artist=True,
        showfliers=True,
        manage_ticks=False,
    )
    for patch, color in zip(box["boxes"], [color_cmp, color_ref], strict=True):
        patch.set_facecolor(color)
        patch.set_alpha(0.22)
        patch.set_edgecolor(color)
    for median, color in zip(box["medians"], [color_cmp, color_ref], strict=True):
        median.set_color(color)
        median.set_linewidth(2.0)

    ax.vlines(
        np.unique(data_c), -0.38, -0.22, color=color_cmp, alpha=0.65, linewidth=1.0
    )
    ax.vlines(np.unique(data_r), 1.22, 1.38, color=color_ref, alpha=0.65, linewidth=1.0)
    cmp_quantiles = np.quantile(data_c, np.arange(0.1, 1.0, 0.1))
    ref_quantiles = np.quantile(data_r, np.arange(0.1, 1.0, 0.1))
    ax.scatter(
        cmp_quantiles,
        np.full_like(cmp_quantiles, 0.24, dtype=np.float64),
        marker="v",
        color=color_cmp,
        alpha=0.75,
        s=36,
        zorder=3,
    )
    ax.scatter(
        ref_quantiles,
        np.full_like(ref_quantiles, 0.76, dtype=np.float64),
        marker="^",
        color=color_ref,
        alpha=0.75,
        s=36,
        zorder=3,
    )

    ax.scatter(
        [center_c],
        [0.0],
        color=color_cmp,
        edgecolor="black",
        linewidth=0.8,
        marker="D",
        s=55,
        label=f"Center Cmp: {center_formatter(center_c)}",
        zorder=3,
    )
    ax.scatter(
        [center_r],
        [1.0],
        color=color_ref,
        edgecolor="black",
        linewidth=0.8,
        marker="D",
        s=55,
        label=f"Center Ref: {center_formatter(center_r)}",
        zorder=3,
    )

    ax.set_xscale(xscale)
    if xscale == "log":
        use_plain_numeric_ticks(ax.xaxis, np.concatenate([data_r, data_c]))

    all_values = np.concatenate([data_r, data_c])
    set_padded_x_limits(ax, all_values, xscale)

    if center_r > 0 and center_c > 0 and center_r != center_c:
        arrow_y = 1.62
        label_y = 1.70
        center_diff = anti_symmetric_frac_diff(center_c, center_r)
        ax.annotate(
            "",
            xy=(center_c, arrow_y),
            xytext=(center_r, arrow_y),
            arrowprops={
                "arrowstyle": "<->",
                "color": "0.25",
                "linewidth": 1.5,
            },
        )
        ax.text(
            center_midpoint(center_r, center_c, xscale),
            label_y,
            f"center diff: {100.0 * center_diff:+.2f}%",
            ha="center",
            va="bottom",
            color="0.25",
            fontsize=10,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 1.5},
        )

    ax.set_ylim(-0.55, 1.90)
    ax.set_yticks([0.0, 1.0])
    ax.set_yticklabels(["Cmp", "Ref"])
    ax.set_xlabel(x_label)
    ax.set_title(title)
    center_handles, center_labels = ax.get_legend_handles_labels()
    center_legend = ax.legend(
        center_handles,
        center_labels,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
        fontsize=9,
    )
    ax.add_artist(center_legend)

    decile_handles = [
        Line2D(
            [0],
            [0],
            marker="v",
            color="none",
            markerfacecolor=color_cmp,
            markeredgecolor=color_cmp,
            markersize=6,
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="none",
            markerfacecolor=color_ref,
            markeredgecolor=color_ref,
            markersize=6,
        ),
    ]
    ax.legend(
        decile_handles,
        ["Cmp deciles", "Ref deciles"],
        loc="lower left",
        bbox_to_anchor=(1.02, 0.0),
        borderaxespad=0.0,
        fontsize=9,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.suptitle(make_title(loader, bulk_row), fontsize=14, fontweight="bold", y=0.98)
    fig.subplots_adjust(left=0.10, right=0.74, bottom=0.14, top=0.76)
    plt.show()


def plot_time_box(loader: Any, bulk_row: dict[str, Any], *, xscale: str) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    time_scale, time_unit = duration_scale_and_label(
        data["reference_samples"], data["compare_samples"]
    )
    plot_box_rug(
        loader,
        bulk_row,
        np.asarray(data["reference_samples"], dtype=np.float64) / time_scale,
        np.asarray(data["compare_samples"], dtype=np.float64) / time_scale,
        bulk_row["reference_time"] / time_scale,
        bulk_row["compare_time"] / time_scale,
        center_formatter=lambda value: format_scaled_value(value, time_unit),
        x_label=f"Timing samples [{time_unit}]",
        title="Timing box/support geometry",
        xscale=xscale,
    )


def plot_cycle_box(loader: Any, bulk_row: dict[str, Any], *, xscale: str) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    cycles_r = compute_cycles(
        data["reference_samples"], data["reference_frequencies"], "reference"
    )
    cycles_c = compute_cycles(
        data["compare_samples"], data["compare_frequencies"], "compare"
    )
    cycle_scale, cycle_label = cycle_scale_and_label(cycles_r, cycles_c)
    cycles_r_scaled = cycles_r / cycle_scale
    cycles_c_scaled = cycles_c / cycle_scale
    plot_box_rug(
        loader,
        bulk_row,
        cycles_r_scaled,
        cycles_c_scaled,
        float(np.median(cycles_r_scaled)),
        float(np.median(cycles_c_scaled)),
        center_formatter=lambda value: format_scaled_value(value, cycle_label),
        x_label=cycle_label,
        title="Cycle box/support geometry",
        xscale=xscale,
    )


def plot_coverage_rug(
    loader: Any,
    bulk_row: dict[str, Any],
    data_r: Any,
    data_c: Any,
    *,
    x_label: str,
    title: str,
    xscale: str,
    epsilon: float = DEFAULT_COVERAGE_EPSILON,
) -> None:
    np = load_numpy()
    plt = load_pyplot()
    sns = load_seaborn()
    Line2D = load_matplotlib_lines().Line2D

    details = compute_coverage_details(data_r, data_c, epsilon)

    current_palette = sns.color_palette()
    color_ref = current_palette[0]
    color_cmp = current_palette[1]
    uncovered_ref = blend_color(color_ref, "red", 0.45)
    uncovered_cmp = blend_color(color_cmp, "red", 0.45)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    for unique, counts, covered, y_position, covered_color, uncovered_color in [
        (
            details["cmp_unique"],
            details["cmp_counts"],
            details["cmp_covered"],
            0.0,
            color_cmp,
            uncovered_cmp,
        ),
        (
            details["ref_unique"],
            details["ref_counts"],
            details["ref_covered"],
            1.0,
            color_ref,
            uncovered_ref,
        ),
    ]:
        ax.hlines(
            [
                y_position - 0.34,
                y_position - 0.28,
                y_position + 0.28,
                y_position + 0.34,
            ],
            xmin=0.0,
            xmax=1.0,
            transform=ax.get_yaxis_transform(),
            color="0.86",
            linewidth=0.6,
            zorder=0,
        )
        widths = coverage_line_widths(counts)
        for is_covered, mark_color, alpha, y0, y1 in [
            (True, covered_color, 0.85, y_position - 0.28, y_position + 0.28),
            (False, uncovered_color, 0.78, y_position - 0.34, y_position + 0.34),
        ]:
            mask = covered == is_covered
            ax.vlines(
                unique[mask],
                y0,
                y1,
                color=mark_color,
                alpha=alpha,
                linewidth=widths[mask],
            )
        if np.any(~covered):
            ax.scatter(
                unique[~covered],
                np.full(np.count_nonzero(~covered), y_position),
                marker="x",
                color=uncovered_color,
                alpha=0.80,
                s=36,
                zorder=3,
            )

    ax.set_xscale(xscale)
    all_values = np.concatenate([details["ref_unique"], details["cmp_unique"]])
    if xscale == "log":
        use_plain_numeric_ticks(ax.xaxis, all_values)
    set_padded_x_limits(ax, all_values, xscale)

    ax.set_ylim(-0.55, 1.55)
    ax.set_yticks([0.0, 1.0])
    ax.set_yticklabels(["Cmp", "Ref"])
    ax.set_xlabel(x_label)
    ax.set_title(title)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    metric_text = "\n".join(
        [
            f"epsilon: {format_percentage(epsilon)}",
            (
                "Ref sample/support: "
                f"{format_percentage(details['ref_sample_coverage'])} / "
                f"{format_percentage(details['ref_support_coverage'])}"
            ),
            (
                "Cmp sample/support: "
                f"{format_percentage(details['cmp_sample_coverage'])} / "
                f"{format_percentage(details['cmp_support_coverage'])}"
            ),
        ]
    )
    ax.text(
        1.02,
        0.55,
        metric_text,
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=10,
        bbox={"facecolor": "white", "edgecolor": "0.8", "alpha": 0.85, "pad": 4},
    )
    ax.legend(
        [
            Line2D([0], [0], color="0.25", linewidth=2.0, alpha=0.85),
            Line2D(
                [0],
                [0],
                color=blend_color("0.25", "red", 0.45),
                marker="x",
                linestyle="-",
                linewidth=2.0,
                markersize=7,
            ),
        ],
        ["covered", "not covered"],
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
        fontsize=9,
    )

    fig.suptitle(make_title(loader, bulk_row), fontsize=14, fontweight="bold", y=0.98)
    fig.subplots_adjust(left=0.10, right=0.70, bottom=0.18, top=0.72)
    plt.show()


def plot_time_coverage(loader: Any, bulk_row: dict[str, Any], *, xscale: str) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    time_scale, time_unit = duration_scale_and_label(
        data["reference_samples"], data["compare_samples"]
    )
    plot_coverage_rug(
        loader,
        bulk_row,
        np.asarray(data["reference_samples"], dtype=np.float64) / time_scale,
        np.asarray(data["compare_samples"], dtype=np.float64) / time_scale,
        x_label=f"Timing support [{time_unit}]",
        title="Timing coverage",
        xscale=xscale,
    )


def plot_cycle_coverage(loader: Any, bulk_row: dict[str, Any], *, xscale: str) -> None:
    data = loader.load_bulk_data(bulk_row)
    cycles_r = compute_cycles(
        data["reference_samples"], data["reference_frequencies"], "reference"
    )
    cycles_c = compute_cycles(
        data["compare_samples"], data["compare_frequencies"], "compare"
    )
    cycle_scale, cycle_label = cycle_scale_and_label(cycles_r, cycles_c)
    plot_coverage_rug(
        loader,
        bulk_row,
        cycles_r / cycle_scale,
        cycles_c / cycle_scale,
        x_label=f"Cycle support [{cycle_label}]",
        title="Cycle coverage",
        xscale=xscale,
    )


def plot_coverage_curves(
    loader: Any,
    bulk_row: dict[str, Any],
    data_r: Any,
    data_c: Any,
    *,
    title: str,
    xscale: str,
    epsilon: float = DEFAULT_COVERAGE_EPSILON,
) -> None:
    np = load_numpy()
    plt = load_pyplot()
    ticker = load_ticker()
    sns = load_seaborn()

    details = compute_coverage_details(data_r, data_c, epsilon)
    curves = [
        (
            "Ref sample",
            *coverage_curve(details["ref_distances"], details["ref_counts"]),
            DEFAULT_SAMPLE_COVERAGE_THRESHOLD,
        ),
        (
            "Cmp sample",
            *coverage_curve(details["cmp_distances"], details["cmp_counts"]),
            DEFAULT_SAMPLE_COVERAGE_THRESHOLD,
        ),
        (
            "Ref support",
            *coverage_curve(
                details["ref_distances"][details["ref_support_mask"]],
                np.ones(np.count_nonzero(details["ref_support_mask"])),
            ),
            DEFAULT_SUPPORT_COVERAGE_THRESHOLD,
        ),
        (
            "Cmp support",
            *coverage_curve(
                details["cmp_distances"][details["cmp_support_mask"]],
                np.ones(np.count_nonzero(details["cmp_support_mask"])),
            ),
            DEFAULT_SUPPORT_COVERAGE_THRESHOLD,
        ),
    ]
    minimum_epsilons = [
        (
            label,
            minimum_epsilon_for_coverage_threshold(epsilons, weights, threshold),
        )
        for label, epsilons, weights, threshold in curves
    ]
    if any(value is None for _, value in minimum_epsilons):
        raise ValueError("coverage threshold cannot be reached")

    minimum_passing_epsilon = max(value for _, value in minimum_epsilons)
    limiting_curves = [
        label
        for label, value in minimum_epsilons
        if np.isclose(value, minimum_passing_epsilon, rtol=1e-10, atol=1e-15)
    ]

    all_epsilons = np.concatenate([curve[1] for curve in curves])
    max_epsilon = max(float(np.max(all_epsilons)), epsilon, minimum_passing_epsilon)
    points = np.unique(
        np.concatenate(
            [[0.0, epsilon, minimum_passing_epsilon, max_epsilon * 1.05], all_epsilons]
        )
    )
    if xscale == "log":
        points = points[points > 0.0]
        if len(points) == 0:
            raise ValueError("log x-scale requires positive coverage epsilon values")

    current_palette = sns.color_palette()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for (label, epsilons, weights, _), color in zip(
        curves, current_palette, strict=False
    ):
        coverage = evaluate_coverage_curve(epsilons, weights, points)
        ax.step(
            points * 100.0, coverage * 100.0, where="post", label=label, color=color
        )

    ax.axvline(
        epsilon * 100.0,
        color="0.25",
        linestyle=":",
        linewidth=1.5,
        label=f"epsilon {format_percentage(epsilon)}",
    )
    if minimum_passing_epsilon > 0.0 or xscale == "linear":
        ax.axvline(
            minimum_passing_epsilon * 100.0,
            color="black",
            linestyle="-",
            linewidth=1.4,
            label=f"min passing epsilon {format_epsilon(minimum_passing_epsilon)}",
        )
    ax.axhline(
        DEFAULT_SAMPLE_COVERAGE_THRESHOLD * 100.0,
        color="0.4",
        linestyle="--",
        linewidth=1.0,
        label=f"sample threshold {format_percentage(DEFAULT_SAMPLE_COVERAGE_THRESHOLD)}",
    )
    ax.axhline(
        DEFAULT_SUPPORT_COVERAGE_THRESHOLD * 100.0,
        color="0.4",
        linestyle="-.",
        linewidth=1.0,
        label=f"support threshold {format_percentage(DEFAULT_SUPPORT_COVERAGE_THRESHOLD)}",
    )

    ax.set_xscale(xscale)
    if xscale == "log":
        use_plain_numeric_ticks(ax.xaxis, points * 100.0)
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=100.0))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda value, _: f"{value:g}%"))
    ax.set_ylim(-2.0, 102.0)
    ax.set_xlabel("epsilon")
    ax.set_ylabel("coverage")
    ax.set_title(title)
    ax.text(
        0.02,
        0.04,
        "\n".join(
            [
                "smallest epsilon meeting all thresholds: "
                f"{format_epsilon(minimum_passing_epsilon)}",
                f"limiting curve: {', '.join(limiting_curves)}",
            ]
        ),
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "0.8", "alpha": 0.86, "pad": 4},
    )
    ax.legend(loc="lower right", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.suptitle(make_title(loader, bulk_row), fontsize=14, fontweight="bold", y=0.98)
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.14, top=0.76)
    plt.show()


def plot_time_coverage_curve(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str
) -> None:
    data = loader.load_bulk_data(bulk_row)
    plot_coverage_curves(
        loader,
        bulk_row,
        data["reference_samples"],
        data["compare_samples"],
        title="Timing coverage trajectory",
        xscale=xscale,
    )


def plot_cycle_coverage_curve(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str
) -> None:
    data = loader.load_bulk_data(bulk_row)
    cycles_r = compute_cycles(
        data["reference_samples"], data["reference_frequencies"], "reference"
    )
    cycles_c = compute_cycles(
        data["compare_samples"], data["compare_frequencies"], "compare"
    )
    plot_coverage_curves(
        loader,
        bulk_row,
        cycles_r,
        cycles_c,
        title="Cycle coverage trajectory",
        xscale=xscale,
    )


def plot_time_metric_pairs(
    loader: Any,
    bulk_row: dict[str, Any],
    *,
    ref_times: Any,
    cmp_times: Any,
    ref_metric: Any,
    cmp_metric: Any,
    ref_metric_center: float,
    cmp_metric_center: float,
    y_label: str,
    title: str,
    xscale: str,
    yscale: str,
) -> None:
    np = load_numpy()
    plt = load_pyplot()
    sns = load_seaborn()

    all_times = np.concatenate([ref_times, cmp_times])
    all_metric = np.concatenate([ref_metric, cmp_metric])
    if xscale == "log":
        validate_log_scale(all_times, "x")
    if yscale == "log":
        validate_log_scale(all_metric, "y")

    current_palette = sns.color_palette()
    color_ref = current_palette[0]
    color_cmp = current_palette[1]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(ref_times, ref_metric, color=color_ref, alpha=0.55, s=20, label="Ref")
    ax.scatter(cmp_times, cmp_metric, color=color_cmp, alpha=0.55, s=20, label="Cmp")

    sns.rugplot(x=ref_times, ax=ax, color=color_ref, height=0.04, alpha=0.25)
    sns.rugplot(y=ref_metric, ax=ax, color=color_ref, height=0.04, alpha=0.25)
    sns.rugplot(x=cmp_times, ax=ax, color=color_cmp, height=0.04, alpha=0.25)
    sns.rugplot(y=cmp_metric, ax=ax, color=color_cmp, height=0.04, alpha=0.25)

    ref_time_center = bulk_row["reference_time"] * 1e6
    cmp_time_center = bulk_row["compare_time"] * 1e6

    ax.axvline(ref_time_center, color=color_ref, linestyle="--", linewidth=1.5)
    ax.axhline(ref_metric_center, color=color_ref, linestyle="--", linewidth=1.5)
    ax.axvline(cmp_time_center, color=color_cmp, linestyle="--", linewidth=1.5)
    ax.axhline(cmp_metric_center, color=color_cmp, linestyle="--", linewidth=1.5)
    ax.scatter(
        [ref_time_center],
        [ref_metric_center],
        color=color_ref,
        edgecolor="black",
        linewidth=0.8,
        s=65,
        zorder=3,
    )
    ax.scatter(
        [cmp_time_center],
        [cmp_metric_center],
        color=color_cmp,
        edgecolor="black",
        linewidth=0.8,
        s=65,
        zorder=3,
    )

    set_padded_limits(ax, x_values=all_times, y_values=all_metric)
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    if xscale == "log":
        use_plain_numeric_ticks(ax.xaxis, all_times)
    if yscale == "log":
        use_plain_numeric_ticks(ax.yaxis, all_metric)
    ax.set_xlabel("time [us]")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.legend()

    plt.suptitle(make_title(loader, bulk_row), fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout()
    plt.show()


def plot_time_cycle_distribution(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str, yscale: str
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    ref_times = np.asarray(data["reference_samples"], dtype=np.float64) * 1e6
    cmp_times = np.asarray(data["compare_samples"], dtype=np.float64) * 1e6
    ref_cycles = compute_cycles(
        data["reference_samples"], data["reference_frequencies"], "reference"
    )
    cmp_cycles = compute_cycles(
        data["compare_samples"], data["compare_frequencies"], "compare"
    )

    cycle_scale, cycle_label = cycle_scale_and_label(ref_cycles, cmp_cycles)
    ref_cycles_scaled = ref_cycles / cycle_scale
    cmp_cycles_scaled = cmp_cycles / cycle_scale
    plot_time_metric_pairs(
        loader,
        bulk_row,
        ref_times=ref_times,
        cmp_times=cmp_times,
        ref_metric=ref_cycles_scaled,
        cmp_metric=cmp_cycles_scaled,
        ref_metric_center=float(np.median(ref_cycles_scaled)),
        cmp_metric_center=float(np.median(cmp_cycles_scaled)),
        y_label=cycle_label,
        title="Time/cycle sample pairs",
        xscale=xscale,
        yscale=yscale,
    )


def plot_time_frequency_distribution(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str, yscale: str
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    if data["reference_frequencies"] is None or data["compare_frequencies"] is None:
        raise ValueError("time/frequency plot requires frequency samples")

    ref_times = np.asarray(data["reference_samples"], dtype=np.float64) * 1e6
    cmp_times = np.asarray(data["compare_samples"], dtype=np.float64) * 1e6
    ref_frequencies = np.asarray(data["reference_frequencies"], dtype=np.float64)
    cmp_frequencies = np.asarray(data["compare_frequencies"], dtype=np.float64)

    if len(ref_times) != len(ref_frequencies):
        raise ValueError(
            "reference time/frequency plot requires matching sample counts; "
            f"got {len(ref_times)} timings and {len(ref_frequencies)} frequencies"
        )
    if len(cmp_times) != len(cmp_frequencies):
        raise ValueError(
            "compare time/frequency plot requires matching sample counts; "
            f"got {len(cmp_times)} timings and {len(cmp_frequencies)} frequencies"
        )

    frequency_scale, frequency_label = frequency_scale_and_label(
        ref_frequencies, cmp_frequencies
    )
    ref_frequencies_scaled = ref_frequencies / frequency_scale
    cmp_frequencies_scaled = cmp_frequencies / frequency_scale
    plot_time_metric_pairs(
        loader,
        bulk_row,
        ref_times=ref_times,
        cmp_times=cmp_times,
        ref_metric=ref_frequencies_scaled,
        cmp_metric=cmp_frequencies_scaled,
        ref_metric_center=float(np.median(ref_frequencies_scaled)),
        cmp_metric_center=float(np.median(cmp_frequencies_scaled)),
        y_label=frequency_label,
        title="Time/frequency sample pairs",
        xscale=xscale,
        yscale=yscale,
    )


def plot_sequence_axis(
    ax: Any,
    values: Any,
    *,
    color: Any,
    title: str,
    y_label: str,
    y_center: float,
    y_center_label: str,
    xscale: str,
    yscale: str,
    y_axis_side: str = "left",
) -> None:
    np = load_numpy()
    indices = np.arange(1, len(values) + 1, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if yscale == "log":
        validate_log_scale(values, "y")

    ax.plot(
        indices,
        values,
        color=color,
        marker=".",
        markersize=3.0,
        linewidth=0.8,
        alpha=0.72,
    )
    ax.axhline(
        y_center,
        color=color,
        linestyle="--",
        linewidth=1.4,
        label=y_center_label,
    )
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    if xscale == "log":
        use_plain_numeric_ticks(ax.xaxis, indices)
    if yscale == "log":
        use_plain_numeric_ticks(ax.yaxis, values)
    ax.set_title(title)
    ax.set_ylabel(y_label)
    if y_axis_side == "right":
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.tick_params(axis="y", labelright=True, labelleft=False)
    else:
        ax.yaxis.set_label_position("left")
        ax.yaxis.tick_left()
        ax.tick_params(axis="y", labelleft=True, labelright=False)
    ax.legend(loc="upper right", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(y_axis_side == "right")
    ax.spines["left"].set_visible(y_axis_side == "left")


def plot_two_quantity_sequence(
    loader: Any,
    bulk_row: dict[str, Any],
    *,
    ref_top: Any,
    cmp_top: Any,
    ref_time: Any,
    cmp_time: Any,
    top_label: str,
    top_title: str,
    ref_top_center: float,
    cmp_top_center: float,
    top_center_label: str,
    time_unit: str,
    ref_time_center: float,
    cmp_time_center: float,
    xscale: str,
    yscale: str,
) -> None:
    plt = load_pyplot()
    sns = load_seaborn()

    current_palette = sns.color_palette()
    color_ref = current_palette[0]
    color_cmp = current_palette[1]

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(12, 7),
        sharey="row",
        gridspec_kw={"hspace": 0.34, "wspace": 0.08},
    )
    plot_sequence_axis(
        axes[0, 0],
        ref_top,
        color=color_ref,
        title=f"Ref {top_title} sequence",
        y_label=top_label,
        y_center=ref_top_center,
        y_center_label=top_center_label,
        xscale=xscale,
        yscale=yscale,
        y_axis_side="left",
    )
    plot_sequence_axis(
        axes[0, 1],
        cmp_top,
        color=color_cmp,
        title=f"Cmp {top_title} sequence",
        y_label=top_label,
        y_center=cmp_top_center,
        y_center_label=top_center_label,
        xscale=xscale,
        yscale=yscale,
        y_axis_side="right",
    )
    plot_sequence_axis(
        axes[1, 0],
        ref_time,
        color=color_ref,
        title="Ref timing sequence",
        y_label=f"Timing samples [{time_unit}]",
        y_center=ref_time_center,
        y_center_label="center",
        xscale=xscale,
        yscale=yscale,
        y_axis_side="left",
    )
    plot_sequence_axis(
        axes[1, 1],
        cmp_time,
        color=color_cmp,
        title="Cmp timing sequence",
        y_label=f"Timing samples [{time_unit}]",
        y_center=cmp_time_center,
        y_center_label="center",
        xscale=xscale,
        yscale=yscale,
        y_axis_side="right",
    )

    axes[0, 0].tick_params(axis="x", labelbottom=False)
    axes[0, 1].tick_params(axis="x", labelbottom=False)
    axes[1, 0].set_xlabel("sample index")
    axes[1, 1].set_xlabel("sample index")

    fig.suptitle(make_title(loader, bulk_row), fontsize=14, fontweight="bold", y=0.98)
    fig.subplots_adjust(left=0.09, right=0.90, bottom=0.09, top=0.86)
    plt.show()


def plot_time_frequency_sequence(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str, yscale: str
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    if data["reference_frequencies"] is None or data["compare_frequencies"] is None:
        raise ValueError("sequence plot requires frequency samples")

    ref_times = np.asarray(data["reference_samples"], dtype=np.float64)
    cmp_times = np.asarray(data["compare_samples"], dtype=np.float64)
    ref_frequencies = np.asarray(data["reference_frequencies"], dtype=np.float64)
    cmp_frequencies = np.asarray(data["compare_frequencies"], dtype=np.float64)

    if len(ref_times) != len(ref_frequencies):
        raise ValueError(
            "reference sequence plot requires matching sample counts; "
            f"got {len(ref_times)} timings and {len(ref_frequencies)} frequencies"
        )
    if len(cmp_times) != len(cmp_frequencies):
        raise ValueError(
            "compare sequence plot requires matching sample counts; "
            f"got {len(cmp_times)} timings and {len(cmp_frequencies)} frequencies"
        )

    time_scale, time_unit = duration_scale_and_label(ref_times, cmp_times)
    frequency_scale, frequency_label = frequency_scale_and_label(
        ref_frequencies, cmp_frequencies
    )

    plot_two_quantity_sequence(
        loader,
        bulk_row,
        ref_top=ref_frequencies / frequency_scale,
        cmp_top=cmp_frequencies / frequency_scale,
        ref_time=ref_times / time_scale,
        cmp_time=cmp_times / time_scale,
        top_label=frequency_label,
        top_title="frequency",
        ref_top_center=float(np.median(ref_frequencies / frequency_scale)),
        cmp_top_center=float(np.median(cmp_frequencies / frequency_scale)),
        top_center_label="median",
        time_unit=time_unit,
        ref_time_center=bulk_row["reference_time"] / time_scale,
        cmp_time_center=bulk_row["compare_time"] / time_scale,
        xscale=xscale,
        yscale=yscale,
    )


def plot_time_cycle_sequence(
    loader: Any, bulk_row: dict[str, Any], *, xscale: str, yscale: str
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    ref_times = np.asarray(data["reference_samples"], dtype=np.float64)
    cmp_times = np.asarray(data["compare_samples"], dtype=np.float64)
    ref_cycles = compute_cycles(
        data["reference_samples"], data["reference_frequencies"], "reference"
    )
    cmp_cycles = compute_cycles(
        data["compare_samples"], data["compare_frequencies"], "compare"
    )

    time_scale, time_unit = duration_scale_and_label(ref_times, cmp_times)
    cycle_scale, cycle_label = cycle_scale_and_label(ref_cycles, cmp_cycles)

    plot_two_quantity_sequence(
        loader,
        bulk_row,
        ref_top=ref_cycles / cycle_scale,
        cmp_top=cmp_cycles / cycle_scale,
        ref_time=ref_times / time_scale,
        cmp_time=cmp_times / time_scale,
        top_label=cycle_label,
        top_title="cycle",
        ref_top_center=float(np.median(ref_cycles / cycle_scale)),
        cmp_top_center=float(np.median(cmp_cycles / cycle_scale)),
        top_center_label="median",
        time_unit=time_unit,
        ref_time_center=bulk_row["reference_time"] / time_scale,
        cmp_time_center=bulk_row["compare_time"] / time_scale,
        xscale=xscale,
        yscale=yscale,
    )


def lagged_phase_values(values: Any, lag: int) -> tuple[Any, Any]:
    np = load_numpy()
    values = np.asarray(values, dtype=np.float64)
    if lag <= 0:
        raise ValueError("lag must be positive")
    if len(values) <= lag:
        raise ValueError(
            f"lag-{lag} phase portrait requires more than {lag} samples; got {len(values)}"
        )
    return values[:-lag], values[lag:]


def plot_phase_axis(
    ax: Any,
    lagged_values: Any,
    current_values: Any,
    *,
    color: Any,
    title: str,
    x_label: str,
    y_label: str,
    center: float,
    xscale: str,
    yscale: str,
    y_axis_side: str = "left",
) -> None:
    ax.plot(
        lagged_values,
        current_values,
        color=color,
        marker=".",
        markersize=3.0,
        linewidth=0.8,
        alpha=0.72,
        label="sample path",
    )
    ax.scatter(
        [lagged_values[0]],
        [current_values[0]],
        color=color,
        edgecolor="black",
        linewidth=0.6,
        marker="o",
        s=42,
        zorder=3,
        label="start",
    )
    ax.scatter(
        [lagged_values[-1]],
        [current_values[-1]],
        color=color,
        edgecolor="black",
        linewidth=0.6,
        marker="s",
        s=42,
        zorder=3,
        label="end",
    )
    ax.scatter(
        [center],
        [center],
        color=color,
        edgecolor="black",
        linewidth=0.7,
        marker="D",
        s=48,
        zorder=3,
        label="center",
    )
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    if xscale == "log":
        use_plain_numeric_ticks(ax.xaxis, lagged_values)
    if yscale == "log":
        use_plain_numeric_ticks(ax.yaxis, current_values)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if y_axis_side == "right":
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.tick_params(axis="y", labelright=True, labelleft=False)
    else:
        ax.yaxis.set_label_position("left")
        ax.yaxis.tick_left()
        ax.tick_params(axis="y", labelleft=True, labelright=False)
    ax.legend(loc="upper left", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(y_axis_side == "right")
    ax.spines["left"].set_visible(y_axis_side == "left")


def plot_phase_portrait(
    loader: Any,
    bulk_row: dict[str, Any],
    ref_values: Any,
    cmp_values: Any,
    ref_center: float,
    cmp_center: float,
    *,
    lag: int,
    quantity_label: str,
    title: str,
    xscale: str,
    yscale: str,
) -> None:
    np = load_numpy()
    plt = load_pyplot()
    sns = load_seaborn()

    ref_lagged, ref_current = lagged_phase_values(ref_values, lag)
    cmp_lagged, cmp_current = lagged_phase_values(cmp_values, lag)
    all_values = np.concatenate([ref_lagged, ref_current, cmp_lagged, cmp_current])
    if xscale == "log":
        validate_log_scale(all_values, "x")
    if yscale == "log":
        validate_log_scale(all_values, "y")

    current_palette = sns.color_palette()
    color_ref = current_palette[0]
    color_cmp = current_palette[1]

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12, 5.8),
        sharex=True,
        sharey=True,
        gridspec_kw={"wspace": 0.08},
    )
    x_limits = padded_limits(all_values, xscale)
    y_limits = padded_limits(all_values, yscale)
    diagonal_min = max(x_limits[0], y_limits[0])
    diagonal_max = min(x_limits[1], y_limits[1])

    for ax in axes:
        ax.set_xlim(*x_limits)
        ax.set_ylim(*y_limits)
        if diagonal_min < diagonal_max:
            ax.plot(
                [diagonal_min, diagonal_max],
                [diagonal_min, diagonal_max],
                color="0.78",
                linestyle="--",
                linewidth=1.0,
                zorder=0,
                label="y = x",
            )

    plot_phase_axis(
        axes[0],
        ref_lagged,
        ref_current,
        color=color_ref,
        title=f"Ref lag-{lag} phase portrait",
        x_label=f"lag-{lag} {quantity_label}",
        y_label=f"current {quantity_label}",
        center=ref_center,
        xscale=xscale,
        yscale=yscale,
        y_axis_side="left",
    )
    plot_phase_axis(
        axes[1],
        cmp_lagged,
        cmp_current,
        color=color_cmp,
        title=f"Cmp lag-{lag} phase portrait",
        x_label=f"lag-{lag} {quantity_label}",
        y_label=f"current {quantity_label}",
        center=cmp_center,
        xscale=xscale,
        yscale=yscale,
        y_axis_side="right",
    )

    fig.suptitle(make_title(loader, bulk_row), fontsize=14, fontweight="bold", y=0.98)
    fig.text(0.5, 0.88, title, ha="center", va="center", fontsize=11)
    fig.subplots_adjust(left=0.09, right=0.90, bottom=0.14, top=0.78)
    plt.show()


def plot_time_phase(
    loader: Any,
    bulk_row: dict[str, Any],
    *,
    lag: int,
    xscale: str,
    yscale: str,
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    ref_times = np.asarray(data["reference_samples"], dtype=np.float64)
    cmp_times = np.asarray(data["compare_samples"], dtype=np.float64)
    time_scale, time_unit = duration_scale_and_label(ref_times, cmp_times)
    plot_phase_portrait(
        loader,
        bulk_row,
        ref_times / time_scale,
        cmp_times / time_scale,
        bulk_row["reference_time"] / time_scale,
        bulk_row["compare_time"] / time_scale,
        lag=lag,
        quantity_label=f"timing [{time_unit}]",
        title="Timing lag phase portrait",
        xscale=xscale,
        yscale=yscale,
    )


def plot_cycle_phase(
    loader: Any,
    bulk_row: dict[str, Any],
    *,
    lag: int,
    xscale: str,
    yscale: str,
) -> None:
    np = load_numpy()
    data = loader.load_bulk_data(bulk_row)
    ref_cycles = compute_cycles(
        data["reference_samples"], data["reference_frequencies"], "reference"
    )
    cmp_cycles = compute_cycles(
        data["compare_samples"], data["compare_frequencies"], "compare"
    )
    cycle_scale, cycle_label = cycle_scale_and_label(ref_cycles, cmp_cycles)
    ref_cycles = ref_cycles / cycle_scale
    cmp_cycles = cmp_cycles / cycle_scale
    plot_phase_portrait(
        loader,
        bulk_row,
        ref_cycles,
        cmp_cycles,
        float(np.median(ref_cycles)),
        float(np.median(cmp_cycles)),
        lag=lag,
        quantity_label=cycle_label,
        title="Cycle lag phase portrait",
        xscale=xscale,
        yscale=yscale,
    )


def row_index(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc

    if result < 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be non-negative")

    return result


def positive_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc

    if result <= 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be positive")

    return result


def select_auto_aspect(bulk_row: dict[str, Any]) -> str:
    reason = str(bulk_row.get("reason", ""))
    aspect = AUTO_ASPECT_BY_REASON.get(reason, DEFAULT_AUTO_ASPECT)
    print(
        f"auto aspect selected {aspect!r} for reason {reason!r}",
        file=sys.stderr,
    )
    return aspect


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nvbench-bulk-visualize",
        description="Visualize rows emitted by nvbench-compare-robust --bulk-debug-python.",
    )
    parser.add_argument(
        "loader", help="Path to loader.py generated by --bulk-debug-python"
    )
    parser.add_argument("row_pos", nargs="?", type=row_index)
    parser.add_argument("--row", dest="row_opt", type=row_index)
    parser.add_argument(
        "--aspect",
        choices=[
            "auto",
            "time",
            "cycle",
            "cycles",
            "time-box",
            "cycle-box",
            "time-coverage",
            "cycle-coverage",
            "time-coverage-curve",
            "cycle-coverage-curve",
            "time-cycle",
            "time-cycles",
            "time-freq",
            "time-frequency",
            "sequence",
            "time-freq-sequence",
            "time-frequency-sequence",
            "time-cycle-sequence",
            "time-cycles-sequence",
            "time-phase",
            "time-lag",
            "cycle-phase",
            "cycles-phase",
            "cycle-lag",
            "cycles-lag",
        ],
        default="time",
        help="Distribution aspect to plot",
    )
    parser.add_argument(
        "--xscale",
        choices=["linear", "log"],
        default="linear",
        help="Scale for the x-axis",
    )
    parser.add_argument(
        "--yscale",
        choices=["linear", "log"],
        default="linear",
        help="Scale for the y-axis",
    )
    parser.add_argument(
        "--lag",
        type=positive_int,
        default=1,
        help="Lag used by lag phase-portrait aspects",
    )
    args = parser.parse_args(argv)

    if args.row_pos is None and args.row_opt is None:
        parser.error("Row selection is required, either as positional ROW or --row ROW")

    if args.row_pos is not None and args.row_opt is not None:
        parser.error(
            "Row selection may be provided either as positional ROW or --row ROW, not both"
        )

    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        loader = load_loader_module(Path(args.loader))
        num_rows = len(loader.bulk_rows)

        row = args.row_pos if args.row_opt is None else args.row_opt
        if row >= num_rows:
            raise ValueError(
                f"{row!r} must be less than {num_rows} to select a valid row"
            )

        bulk_row = loader.bulk_rows[row]
        aspect = select_auto_aspect(bulk_row) if args.aspect == "auto" else args.aspect

        if aspect == "time":
            plot_time_distribution(
                loader, bulk_row, xscale=args.xscale, yscale=args.yscale
            )
        elif aspect in {"cycle", "cycles"}:
            plot_cycle_distribution(
                loader, bulk_row, xscale=args.xscale, yscale=args.yscale
            )
        elif aspect == "time-box":
            plot_time_box(loader, bulk_row, xscale=args.xscale)
        elif aspect == "cycle-box":
            plot_cycle_box(loader, bulk_row, xscale=args.xscale)
        elif aspect == "time-coverage":
            plot_time_coverage(loader, bulk_row, xscale=args.xscale)
        elif aspect == "cycle-coverage":
            plot_cycle_coverage(loader, bulk_row, xscale=args.xscale)
        elif aspect == "time-coverage-curve":
            plot_time_coverage_curve(loader, bulk_row, xscale=args.xscale)
        elif aspect == "cycle-coverage-curve":
            plot_cycle_coverage_curve(loader, bulk_row, xscale=args.xscale)
        elif aspect in {"time-cycle", "time-cycles"}:
            plot_time_cycle_distribution(
                loader, bulk_row, xscale=args.xscale, yscale=args.yscale
            )
        elif aspect in {"time-freq", "time-frequency"}:
            plot_time_frequency_distribution(
                loader, bulk_row, xscale=args.xscale, yscale=args.yscale
            )
        elif aspect in {
            "sequence",
            "time-freq-sequence",
            "time-frequency-sequence",
        }:
            plot_time_frequency_sequence(
                loader, bulk_row, xscale=args.xscale, yscale=args.yscale
            )
        elif aspect in {"time-cycle-sequence", "time-cycles-sequence"}:
            plot_time_cycle_sequence(
                loader, bulk_row, xscale=args.xscale, yscale=args.yscale
            )
        elif aspect in {"time-phase", "time-lag"}:
            plot_time_phase(
                loader,
                bulk_row,
                lag=args.lag,
                xscale=args.xscale,
                yscale=args.yscale,
            )
        elif aspect in {"cycle-phase", "cycles-phase", "cycle-lag", "cycles-lag"}:
            plot_cycle_phase(
                loader,
                bulk_row,
                lag=args.lag,
                xscale=args.xscale,
                yscale=args.yscale,
            )
        else:
            raise ValueError(f"unhandled aspect {aspect!r}")
    except MissingToolingDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
