from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kurtosis

SAMPLE_RATE_HZ = 10_000
FEATURE_VERSION = 1
FREQUENCY_BANDS_HZ = (
    (0, 50),
    (50, 100),
    (100, 250),
    (250, 500),
    (500, 1_000),
    (1_000, 2_500),
    (2_500, 5_001),
)


def _summarize_channels(prefix: str, values: np.ndarray) -> dict[str, float]:
    """Summarize a group of sensor channels without cancelling signed signals."""
    rms = np.sqrt(np.mean(np.square(values), axis=0))
    std = np.std(values, axis=0)
    peak = np.max(np.abs(values), axis=0)
    channel_kurtosis = np.nan_to_num(kurtosis(values, axis=0, fisher=False), nan=0.0)

    summaries: dict[str, float] = {}
    channel_metrics = {
        "rms": rms,
        "std": std,
        "peak": peak,
        "kurtosis": channel_kurtosis,
    }
    for metric_name, metric_values in channel_metrics.items():
        summaries[f"{prefix}_{metric_name}_mean"] = float(np.mean(metric_values))
        summaries[f"{prefix}_{metric_name}_median"] = float(np.median(metric_values))
        summaries[f"{prefix}_{metric_name}_max"] = float(np.max(metric_values))
        summaries[f"{prefix}_{metric_name}_spread"] = float(np.std(metric_values))

    centered = values - np.mean(values, axis=0, keepdims=True)
    spectrum_power = np.abs(np.fft.rfft(centered, axis=0)) ** 2
    frequencies = np.fft.rfftfreq(values.shape[0], d=1 / SAMPLE_RATE_HZ)
    total_power = np.sum(spectrum_power, axis=0) + 1e-12

    for low, high in FREQUENCY_BANDS_HZ:
        mask = (frequencies >= low) & (frequencies < high)
        band_fraction = np.sum(spectrum_power[mask], axis=0) / total_power
        band_name = f"band_{low}_{high}hz"
        summaries[f"{prefix}_{band_name}_mean"] = float(np.mean(band_fraction))
        summaries[f"{prefix}_{band_name}_max"] = float(np.max(band_fraction))
    return summaries


