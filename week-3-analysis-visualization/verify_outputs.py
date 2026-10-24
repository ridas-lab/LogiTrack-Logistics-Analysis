"""Independent verification of Week 3 saved outputs; never imports analyze.py."""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input', type=Path, default=Path('data/orders_audit.csv.gz'))
parser.add_argument('--results', type=Path, default=Path('results'))
args = parser.parse_args()
OUT = args.results
INPUT = args.input
summary = json.loads((OUT / 'summary.json').read_text(encoding='utf-8'))
d = pd.read_csv(INPUT)
d['weight_kg'] = d.total_weight_g / 1000
d['volume_litres'] = d.total_volume_cm3 / 1000
d['month'] = pd.to_datetime(d.order_purchase_timestamp).dt.strftime('%Y-%m')
c = d.loc[d.eligible_cycle]
o = d.loc[d.eligible_otd]
checks = []


def check(name, actual, expected, atol=1e-9):
    if isinstance(expected, (float, int, np.integer, np.floating)):
        passed = math.isclose(float(actual), float(expected), rel_tol=1e-11, abs_tol=atol)
    else:
        passed = actual == expected
    checks.append({'name': name, 'passed': bool(passed), 'actual': actual, 'expected': expected})


def matrix_check(name, actual, expected):
    actual = np.asarray(actual, dtype=float)
    expected = np.asarray(expected, dtype=float)
    passed = actual.shape == expected.shape and np.allclose(actual, expected, rtol=1e-10, atol=1e-9, equal_nan=True)
    checks.append({'name': name, 'passed': bool(passed), 'actual_shape': list(actual.shape), 'expected_shape': list(expected.shape), 'maximum_absolute_error': float(np.nanmax(np.abs(actual-expected))) if actual.shape == expected.shape else None})


def stats(s):
    s = s.dropna()
    return {'n': int(len(s)), 'mean': s.mean(), 'median': s.median(), 'std': s.std(ddof=1),
            'minimum': s.min(), 'q1': s.quantile(.25), 'q3': s.quantile(.75),
            'p90': s.quantile(.9), 'maximum': s.max(), 'skew': s.skew()}


for key, value in {'source_orders': len(d), 'delivered_status': int(d.order_status.eq('delivered').sum()),
                   'cycle_n': len(c), 'otd_n': len(o), 'on_time_n': int(o.on_time.sum()),
                   'on_time_pct': 100*o.on_time.mean(), 'late_n': int(len(o)-o.on_time.sum()),
                   'item_count_mode': float(c.item_count.mode().iat[0]),
                   'over30_days': int(c.cycle_days.gt(30).sum()), 'over60_days': int(c.cycle_days.gt(60).sum())}.items():
    check('summary.'+key, summary[key], value)
check('unique_order_ids', d.order_id.is_unique, True)
check('input_sha256', summary['input_sha256'], hashlib.sha256(INPUT.read_bytes()).hexdigest())
descriptive = pd.read_csv(OUT/'descriptive_statistics.csv', index_col=0)
for col in ['cycle_days','freight_brl','order_value_brl','item_count','weight_kg','volume_litres']:
    for metric, value in stats(c[col]).items():
        check(f'descriptive_summary.{col}.{metric}', summary['descriptive'][col][metric], value)
        check(f'descriptive_csv.{col}.{metric}', descriptive.loc[col,metric], value)

stage_cols = ['approval_wait_days','dispatch_days','transit_days','cycle_days']
stage = d.loc[d.order_status.eq('delivered') & d[stage_cols].notna().all(axis=1)]
check('stage_n', summary['stage_n'], len(stage))
stage_csv = pd.read_csv(OUT/'stage_statistics.csv', index_col=0)
for col in stage_cols:
    check('stage_mean.'+col, summary['stage_means'][col], stage[col].mean())
    for metric, value in stats(stage[col]).items():
        check(f'stage_csv.{col}.{metric}', stage_csv.loc[col,metric], value)
matrix_check('stage_row_additivity', stage[stage_cols[:3]].sum(axis=1), stage.cycle_days)
check('transit_share_pct', summary['transit_share_pct'], 100*stage.transit_days.mean()/stage.cycle_days.mean())

