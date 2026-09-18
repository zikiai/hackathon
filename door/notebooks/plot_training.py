"""Plot only Door training data. No model fitting or test-data access."""
from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COLORS = {"Normal": "#2878b5", "Abnormal resistance": "#d95f02"}
SIGNALS = ["Motor current(mA)", "Motor Voltage(10mV)", "Door leaf position"]


def timestamp(value):
    """Parse the organiser's seven-field timestamp, including milliseconds."""
    year, month, day, hour, minute, second, ms = map(int, value.split("-"))
    return pd.Timestamp(year, month, day, hour, minute, second) + pd.Timedelta(milliseconds=ms)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/training_plots")
    args = parser.parse_args()
    # Deliberately name the two training files; never scan or load other CSVs.
    data = pd.read_csv(args.raw_dir / "Train.csv")
    labels = pd.read_csv(args.raw_dir / "Train_Segments_Answer.csv")
    data["time"] = data["Datetime"].map(timestamp)
    for name in ["start_time", "end_time"]:
        labels[name] = labels[name].map(timestamp)
    if not data.time.is_monotonic_increasing or data.time.duplicated().any():
        raise ValueError("Training timestamps must be unique and increasing.")
    if not set(labels.status).issubset(COLORS):
        raise ValueError("Unexpected training label.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})
    origin = data.time.iloc[0]
    handles = [Patch(color=color, alpha=.3, label=status) for status, color in COLORS.items()]
    features = []
    segments = []
    for row in labels.itertuples(index=False):
        part = data.loc[data.time.between(row.start_time, row.end_time)].copy()
        if len(part) != row.n_rows or part.empty:
            raise ValueError(f"{row.segment_id}: labelled row count does not match data.")
        segments.append((row, part))
        features.append({"segment_id": row.segment_id, "operation": row.operation,
                         "status": row.status,
                         "duration_s": (row.end_time-row.start_time).total_seconds(),
                         "peak_abs_current_mA": part["Motor current(mA)"].abs().max(),
                         "mean_abs_current_mA": part["Motor current(mA)"].abs().mean()})

    fig, axes = plt.subplots(3, 1, figsize=(15, 9), sharex=True)
    # Draw each labelled segment separately to avoid lines across recording gaps.
    for row, part in segments:
        x = (part.time-origin).dt.total_seconds()
        for ax, signal in zip(axes, SIGNALS):
            ax.plot(x, part[signal], color=COLORS[row.status], lw=.8)
            ax.axvspan((row.start_time-origin).total_seconds(),
                       (row.end_time-origin).total_seconds(), color=COLORS[row.status], alpha=.08)
    for ax, signal in zip(axes, SIGNALS):
        ax.set_ylabel(signal)
        ax.grid(alpha=.2)
    axes[0].legend(handles=handles, loc="upper right")
    axes[-1].set_xlabel("Seconds from start of training recording")
    fig.suptitle("Training recording — supplied labels (not model predictions)")
    fig.tight_layout()
    fig.savefig(args.output_dir / "01_training_overview.png", dpi=160)
    plt.close(fig)

    # First example in each group: reproducible selection, not cherry-picked.
    fig, axes = plt.subplots(3, 4, figsize=(17, 10), squeeze=False)
    groups = [(op, status) for op in ["Open", "Close"] for status in COLORS]
    for j, (op, status) in enumerate(groups):
        example = next(((r, p) for r, p in segments if r.operation == op and r.status == status), None)
        if example is None:
            axes[0, j].set_title(f"{op}: {status}\nNo examples")
            continue
        row, part = example
        for i, signal in enumerate(SIGNALS):
            axes[i, j].plot((part.time-row.start_time).dt.total_seconds(), part[signal], color=COLORS[status])
            axes[i, j].grid(alpha=.2)
            axes[i, j].set_ylabel(signal)
        axes[0, j].set_title(f"{op}: {status}\n{row.segment_id}", fontsize=10)
        axes[-1, j].set_xlabel("Seconds within movement")
    # Common scales within each signal make comparisons honest.
    for i in range(3):
        low = min(ax.get_ylim()[0] for ax in axes[i])
        high = max(ax.get_ylim()[1] for ax in axes[i])
        for ax in axes[i]:
            ax.set_ylim(low, high)
    fig.suptitle("First labelled example per group — examples, not proof of separation")
    fig.tight_layout()
    fig.savefig(args.output_dir / "02_example_movements.png", dpi=160)
    plt.close(fig)

    table = pd.DataFrame(features)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, feature in zip(axes, ["duration_s", "peak_abs_current_mA", "mean_abs_current_mA"]):
        values = [table.loc[(table.operation == op) & (table.status == status), feature].to_numpy()
                  for op, status in groups]
        boxes = ax.boxplot(values, patch_artist=True)
        for box, (_, status) in zip(boxes["boxes"], groups):
            box.set_facecolor(COLORS[status]); box.set_alpha(.5)
        ax.set_xticks(range(1, 5), [f"{op}\n{'Normal' if status == 'Normal' else 'Abnormal'}\nn={len(v)}"
                                  for (op, status), v in zip(groups, values)], fontsize=8)
        ax.set_title(feature)
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Descriptive training comparisons — not validation results")
    fig.tight_layout()
    fig.savefig(args.output_dir / "03_feature_comparisons.png", dpi=160)
    plt.close(fig)
    table.to_csv(args.output_dir / "movement_summary.csv", index=False)
    summary = {"sensor_rows": len(data), "movements": len(labels),
               "label_counts": labels.status.value_counts().to_dict(),
               "missing_values": data.drop(columns="time").isna().sum().to_dict()}
    (args.output_dir / "data_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Saved three plots and two summaries to {args.output_dir}")


if __name__ == "__main__":
    main()
