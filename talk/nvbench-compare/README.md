# nvbench-compare Presentation

This folder contains a Marp-based slide deck for presenting the
`nvbench-compare` work.

## Setup

Node.js is needed to render slides from markdown. I used conda environment to install it:

```
conda install nodejs
```

Install the slide renderer:

```bash
cd talk/nvbench-compare
npm install
```

Install Python packages used to generate figures:

```bash
cd talk/nvbench-compare
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If you already work from a Python environment with `numpy` and `matplotlib`,
the virtual environment is optional.

## Generate Visuals

```bash
cd talk/nvbench-compare
python scripts/generate_visuals.py
```

This writes SVG assets under `assets/`.

The current decision-tree slide uses a separate v2 diagram:

```bash
cd talk/nvbench-compare
python scripts/generate_decision_tree_v2.py
```

To download the issue #316 histogram/KDE attachments and build the legacy
FAST/SLOW grid:

```bash
cd talk/nvbench-compare
python scripts/build_issue_316_grid.py
```

## Build Slides

Generate HTML:

```bash
cd talk/nvbench-compare
npm run slides:html
```

Generate PDF:

```bash
cd talk/nvbench-compare
npm run slides:pdf
```

For quick iteration without installing locally, you can also run:

```bash
npx @marp-team/marp-cli slides.md --theme theme.css --html --preview
```