states = pd.read_csv(OUT/'state_performance.csv', index_col=0)
for state, group in o.groupby('customer_state'):
    expected = {'orders': len(group), 'on_time': group.on_time.sum(), 'late': len(group)-group.on_time.sum(),
                'median_days': group.cycle_days.median(), 'mean_freight': group.freight_brl.mean(),
                'on_time_pct': 100*group.on_time.mean()}
    for key,value in expected.items():
        check(f'state.{state}.{key}', states.loc[state,key], value)
check('state_ordering_descending_volume', states.orders.is_monotonic_decreasing, True)
check('state_otd_denominator_sum', states.orders.sum(), len(o))
check('top2_late_share_pct', summary['top2_late_share_pct'], 100*states.loc[['SP','RJ'],'late'].sum()/(len(o)-o.on_time.sum()))

monthly = pd.read_csv(OUT/'monthly_performance.csv', index_col=0)
mature = d.loc[d.month.ge('2017-01') & d.month.le('2018-06')]
check('mature_month_count', len(monthly), 18)
for month,group in mature.groupby('month'):
    completed = group.loc[group.eligible_cycle]
    expected = {'orders':len(group), 'items':group.item_count.sum(), 'completed':len(completed),
                'median':completed.cycle_days.median(), 'p90':completed.cycle_days.quantile(.9),
                'completion_coverage_pct':100*len(completed)/len(group)}
    for key,value in expected.items():
        check(f'month.{month}.{key}', monthly.loc[month,key], value)
check('monthly_orders', summary['monthly_orders'], len(mature))
check('monthly_completed', summary['monthly_completed'], int(mature.eligible_cycle.sum()))

corcols = ['cycle_days','freight_brl','order_value_brl','weight_kg','volume_litres','item_count']
complete = c[corcols].dropna()
check('corr_n', summary['corr_n'], len(complete))
for filename,expected in [('spearman_correlations.csv', complete.rank(method='average').corr()),
                          ('pearson_correlations.csv', complete.corr())]:
    actual = pd.read_csv(OUT/filename,index_col=0)
    matrix_check(filename, actual.loc[corcols,corcols], expected.loc[corcols,corcols])
relation = c[['weight_kg','freight_brl']].dropna()
check('relation_n', summary['relation_n'], len(relation))
check('zero_freight_n', summary['zero_freight_n'], int(relation.freight_brl.eq(0).sum()))
bands = [(0,.25),(.25,.5),(.5,1),(1,2),(2,5),(5,10),(10,float('inf'))]
band_csv = pd.read_csv(OUT/'freight_by_weight.csv')
for i,(lo,hi) in enumerate(bands):
    subset = relation.loc[relation.weight_kg.gt(lo) & relation.weight_kg.le(hi),'freight_brl']
    for key,value in {'n':len(subset),'median':subset.median(),'q1':subset.quantile(.25),'q3':subset.quantile(.75)}.items():
        check(f'weight_band.{i}.{key}', band_csv.loc[i,key], value)
check('weight_band_population_sum', band_csv.n.sum(), len(relation))
sample = pd.read_csv(OUT/'scatter_sample.csv')
matrix_check('scatter_sample_reproducibility', sample[['weight_kg','freight_brl']], relation.sample(n=3000,random_state=2026))
hist = pd.read_csv(OUT/'cycle_histogram.csv')
expected_hist = []
for i in range(30):
    low,high=2*i,2*i+2
    selector=c.cycle_days.ge(low)&(c.cycle_days.le(high) if i==29 else c.cycle_days.lt(high))
    expected_hist.append(int(selector.sum()))
matrix_check('histogram_counts',hist.orders,expected_hist)
check('histogram_plus_tail_reconciliation',int(hist.orders.sum())+summary['over60_days'],len(c))
ecdf = pd.read_csv(OUT/'cycle_ecdf.csv')
matrix_check('ecdf_percentages',ecdf.cumulative_pct,[100*c.cycle_days.le(day).mean() for day in range(61)])