def extract_features(frame: pd.DataFrame) -> dict[str, float]:
    """Convert one 129-column, one-second recording into model features.

    Sensor columns alternate vibration and shock. Within each car, odd positions
    belong to Side I and even positions belong to Side II.
    """
    values = frame.to_numpy(dtype=np.float64)
    speed = values[:, 0]
    sensor_values = values[:, 1:]

    features: dict[str, float] = {
        "n_rows": float(len(frame)),
        "speed_mean": float(np.mean(speed)),
        "speed_std": float(np.std(speed)),
        "speed_transition_rate": float(np.mean(np.diff(speed) != 0)) if len(speed) > 1 else 0.0,
    }

    groups: dict[tuple[str, str], list[int]] = {
        ("side1", "vibration"): [],
        ("side1", "shock"): [],
        ("side2", "vibration"): [],
        ("side2", "shock"): [],
    }
    for sensor_column in range(sensor_values.shape[1]):
        position = (sensor_column // 2) % 8 + 1
        side = "side1" if position % 2 == 1 else "side2"
        signal_type = "vibration" if sensor_column % 2 == 0 else "shock"
        groups[(side, signal_type)].append(sensor_column)

    for (side, signal_type), indices in groups.items():
        features.update(_summarize_channels(f"{side}_{signal_type}", sensor_values[:, indices]))

    comparison_metrics = ("rms_mean", "std_mean", "peak_mean", "kurtosis_mean")
    for signal_type in ("vibration", "shock"):
        for metric in comparison_metrics:
            side1 = features[f"side1_{signal_type}_{metric}"]
            side2 = features[f"side2_{signal_type}_{metric}"]
            name = f"{signal_type}_{metric}"
            features[f"{name}_side1_minus_side2"] = side1 - side2
            features[f"{name}_side1_over_side2"] = side1 / (side2 + 1e-12)

    return features


def extract_cross_car_consensus_features(frame: pd.DataFrame) -> dict[str, float]:
    """Describe whether the same rail side is consistently stronger across cars."""
    sensor_values = frame.to_numpy(dtype=np.float64)[:, 1:]
    signals = sensor_values.reshape(len(frame), 8, 8, 2)
    features: dict[str, float] = {}

    for signal_index, signal_name in enumerate(("vibration", "shock")):
        signal = signals[:, :, :, signal_index]
        channel_metrics = {
            "rms": np.sqrt(np.mean(np.square(signal), axis=0)),
            "peak": np.max(np.abs(signal), axis=0),
        }
        for metric_name, metric in channel_metrics.items():
            side1 = np.mean(metric[:, [0, 2, 4, 6]], axis=1)
            side2 = np.mean(metric[:, [1, 3, 5, 7]], axis=1)
            difference = side1 - side2
            relative_difference = difference / ((side1 + side2) / 2 + 1e-12)
            for comparison_name, per_car_values in (
                ("difference", difference),
                ("relative_difference", relative_difference),
            ):
                prefix = f"car_consensus_{signal_name}_{metric_name}_{comparison_name}"
                features[f"{prefix}_median"] = float(np.median(per_car_values))
                features[f"{prefix}_spread"] = float(np.std(per_car_values))
                features[f"{prefix}_positive_fraction"] = float(
                    np.mean(per_car_values > 0)
                )
    return features


def extract_car_feature_rows(frame: pd.DataFrame) -> list[dict[str, float]]:
    """Preserve each car as one instance while comparing both rail sides."""
    sensor_values = frame.to_numpy(dtype=np.float64)[:, 1:]
    signals = sensor_values.reshape(len(frame), 8, 8, 2)
    rows: list[dict[str, float]] = []

    for car_index in range(8):
        row: dict[str, float] = {"car_index": float(car_index + 1)}
        for signal_index, signal_name in enumerate(("vibration", "shock")):
            signal = signals[:, car_index, :, signal_index]
            channel_metrics = {
                "rms": np.sqrt(np.mean(np.square(signal), axis=0)),
                "peak": np.max(np.abs(signal), axis=0),
            }
            for metric_name, metric in channel_metrics.items():
                side_means: dict[str, float] = {}
                for side_name, positions in (
                    ("side1", [0, 2, 4, 6]),
                    ("side2", [1, 3, 5, 7]),
                ):
                    values = metric[positions]
                    prefix = f"{signal_name}_{metric_name}_{side_name}"
                    row[f"{prefix}_mean"] = float(np.mean(values))
                    row[f"{prefix}_median"] = float(np.median(values))
                    row[f"{prefix}_max"] = float(np.max(values))
                    row[f"{prefix}_spread"] = float(np.std(values))
                    side_means[side_name] = float(np.mean(values))
                comparison = f"{signal_name}_{metric_name}"
                row[f"{comparison}_side1_minus_side2"] = (
                    side_means["side1"] - side_means["side2"]
                )
                row[f"{comparison}_side1_over_side2"] = side_means["side1"] / (
                    side_means["side2"] + 1e-12
                )
        rows.append(row)
    return rows


def extract_periodicity_features(frame: pd.DataFrame) -> dict[str, float]:
    """Measure repeating vibration energy without assuming a rotating-speed unit."""
    sensor_values = frame.to_numpy(dtype=np.float64)[:, 1:]
    frequencies = np.fft.rfftfreq(len(frame), d=1 / SAMPLE_RATE_HZ)
    usable_frequency = (frequencies >= 20) & (frequencies <= 2_500)
    usable_values = frequencies[usable_frequency]
    features: dict[str, float] = {}
    metric_by_side: dict[str, dict[str, float]] = {}

    for side_name, positions in (
        ("side1", {1, 3, 5, 7}),
        ("side2", {2, 4, 6, 8}),
    ):
        indices = [
            sensor_column
            for sensor_column in range(sensor_values.shape[1])
            if sensor_column % 2 == 0
            and ((sensor_column // 2) % 8 + 1) in positions
        ]
        vibration = sensor_values[:, indices]
        centered = vibration - np.mean(vibration, axis=0, keepdims=True)
        power = np.abs(np.fft.rfft(centered, axis=0)) ** 2
        usable_power = power[usable_frequency]
        total_power = np.sum(usable_power, axis=0) + 1e-12
        normalized_power = usable_power / total_power
        dominant_indices = np.argmax(usable_power, axis=0)
        dominant_frequency = usable_values[dominant_indices]
        spectral_centroid = np.sum(usable_values[:, None] * normalized_power, axis=0)
        spectral_entropy = -np.sum(
            normalized_power * np.log(normalized_power + 1e-12), axis=0
        ) / np.log(len(usable_values))
        peak_concentration = np.max(normalized_power, axis=0)

        harmonic_concentration = np.zeros(len(indices), dtype=float)
        for channel_index, fundamental in enumerate(dominant_frequency):
            harmonic_mask = np.zeros(len(usable_values), dtype=bool)
            for multiple in (2, 3):
                harmonic = fundamental * multiple
                harmonic_mask |= np.abs(usable_values - harmonic) <= 2
            harmonic_concentration[channel_index] = np.sum(
                normalized_power[harmonic_mask, channel_index]
            )

        side_metrics = {
            "dominant_frequency": dominant_frequency,
            "spectral_centroid": spectral_centroid,
            "spectral_entropy": spectral_entropy,
            "peak_concentration": peak_concentration,
            "harmonic_concentration": harmonic_concentration,
        }
        metric_by_side[side_name] = {}
        for metric_name, values in side_metrics.items():
            median = float(np.median(values))
            spread = float(np.std(values))
            features[f"periodicity_{side_name}_{metric_name}_median"] = median
            features[f"periodicity_{side_name}_{metric_name}_spread"] = spread
            metric_by_side[side_name][metric_name] = median

    for metric_name in metric_by_side["side1"]:
        side1 = metric_by_side["side1"][metric_name]
        side2 = metric_by_side["side2"][metric_name]
        prefix = f"periodicity_{metric_name}"
        features[f"{prefix}_side1_minus_side2"] = side1 - side2
        features[f"{prefix}_side1_over_side2"] = side1 / (side2 + 1e-12)
    return features


def extract_feature_table(paths: list, *, progress: bool = True) -> pd.DataFrame:
    from rail_cdm.io import read_sensor_csv

    rows: list[dict[str, float | str]] = []
    total = len(paths)
    for number, path in enumerate(paths, start=1):
        if progress:
            print(f"[{number:>3}/{total}] Extracting {path.name}")
        rows.append({"filename": path.name, **extract_features(read_sensor_csv(path))})
    return pd.DataFrame(rows)
