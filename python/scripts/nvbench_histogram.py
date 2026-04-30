#!/usr/bin/env python

from collections.abc import Iterator
from typing import Any, Optional
import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

try:
    from nvbench_json import reader
except ImportError:
    from scripts.nvbench_json import reader


def parse_files():
    help_text = "%(prog)s [nvbench.out.json | dir/] ..."
    parser = argparse.ArgumentParser(prog="nvbench_histogram", usage=help_text)

    args, files_or_dirs = parser.parse_known_args()

    filenames = []
    for file_or_dir in files_or_dirs:
        if os.path.isdir(file_or_dir):
            for f in os.listdir(file_or_dir):
                if os.path.splitext(f)[1] != ".json":
                    continue
                filename = os.path.join(file_or_dir, f)
                if os.path.isfile(filename) and os.path.getsize(filename) > 0:
                    filenames.append(filename)
        else:
            filenames.append(file_or_dir)

    filenames.sort()

    if not filenames:
        parser.print_help()
        exit(0)

    return filenames


def extract_tagged(tag : str, summary : list) -> Iterator[str]:
    return filter(lambda v: v["tag"] == tag, summary)


def extract_named(name : str, summary : list) -> Iterator[str]:
    return filter(lambda v: v["name"] == name, summary)


def first_val(it : Iterator[str]) -> Any:
    return next(it)


def optional_first_val(it : Iterator[str]) -> Optional[Any]:
    v = next(it, None)
    return v


def extract_filename(summary):
    summary_data = summary["data"]
    value_data = first_val(extract_named(name="filename", summary=summary_data))
    assert value_data["type"] == "string"
    return value_data["value"]


def extract_size(summary):
    summary_data = summary["data"]
    value_data = first_val(extract_named(name="size", summary=summary_data))
    assert value_data["type"] == "int64"
    return int(value_data["value"])


def to_absolute_fn(json_fn, fn):
    # If not absolute, the path is relative to the associated .json file:
    if not os.path.isabs(fn):
        return os.path.join(os.path.dirname(json_fn), fn)
    return fn


def parse_samples_meta(json_filename, state):
    summaries = state["summaries"]
    if not summaries:
        return None, None, None

    times_summary = optional_first_val(extract_tagged(tag="nv/json/bin:nv/cold/sample_times", summary=summaries))
    if not times_summary:
        return None, None, None

    sample_times_filename = to_absolute_fn(json_filename, extract_filename(times_summary))
    sample_count = extract_size(times_summary)

    freqs_summary = optional_first_val(extract_tagged(tag="nv/json/freqs-bin:nv/cold/sample_freqs", summary=summaries))
    if not freqs_summary:
        return sample_count, sample_times_filanem, None

    sample_freqs_filename = to_absolute_fn(json_filename, extract_filename(freqs_summary))
    freqs_count = extract_size(freqs_summary)
    assert freqs_count == sample_count

    return sample_count, sample_times_filename, sample_freqs_filename


def parse_samples(filename, state):
    sample_count, times_filename, freqs_filename = parse_samples_meta(filename, state)
    if not sample_count or not times_filename:
        return []

    with open(times_filename, "rb") as f:
        time_samples = np.fromfile(f, "<f4")

    assert sample_count == len(time_samples)
    return time_samples


def to_df(data):
    return pd.DataFrame.from_dict(dict([(k, pd.Series(v)) for k, v in data.items()]))


def parse_json(filename):
    json_root = reader.read_file(filename)

    samples_data = {}

    for bench in json_root["benchmarks"]:
        print(f"""Benchmark: {bench["name"]}""")
        for state in bench["states"]:
            print(f"""State: {state["name"]}""")

            samples = parse_samples(filename, state)
            if len(samples) == 0:
                continue

            samples_data[f"""{bench["name"]} {state["name"]}"""] = samples

    return to_df(samples_data)


def main():
    filenames = parse_files()

    dfs = [parse_json(filename) for filename in filenames]
    df = pd.concat(dfs, ignore_index=True)

    sns.displot(df, rug=True, kind="kde", fill=True)
    plt.show()


if __name__ == "__main__":
    #d = {"benchmarks": [{'name': "Anne", "size": 104}, {"name" : "Jane", "size": 20}]}
    #print(first_val(extract_tagged(tag="Anne", summary=d["benchmarks"])))

    sys.exit(main())