sim=pd.read_csv(OUT/'hypothetical_shipments.csv')
s=summary['synthetic']
check('synthetic_n',len(sim),2000)
check('synthetic_unique_ids',sim.shipment_id.is_unique,True)
check('synthetic_seed',s['seed'],20261022)
rng=np.random.default_rng(20261022)
dates=pd.Timestamp('2026-07-01')+pd.to_timedelta(rng.integers(0,31,2000),unit='D')
check('synthetic_seed_dates',pd.to_datetime(sim.dispatch_date).tolist(),list(dates))
matrix_check('synthetic_seed_distances',sim.distance_km,rng.uniform(50,1200,2000))
matrix_check('synthetic_seed_weights',sim.weight_kg,np.clip(rng.lognormal(np.log(2),.8,2000),.2,30))
matrix_check('synthetic_seed_units',sim.item_units,rng.integers(1,6,2000))
matrix_check('synthetic_seed_delays',sim.extra_delay_days,rng.choice([0,1,2,4],2000,p=[.65,.2,.1,.05]))
matrix_check('synthetic_delivery_formula',sim.delivery_days,1+sim.distance_km/300+sim.extra_delay_days)
matrix_check('synthetic_promise_formula',sim.promised_days,np.ceil(1+sim.distance_km/300)+1)
check('synthetic_ontime_flags',sim.on_time.tolist(),sim.delivery_days.le(sim.promised_days).tolist())
components={'base_cost_brl':np.full(2000,12),'distance_cost_brl':.035*sim.distance_km,
            'weight_cost_brl':1.2*sim.weight_kg,'delay_cost_brl':4*sim.extra_delay_days}
for col,expected in components.items():
    matrix_check('synthetic_'+col,sim[col],expected)
    check('synthetic_mean_'+col,s['mean_components'][col],float(np.mean(expected)))
baseline=12+.035*sim.distance_km+1.2*sim.weight_kg+4*sim.extra_delay_days
distance_case=12+.035*(.9*sim.distance_km)+1.2*sim.weight_kg+4*sim.extra_delay_days
delay_case=12+.035*sim.distance_km+1.2*sim.weight_kg+4*np.maximum(sim.extra_delay_days-1,0)
matrix_check('synthetic_baseline_formula',sim.transport_cost_brl,baseline)
matrix_check('synthetic_distance_sensitivity',sim.cost_distance_minus10pct_brl,distance_case)
matrix_check('synthetic_delay_sensitivity',sim.cost_delay_minus1day_brl,delay_case)
for key, series in [('baseline',baseline),('distance_minus10pct',distance_case),('delay_minus1day',delay_case)]:
    check('synthetic_sensitivity_mean_'+key,s['sensitivity_mean_cost_brl'][key],series.mean())
    if key!='baseline':
        check('synthetic_savings_'+key,s['mean_savings_brl'][key],baseline.mean()-series.mean())
for field,col in [('cost','transport_cost_brl'),('delivery','delivery_days')]:
    for key,value in stats(sim[col]).items():
        check('synthetic_'+field+'_'+key,s[field][key],value)
check('synthetic_on_time_pct',s['on_time_pct'],100*sim.on_time.mean())
check('synthetic_item_units',s['item_units'],int(sim.item_units.sum()))
check('synthetic_distance_cost_correlation',s['distance_cost_correlation'],sim.distance_km.corr(sim.transport_cost_brl))

# Large boolean checks do not need row-wise contents in the audit report.
for entry in checks:
    if isinstance(entry.get('actual'), list) and len(entry['actual'])>50:
        entry['actual']='List contents compared in memory'
        entry['expected']='Identical list contents required'
def convert(value):
    if isinstance(value,np.generic): return value.item()
    raise TypeError(type(value).__name__)
failed=[entry for entry in checks if not entry['passed']]
verification={'status':'PASS' if not failed else 'FAIL','checks_run':len(checks),'checks_passed':len(checks)-len(failed),
    'checks_failed':len(failed),'failures':failed,'checks':checks,
    'methodology_review':{
        'numerical_fixes_required':[],
        'interpretation_requirements':[
            'Keep historical observed charges and hypothetical operating costs explicitly separate.',
            'The two synthetic sensitivities are separate cost-only cases holding other inputs fixed; no joint saving or delivery-time improvement is calculated.',
            'Synthetic distance-cost correlation is induced by the assumed formula and is not empirical causal evidence.',
            'Show both eligible cohort denominators and all-order monthly volumes.',
            'Disclose 306 completed orders above the 60-day histogram range; preserve these records in all statistics.',
            'Use stage mean shares on the common cohort of 95,082; do not add medians.',
            'ReportLab is used for chart rendering; do not claim matplotlib/seaborn/plotly execution.',
        ],
        'scope':'Numerical CSV/JSON outputs and Python analysis inspected; document and rendered charts require visual review separately.'}}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2,default=convert),encoding='utf-8')
print(json.dumps({k:verification[k] for k in ['status','checks_run','checks_passed','checks_failed','failures']},indent=2,default=convert))
