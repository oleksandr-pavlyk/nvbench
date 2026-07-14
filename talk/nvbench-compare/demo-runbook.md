# nvbench-compare Demo Runbook

This runbook assumes commands are executed from the repository root:

```bash
cd /home/opavlyk/repos/nvbench
```

Use repo-local scripts for the demo so the behavior matches the branch:

```bash
NVCMP="python python/scripts/nvbench_compare.py"
NVCMP_LEGACY="python python/scripts/nvbench_compare_legacy.py"
REF="demo/main.json"
CMP="demo/pdl1.json"
```

If `nvbench-compare` is installed from this branch, the same commands can use
`nvbench-compare` and `nvbench-compare-legacy` instead.

## Preflight

Rebuild the deck after visual or Markdown edits:

```bash
cd talk/nvbench-compare
npm run slides:html
cd ../..
```

Smoke-test the main demo inputs:

```bash
$NVCMP "$REF" "$CMP" --no-color
```

Expected shape:

- benchmark `base`;
- 14 total matches;
- mix of SAME, FAST, and AMBG;
- AMBG reason group includes `bulk_time_support_mismatch`.

## Primary Demo Path

### 1. Show Default Output

```bash
$NVCMP -b base -a 'T{ct}=I8' "$REF" "$CMP" --no-color
```

Talking points:

- This uses benchmark and axis filtering to keep the output small.
- One row is SAME, one row is AMBG.
- `Change` is blank for SAME and AMBG.
- Summary groups the AMBG reason:
  `bulk_time_support_mismatch`.

### 2. Contrast With Legacy Comparator

```bash
$NVCMP_LEGACY -b base -a 'T{ct}=I8' "$REF" "$CMP" --no-color
```

Expected shape:

- same two rows;
- legacy reports one FAST and one SLOW.

Talking point:

- This is the core motivation: the old mean/stdev rule can turn a rerun into
  actionable-looking FAST/SLOW findings.

### 3. Show Legacy Table View Is Not Legacy Semantics

```bash
$NVCMP -b base -a 'T{ct}=I8' "$REF" "$CMP" --display legacy --no-color
```

Talking points:

- The columns look familiar.
- The decision logic remains the new decision tree.
- `Ref Noise` / `Cmp Noise` are selected noise values, often robust IQR-based
  when robust summaries are available.

### 4. Show Explain Mode

```bash
$NVCMP -b base -a 'T{ct}=I32' "$REF" "$CMP" --display explain --no-color
```

Expected shape:

- one FAST row with reason `bc-gap`;
- one AMBG row with reason `bt-sup-miss`;
- summary includes a reason legend.

Talking points:

- Explain mode exposes the specific decision check.
- `bc-gap` means timing clear gap was confirmed by bulk cycles.
- `bt-sup-miss` means bulk timing support coverage did not support SAME.

### 5. Show Full Summary Once

```bash
$NVCMP "$REF" "$CMP" --no-color
```

Talking points:

- FAST/SLOW are counted as Improvement/Regression.
- AMBG rows are grouped by reason.
- Reason detail is a representative worst-severity case.

## Optional Branches

### Bulk Debug Python

Skip this if short on time. It is useful if someone asks how to inspect the raw
sidecars for one row.

```bash
loader="$(mktemp "${TMPDIR:-/tmp}/nvbench-bulk-debug.XXXXXX.py")"
$NVCMP -b base -a 'T{ct}=I8' "$REF" "$CMP" --bulk-debug-python "$loader" --no-color
python -i "$loader"
```

Inside Python:

```python
len(bulk_rows)
bulk_rows[1]["status"], bulk_rows[1]["reason"]
bulk_rows[1]["reference_sample_filename"]
ref_samples, cmp_samples = load_samples(bulk_rows[1])
ref_samples[:10], cmp_samples[:10]
```

### Config / Presets

```bash
$NVCMP --dump-config
$NVCMP --preset permissive --dump-config
$NVCMP --preset permissive -b base -a 'T{ct}=I8' "$REF" "$CMP" --no-color
```

Talking points:

- Presets are starting points, not calibrated policy.
- TOML config documents decision knobs and allows local tuning.

### Device Filtering

Use this as a CLI capability demonstration rather than a semantic comparison:

```bash
$NVCMP \
  --reference-devices 0 \
  --compare-devices 0 \
  -b base -a 'T{ct}=I8' \
  "$REF" "$CMP" --no-color
```

Talking points:

- Explicit device filters allow comparing files collected with different device
  sets.
- Filtered reference and compare device lists are paired positionally.

### Collection Settings

Do not run this live unless the benchmark is already built and expected to
finish quickly. Use as a talking point:

```bash
./benchmark \
  -d 0 \
  --cold-warmup-runs 16 \
  --cold-max-warmup-walltime 5 \
  --stopping-criterion entropy \
  --jsonbin perf_data/run1.json
```

Practical guidance:

- Use `--jsonbin` when rows may need bulk-data diagnosis.
- Increase `--cold-warmup-runs` when cold-start effects dominate.
- Use `--cold-max-warmup-walltime` to cap warmup cost.
- Consider `--stopping-criterion entropy` or `sample-count` when the default
  stopping behavior is not producing stable enough samples.

## Short Path If Time Is Tight

Use only these commands:

```bash
$NVCMP -b base -a 'T{ct}=I8' "$REF" "$CMP" --no-color
$NVCMP_LEGACY -b base -a 'T{ct}=I8' "$REF" "$CMP" --no-color
$NVCMP -b base -a 'T{ct}=I32' "$REF" "$CMP" --display explain --no-color
```

This still demonstrates:

- modern SAME/AMBG behavior;
- legacy FAST/SLOW overclaiming;
- reason codes and summary legend.

## Failure Fallbacks

If optional dependencies are missing:

```bash
python -m pip install numpy tabulate colorama jsondiff
```

If the terminal output is too wide:

```bash
$NVCMP -b base -a 'T{ct}=I32' "$REF" "$CMP" --display explain --no-color
```

If demo data paths fail, verify:

```bash
ls demo/main.json demo/pdl1.json
ls demo/main.json-bin demo/pdl1.json-bin
ls demo/main.json-freqs-bin demo/pdl1.json-freqs-bin
```
