#!/usr/bin/env python
#
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib.image as mpimg
import matplotlib.pyplot as plt

ASSETS = ROOT / "assets"
IMAGE_DIR = ASSETS / "issue-316-legacy-misreports"
OUTPUT = ASSETS / "issue-316-legacy-fast-slow-grid.jpg"

IMAGE_URLS = [
    "https://github.com/user-attachments/assets/cf0b9081-2222-4493-a665-22f0fe691adf",
    "https://github.com/user-attachments/assets/45f2dc36-60d6-4e5b-9a9d-deccd7120bae",
    "https://github.com/user-attachments/assets/ecd43901-2a24-4db0-acef-fa94202da13e",
    "https://github.com/user-attachments/assets/2ce00606-25fe-4383-a1a7-fc7a93ace018",
    "https://github.com/user-attachments/assets/ba426c24-f15b-4ef3-a465-2de9d1f692c3",
    "https://github.com/user-attachments/assets/4815a173-2450-4193-86cf-4a5068c255d5",
    "https://github.com/user-attachments/assets/feaaacc5-c1ab-4600-b021-f3b418685c29",
    "https://github.com/user-attachments/assets/762af380-438e-465c-9566-b3380b2ddc1a",
    "https://github.com/user-attachments/assets/786e674b-6414-4ce9-b688-54c883f277a8",
    "https://github.com/user-attachments/assets/db979444-374d-4625-8c8a-ecae65232431",
    "https://github.com/user-attachments/assets/773fd319-70b8-40a7-9653-0c122097c4b4",
    "https://github.com/user-attachments/assets/77560cb4-85b3-4f95-9d9f-3bfed05f9620",
    "https://github.com/user-attachments/assets/0fbc5b4a-3ac4-48ec-88cb-d68a2257f7b4",
    "https://github.com/user-attachments/assets/9713744b-40ee-455a-9ede-af4da135aa6c",
    "https://github.com/user-attachments/assets/34ec2d30-c6c6-4966-94f6-2acaaae48c5a",
    "https://github.com/user-attachments/assets/803820ab-8327-4b19-935b-765af4beb7da",
    "https://github.com/user-attachments/assets/869461cb-f26a-4768-b8a0-9db62a4b0e18",
    "https://github.com/user-attachments/assets/fe0062c5-ecdf-4dbd-be20-fa1d800ccdbc",
    "https://github.com/user-attachments/assets/5b90bad7-5377-4c3c-83bb-8d14ddc907f7",
    "https://github.com/user-attachments/assets/2d851a12-037f-4c56-9465-a369fb0fa5e4",
    "https://github.com/user-attachments/assets/2f77170b-567b-483f-82d2-ec1eb539290b",
    "https://github.com/user-attachments/assets/89db1577-b758-4ee6-9da3-31432f60b252",
    "https://github.com/user-attachments/assets/1e4c5039-2367-4709-978f-050338f5595c",
    "https://github.com/user-attachments/assets/a4b2fe2b-5513-4983-9818-ed8ff48c2e7f",
]


def download_images() -> list[Path]:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filenames = []
    for index, url in enumerate(IMAGE_URLS, start=1):
        filename = IMAGE_DIR / f"{index:02d}.png"
        filenames.append(filename)
        if filename.exists() and filename.stat().st_size > 0:
            continue
        print(f"Downloading {filename.name}")
        urllib.request.urlretrieve(url, filename)  # noqa: S310
    return filenames


def build_grid(filenames: list[Path]) -> None:
    rows = 4
    cols = 6
    fig, axes = plt.subplots(rows, cols, figsize=(16, 9.2))
    for axis in axes.flat:
        axis.set_axis_off()

    for index, filename in enumerate(filenames):
        axis = axes.flat[index]
        image = mpimg.imread(filename)
        axis.imshow(image)
        axis.set_title(f"{index + 1}", fontsize=7, pad=1.5)

    fig.suptitle(
        "Legacy nvbench-compare: 24 FAST/SLOW reports from two runs of the same benchmark",
        fontsize=14,
        fontweight="bold",
        y=0.992,
    )
    fig.tight_layout(pad=0.06, rect=(0, 0, 1, 0.972))
    fig.savefig(OUTPUT, dpi=180, pil_kwargs={"quality": 92})
    plt.close(fig)
    print(f"Wrote {OUTPUT}")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    filenames = download_images()
    build_grid(filenames)


if __name__ == "__main__":
    main()
