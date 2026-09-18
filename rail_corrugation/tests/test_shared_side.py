import numpy as np
import pandas as pd
from sklearn.base import clone
from rail_cdm.shared_side import SharedSideClassifier, exchange_sides
from rail_cdm.train import make_production_model

def test_selected_configuration():
    model=clone(make_production_model())
    assert model.feature_count==20
    assert model.threshold==0.40

def test_exchange_and_input_unchanged():
    x=pd.DataFrame({'side1_rms':[2.0], 'side2_rms':[4.0],
                    'rms_side1_minus_side2':[-2.0], 'rms_side1_over_side2':[2/(4+1e-12)]})
    original=x.copy(deep=True)
    z=exchange_sides(x)
    assert z.side1_rms.iloc[0]==4
    assert z.rms_side1_minus_side2.iloc[0]==2
    assert z.rms_side1_over_side2.iloc[0]==4/(2+1e-12)
    pd.testing.assert_frame_equal(x,original)
    pd.testing.assert_frame_equal(exchange_sides(z),x)

def test_threshold_not_normalized_argmax():
    model=SharedSideClassifier()
    model.classes_=np.array(['Normal','Side I','Side II'])
    model.side_scores=lambda x:np.array([[.39,.1],[.40,.1],[.1,.7]])
    assert model.predict(None).tolist()==['Normal','Side I','Side II']
    assert model.predict_proba(None)[1].argmax()==0
    np.testing.assert_allclose(model.predict_proba(None).sum(axis=1),1)

def test_fit_and_serialization(tmp_path):
    import joblib
    rng=np.random.default_rng(42)
    x=pd.DataFrame({'side1_x':rng.normal(size=30),'side2_x':rng.normal(size=30)})
    y=np.array(['Normal','Side I','Side II']*10)
    model=SharedSideClassifier(feature_count=2).fit(x,y)
    assert model.estimator_[-1].n_estimators==400
    path=tmp_path/'model.joblib';joblib.dump(model,path)
    np.testing.assert_array_equal(model.predict(x),joblib.load(path).predict(x))
