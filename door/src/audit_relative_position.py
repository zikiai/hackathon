"""Training-only experiment with relative-travel features and fixed audit settings.

This feature-design experiment follows unlabelled-test inspection. Its validation
is exploratory, not an untouched independent estimate. No test file is read.
"""
from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import audit_robustness as audit


def relative_position_features(p):
    t=(p.time-p.time.iloc[0]).dt.total_seconds().to_numpy()
    pos=p['Door leaf position'].to_numpy(float)
    travel=pos[-1]-pos[0]
    if abs(travel)<1:
        raise ValueError('Relative-travel features require a nonzero net movement')
    # Only position is expressed relatively; current/power amplitudes stay physical.
    progress=(pos-pos[0])/travel
    smooth=pd.Series(pos).rolling(5,center=True,min_periods=1).median().to_numpy()
    speed=np.gradient(smooth,t)
    direction=1 if travel>0 else -1
    current=np.abs(p['Motor current(mA)'].to_numpy(float))*.001
    power=p['Motor current(mA)'].to_numpy(float)*.001*p['Motor Voltage(10mV)'].to_numpy(float)*.01
    out={}
    edges=np.linspace(.05,.95,6)
    for k,(lo,hi) in enumerate(zip(edges[:-1],edges[1:])):
        mask=(progress>=lo)&(progress<hi)
        for name,signal in [('current',current),('power',power),('speed',speed*direction)]:
            out[f'position_{k}_{name}']=float(np.mean(signal[mask])) if mask.any() else np.nan
    stationary=np.abs(speed)<1
    out['stationary_fraction']=float(stationary.mean())
    out['stationary_current']=float(current[stationary].mean()) if stationary.any() else 0.
    out['reverse_fraction']=float((speed*direction < -1).mean())
    # Original baseline retains raw duration and signed displacement.
    return out


def main():
    # Reuse the exact audit machinery; swap only the declared feature function.
    if '--output-dir' not in sys.argv:
        sys.argv.extend(['--output-dir', str(Path(audit.__file__).resolve().parents[1]/'outputs/relative_position_audit')])
    audit.position_features=relative_position_features
    audit.main()
    output=Path(sys.argv[sys.argv.index('--output-dir')+1])
    record=json.loads((output/'audit.json').read_text())
    record['notes']=[n for n in record['notes'] if not n.startswith('Position bins use')]
    record['notes'].extend(['Position bins use 5–95% of signed start-to-end travel; raw duration and displacement retained.', 'Feature-design experiment follows unlabelled test inspection; no test is read in this run.'])
    (output/'audit.json').write_text(json.dumps(record,indent=2))


if __name__=='__main__':main()
