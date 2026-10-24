"""Independent checks of saved Week 2 artifacts against the source CSVs."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd

root=Path(__file__).parent
data=root/'data'; results=root/'results'
summary=json.loads((results/'audit_summary.json').read_text())
params=json.loads((results/'preprocessing_parameters.json').read_text())
manifest=json.loads((data/'source_manifest.json').read_text())
for entry in manifest['files']:
    assert hashlib.sha256((data/entry['file']).read_bytes()).hexdigest()==entry['sha256']
orders=pd.read_csv(data/'olist_orders_dataset.csv')
master=pd.read_csv(results/'orders_audit.csv')
X=pd.read_csv(results/'prepared_features.csv')
labels=pd.read_csv(results/'feature_index_and_labels.csv')
assert len(master)==len(orders)==99441
assert master.order_id.is_unique
assert len(labels)==len(X)==86484 and X.shape[1]==54
assert labels.order_id.is_unique
assert np.isfinite(X.to_numpy()).all()
for feature in ['customer_state','approval_weekday']:
    assert X.filter(regex='^'+feature+'__').sum(axis=1).eq(1).all()
joined=labels[['order_id','split']].merge(master,on='order_id',validate='one_to_one',suffixes=('', '_master'))
train=labels.split.eq('train')
for feature in params['numeric']:
    expected_median=joined.loc[train,feature].median()
    assert np.isclose(expected_median,params['numeric'][feature]['median'])
    raw=joined[feature].fillna(expected_median)
    z=np.log1p(raw) if params['numeric'][feature]['transform']=='log1p' else raw
    expected=(z-params['numeric'][feature]['min'])/params['numeric'][feature]['denominator']
    assert np.allclose(expected,X[feature+'_scaled'])
    assert np.array_equal(joined[feature].isna().astype(int),X[feature+'_missing'])
actual=pd.to_datetime(orders.order_delivered_customer_date,format='%Y-%m-%d %H:%M:%S')
promise=pd.to_datetime(orders.order_estimated_delivery_date,format='%Y-%m-%d %H:%M:%S')
buy=pd.to_datetime(orders.order_purchase_timestamp,format='%Y-%m-%d %H:%M:%S')
eligible=(orders.order_status.eq('delivered') & actual.notna() & promise.notna() & actual.ge(buy))
on_time=int(actual.loc[eligible].dt.normalize().le(promise.loc[eligible].dt.normalize()).sum())
assert on_time==summary['service_snapshot']['on_time_orders']==89936
assert eligible.sum()==96470
assert len(master)-len(X)==12957
e=summary['feature_exclusions']
assert sum(e.values())==12957
result={'status':'passed','checks':['source hashes match manifest','master grain and row conservation',
    'feature and label row alignment','all feature values finite','one-hot category validity',
    'independently recomputed training medians','independently reconstructed transformations',
    'missing indicators match raw-derived missingness','independently recomputed on-time numerator',
    'cohort exclusion reconciliation']}
(results/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
