"""Predict fatigue damage using the saved SHM model; no training or label reading.

Put this file in shm_work beside build_features.py, build_features_v2.py,
train_shm_shape.py and shm_shape_model.joblib. With no arguments, processes
train01.csv as a pipeline check. --input accepts a raw CSV or a directory of
raw CSVs. Output has file_id (filename including .csv) and prediction columns.
This is a local prediction utility, not the integrated submission app.
"""
from pathlib import Path
from datetime import datetime
import argparse
import sys
import joblib
import numpy as np
import pandas as pd

FOLDER = Path(__file__).resolve().parent
DEFAULT_INPUT = (FOLDER.parent / 'NebulaX-Hackathon-ProblemStatement-main'
                 / 'PS3' / '02_Datasets' / 'SHM' / 'Train' / 'train01.csv')


def load_model(path):
    """Load the user's own trained model bundle."""
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or bundle.get('model_type') != 'rainflow_ridge_cycle_shape':
        raise ValueError('Expected shm_shape_model.joblib from train_shm_shape.py.')
    if bundle.get('feature_set') != 'current_plus_shape':
        raise ValueError('Expected the current_plus_shape candidate.')
    return bundle


def predict_features(bundle, features):
    # Use exactly the same feature transformations as training.
    from train_shm_shape import predict_bundle
    predictions = np.asarray(predict_bundle(bundle, features), dtype=float)
    if predictions.shape != (len(features),) or not np.isfinite(predictions).all() or (predictions <= 0).any():
        raise ValueError('Model returned invalid damage predictions.')
    return predictions


def predict_file(file_path, bundle):
    """App entry point: pass a Path and a bundle loaded once with load_model()."""
    from build_features_v2 import extract_features_v2, load_stress
    stress = load_stress(Path(file_path))
    if len(stress) != 581120:
        print(f'Note: {Path(file_path).name} has {len(stress)} readings; training recordings had 581120. '
              'Accuracy for other lengths has not been established.', file=sys.stderr)
    features = pd.DataFrame([extract_features_v2(stress)])
    return float(predict_features(bundle, features)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT,
                        help='Raw CSV or folder of raw CSVs. Default: training example train01.csv.')
    parser.add_argument('--model', type=Path, default=FOLDER / 'shm_shape_model.joblib')
    parser.add_argument('--output', type=Path, default=None,
                        help='New output CSV; existing files are never overwritten.')
    args = parser.parse_args()
    output = args.output or FOLDER / 'predictions' / ('shm_predictions_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.csv')
    if output.exists():
        raise FileExistsError(f'Output already exists; choose another name: {output}')
    if args.input.is_dir():
        files = sorted(p for p in args.input.iterdir() if p.is_file() and p.suffix.lower() == '.csv')
    elif args.input.is_file() and args.input.suffix.lower() == '.csv':
        files = [args.input]
    else:
        raise FileNotFoundError(f'Input CSV or folder not found: {args.input}')
    if not files:
        raise ValueError('No CSV recordings found.')
    if output.resolve() in {p.resolve() for p in files} or output.resolve() == args.model.resolve():
        raise ValueError('Output must be separate from input recordings and the model.')
    bundle = load_model(args.model)
    print(f'Loaded saved model. Predicting {len(files)} recording(s); no training.')
    rows = []
    for i, path in enumerate(files, 1):
        print(f'[{i}/{len(files)}] Reading {path.name} and extracting features...', flush=True)
        try:
            value = predict_file(path, bundle)
        except Exception as error:
            raise RuntimeError(f'{path.name}: {error}. No prediction CSV was written.') from error
        rows.append({'file_id': path.name, 'prediction': value})
        print(f'  Predicted fatigue damage: {value:.9f}')
    table = pd.DataFrame(rows, columns=['file_id', 'prediction'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', newline='', encoding='utf-8') as handle:
        table.to_csv(handle, index=False)
    print(f'\nSaved: {output.resolve()}')
    print('No damage labels were read. These are predictions, not measured accuracy.')
    if args.input.resolve() == DEFAULT_INPUT.resolve():
        print('train01.csv was used for training. This run checks the pipeline only.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'\nPrediction failed: {error}', file=sys.stderr)
        sys.exit(1)
