"""Independent verification against original order timestamps and saved predictions."""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

import joblib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data', type=Path, default=Path('data'))
parser.add_argument('--results', type=Path, default=Path('results'))
args = parser.parse_args()
D, R = args.data, args.results

def data_file(name):
    compressed = D / (name + '.csv.gz')
    return compressed if compressed.exists() else D / (name + '.csv')
S = json.loads((R / 'summary.json').read_text())
raw = pd.read_csv(data_file('olist_orders_dataset'))
for c in ['order_approved_at', 'order_delivered_customer_date', 'order_estimated_delivery_date']:
    raw[c] = pd.to_datetime(raw[c])
raw = raw.set_index('order_id')
labels = pd.read_csv(data_file('feature_index_and_labels'))
x = pd.read_csv(data_file('prepared_features'))
a = raw.loc[labels.order_id].reset_index()
y = (a.order_delivered_customer_date - a.order_approved_at).dt.total_seconds() / 86400
checks = []

def passed(name):
    checks.append(name)

def calc(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    e = predicted - actual
    return dict(n=len(e), mae_days=np.mean(abs(e)), rmse_days=np.sqrt(np.mean(e*e)),
                r2=1-np.sum(e*e)/np.sum((actual-actual.mean())**2), bias_days=e.mean(),
                median_absolute_error_days=np.median(abs(e)), p90_absolute_error_days=np.quantile(abs(e), .9))

def same_metrics(actual, predicted, row):
    for k,v in calc(actual, predicted).items():
        assert np.isclose(v, row[k], atol=1e-10), (k,v,row[k])

masks = {}
for split, start, end, cutoff in [
    ('train', None, '2018-01-01', '2018-01-01'),
    ('validation', '2018-01-01', '2018-04-01', '2018-04-01'),
    ('test', '2018-04-01', '2018-07-01', '2018-09-01')]:
    approvals = a.order_approved_at.lt(end)
    if start: approvals &= a.order_approved_at.ge(start)
    mature = approvals & a.order_approved_at.lt(pd.Timestamp(cutoff)-pd.Timedelta(days=60))
    observable = a.order_status.eq('delivered') & y.ge(0) & a.order_delivered_customer_date.lt(cutoff)
    masks[split] = mature & observable
    cohort = next(c for c in S['cohorts'] if c['split'] == split)
    assert approvals.sum() == cohort['all_approvals']
    assert mature.sum() == cohort['mature_approvals']
    assert masks[split].sum() == cohort['mature_eligible_labels']
    assert (approvals & observable).sum() == cohort['all_eligible_labels']
    passed(f'{split} cohort reconstructed from raw timestamps')

model_bundle = joblib.load(R / 'trained_model.joblib')
assert model_bundle['features'] == x.columns.tolist()
fitted = model_bundle['model']
for split, filename in [('validation','validation_predictions.csv'),('test','test_predictions.csv')]:
    saved = pd.read_csv(R / filename)
    mask = masks[split]
    assert saved.order_id.tolist() == labels.loc[mask,'order_id'].tolist()
    assert np.allclose(saved.remaining_delivery_days, y[mask], atol=1e-12)
    expected = np.maximum(fitted.predict(x.loc[mask]),0)
    assert np.allclose(saved.prediction_days, expected, atol=1e-12)
    target_metrics = S['validation_selected'] if split == 'validation' else S['test'][0]
    same_metrics(y[mask], saved.prediction_days, target_metrics)
    passed(f'{split} saved model predictions and metrics recomputed')

for i, statistic in [(1,np.median),(2,np.mean)]:
    predicted = np.full(int(masks['test'].sum()),statistic(y[masks['train']]))
    same_metrics(y[masks['test']],predicted,S['test'][i])
passed('Mean and median baseline test metrics independently recomputed')

v = pd.read_csv(R / 'validation_model_comparison.csv')
assert len(v) == 10
assert v.sort_values(['mae_days','model']).iloc[0]['model'] == S['selected_model']
assert np.isclose(v.iloc[0].mae_days,S['validation_selected']['mae_days'])
passed('Model selection minimizes recorded mature validation MAE among 10 candidates')

t = pd.read_csv(R / 'test_all_approval_predictions.csv')
assert len(t) == 20008 and t.order_id.is_unique
r = raw.loc[t.order_id].reset_index()
assert pd.to_datetime(t.order_approved_at).eq(r.order_approved_at).all()
promise = (r.order_estimated_delivery_date.dt.normalize()+pd.Timedelta(days=1)-r.order_approved_at).dt.total_seconds()/86400
actual = (r.order_delivered_customer_date-r.order_approved_at).dt.total_seconds()/86400
known = r.order_status.eq('delivered') & actual.ge(0) & r.order_delivered_customer_date.lt('2018-09-01')
late = r.order_delivered_customer_date.dt.normalize().gt(r.order_estimated_delivery_date.dt.normalize())
assert np.allclose(t.promise_days,promise)
assert t.outcome_known.eq(known).all()
assert t.loc[known,'late'].eq(late[known]).all()
assert np.allclose(t.priority_score,t.prediction_days-promise)
passed('Queue score, known outcome mask, and late labels reconstructed from raw timestamps')

q = pd.read_csv(R / 'queue_metrics.csv')
for _,row in q.iterrows():
    chosen = []
    for _,g in t.groupby('approval_day'):
        if row.policy == 'Model priority':
            g=g.sort_values(['missing_promise','priority_score','order_id'],ascending=[False,False,True])
        else:
            g=g.sort_values(['order_approved_at','order_id'])
        chosen.extend(g.head(int(row.capacity)).index.tolist())
    sel=t.loc[chosen]
    k=sel.outcome_known
    nlate=int(sel.loc[k,'late'].sum())
    assert len(sel)==row.selected
    assert int(k.sum())==row.selected_known
    assert int((~k).sum())==row.selected_unknown
    assert nlate==row.selected_late
    assert np.isclose(100*nlate/late[known].sum(),row.late_capture_pct)
    assert np.isclose(100*nlate/k.sum(),row.late_precision_pct)
    assert np.isclose(100*k.mean(),row.outcome_coverage_pct)
    if row.capacity==100:
        col='selected_model_100' if row.policy=='Model priority' else 'selected_fifo_100'
        assert set(t.index[t[col]])==set(chosen)
passed('All 8 queue policy capacity combinations independently reconstructed')

test = pd.read_csv(R/'test_predictions.csv')
for filename,key,group in [('monthly_test_metrics.csv','month','approval_month'),('state_test_metrics.csv','state','customer_state')]:
    for _,row in pd.read_csv(R/filename).iterrows():
        g=test[test[group].eq(row[key])]
        same_metrics(g.remaining_delivery_days,g.prediction_days,row)
passed('All monthly and state error metrics recomputed from saved predictions')

sim = pd.read_csv(data_file('hypothetical_shipments'))
assert len(sim)==2000
assert np.allclose(sim.delivery_days,1+sim.distance_km/300+sim.extra_delay_days)
sp = pd.read_csv(R/'synthetic_test_predictions.csv')
assert len(sp)==396
same_metrics(sp.delivery_days,sp.prediction_days,S['synthetic']['metrics'][2])
passed('Synthetic target construction and held out metric arithmetic verified')

result={'status':'passed','verification_categories':len(checks),'checks':checks}
(R/'independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
