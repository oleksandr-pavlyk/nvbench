# nvbench-compare Presentation Roadmap

## Working Format

Use a source-controlled, text-first deck. Markdown plus Marp gives enough
structure for slides while keeping the material easy to review, diff, and
rewrite.

Recommended folder layout:

- `slides.md`: deck body.
- `theme.css`: NVIDIA-inspired Marp theme.
- `assets/`: generated plots, diagrams, and screenshots.
- `scripts/`: reproducible visual-generation scripts.
- `roadmap.md`: outline and narrative notes.

## Why Markdown First

Markdown is the easiest format for iterative help:

- outline and narrative changes are small diffs;
- generated visuals can be scripted and regenerated;
- examples can be copied from command output without fighting PowerPoint;
- the final deck can later be recreated in an official PowerPoint template if
  needed.

## Styling Direction

Markdown itself has no presentation styling. The renderer supplies that. This
deck uses Marp with a custom CSS theme:

- black title slides;
- NVIDIA green accent color;
- restrained white content slides;
- compact tables;
- high-contrast code blocks and callouts.

The theme is NVIDIA-inspired, not an official corporate template.

## Suggested Deck Story

1. **Problem**
   Explain why mean/stdev summaries are too weak for repeated GPU benchmark
   timing data.

2. **Observed Data**
   Show problematic datasets: repeated timing values, multimodal timings,
   frequency-dependent behavior, and degenerate robust intervals.

3. **Legacy Behavior**
   Explain the old mean/stdev comparison rule and why it is still useful as a
   transitional baseline.

4. **Timing Model**
   Treat timing data as intervals or fuzzy estimates rather than exact points.

5. **Decision Tree**
   Walk through UNKNOWN, AMBG, SAME, FAST, and SLOW decisions.

6. **Bulk Data**
   Explain why `--jsonbin` changes what can be decided.

7. **Coverage Metric**
   Build intuition for nearest-neighbor support/sample coverage.

8. **Interpreting Output**
   Show `--display intervals`, `--display explain`, reason codes, and summary
   diagnostics.

9. **Debug Workflow**
   Explain `--bulk-debug-python` and how a developer inspects rows manually.

10. **Configuration**
    Show presets, TOML config, `--dump-config`, and the decision knobs.

11. **Adoption Plan**
    Discuss the legacy script, threshold calibration, and follow-up work.

## Canonical Examples To Collect

- One clean SAME row.
- One clear FAST or SLOW row.
- One AMBG caused by overlapping intervals.
- One AMBG caused by bulk support mismatch.
- One row with degenerate robust interval output.
- One legacy-vs-new comparison showing why the new logic matters.

## Visuals To Generate

- Decision tree.
- Timing interval interpretation.
- Coverage metric on a simple one-dimensional timing axis.
- Sample-weight versus unique-support coverage.
- Bulk-debug workflow diagram.
