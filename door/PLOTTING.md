# Plot the Door training data

From the repository root:

```bash
python3 -m pip install -r door/requirements-plots.txt
python3 door/notebooks/plot_training.py
```

The script reads only `Train.csv` and `Train_Segments_Answer.csv` from
`door/data/raw/`. It does not read test data or train a model.

Results appear in `door/outputs/training_plots/`:

- `01_training_overview.png`: current, voltage, and position over the recording,
  coloured using the supplied ground-truth labels. Gaps are not joined by lines.
- `02_example_movements.png`: the first normal and abnormal opening and closing
  movements, with consistent vertical scales for each signal.
- `03_feature_comparisons.png`: duration and absolute-current distributions,
  grouped by operation and status.
- `movement_summary.csv`: one row per labelled movement, with descriptive features.
- `data_summary.json`: row counts, label counts, and missing-value counts.

These are exploratory plots of labelled training data, not predictions or validation
scores. Before model tuning, reserve validation blocks; do not select features or
thresholds repeatedly using their outcomes. Voltage is shown in the original 10 mV
units. Timestamp milliseconds are parsed explicitly.

Generated plots and datasets are ignored by Git. Keep raw files unchanged.
