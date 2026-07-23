# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import importlib.util
from pathlib import Path


def load_nvbench_json_version():
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "nvbench_json" / "version.py"
    )
    spec = importlib.util.spec_from_file_location("nvbench_json_version", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


nvbench_json_version = load_nvbench_json_version()


def json_root_with_version(major, minor, patch):
    return {
        "meta": {
            "version": {
                "json": {
                    "major": major,
                    "minor": minor,
                    "patch": patch,
                    "string": f"{major}.{minor}.{patch}",
                }
            }
        }
    }


def test_reader_version_matches_current_json_schema():
    assert nvbench_json_version.file_version == (1, 1, 0)
    assert nvbench_json_version.file_version_string == "1.1.0"


def test_older_same_major_json_version_is_compatible(capsys):
    nvbench_json_version.check_file_version("old.json", json_root_with_version(1, 0, 0))

    assert capsys.readouterr().out == ""


def test_future_minor_json_version_warns(capsys):
    nvbench_json_version.check_file_version(
        "future.json", json_root_with_version(1, 2, 0)
    )

    assert "different NVBench JSON file version" in capsys.readouterr().out


def test_different_major_json_version_warns(capsys):
    nvbench_json_version.check_file_version(
        "future.json", json_root_with_version(2, 0, 0)
    )

    assert "different NVBench JSON file version" in capsys.readouterr().out
