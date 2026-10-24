"""Week 3 executed EDA. Historical benchmark and synthetic experiment stay separate.

Run: python analyze.py --input data/orders_audit.csv.gz --output results
"""
from pathlib import Path
import argparse, hashlib, json, platform
import numpy as np
import pandas as pd

def describe(s):
    s = s.dropna()
    return dict(n=int(s.size), mean=float(s.mean()), median=float(s.median()),
                std=float(s.std(ddof=1)), minimum=float(s.min()), q1=float(s.quantile(.25)),
                q3=float(s.quantile(.75)), p90=float(s.quantile(.9)),
                maximum=float(s.max()), skew=float(s.skew()))

def main(input_path, out):
    out.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(input_path)
    assert d.order_id.is_unique and len(d) == 99441
    for col in ['eligible_cycle','eligible_otd']:
        d[col] = d[col].astype(str).str.lower().eq('true')
    d['on_time'] = d.on_time.astype(str).str.lower().map({'true':True,'false':False}).astype('boolean')
    d['purchase'] = pd.to_datetime(d.order_purchase_timestamp)
    d['month'] = d.purchase.dt.to_period('M').astype(str)
    d['weight_kg'] = d.total_weight_g / 1000
    d['volume_litres'] = d.total_volume_cm3 / 1000
    c = d.loc[d.eligible_cycle].copy()
    o = d.loc[d.eligible_otd].copy()
    assert o.on_time.notna().all()
    assert (c.cycle_days >= 0).all()
    descriptive = {col:describe(c[col]) for col in
        ['cycle_days','freight_brl','order_value_brl','item_count','weight_kg','volume_litres']}
    pd.DataFrame(descriptive).T.to_csv(out/'descriptive_statistics.csv',index_label='variable')
    stage_cols = ['approval_wait_days','dispatch_days','transit_days','cycle_days']
    stage = d.loc[d.order_status.eq('delivered'),stage_cols].dropna()
    assert np.allclose(stage[stage_cols[:3]].sum(axis=1),stage.cycle_days)
    stages = pd.DataFrame({col:describe(stage[col]) for col in stage_cols}).T
    stages.to_csv(out/'stage_statistics.csv',index_label='stage')
    states = o.groupby('customer_state').agg(orders=('order_id','size'),on_time=('on_time','sum'),
        median_days=('cycle_days','median'),mean_freight=('freight_brl','mean'))
    states['late'] = states.orders - states.on_time
    states['on_time_pct'] = states.on_time / states.orders * 100
    states = states.sort_values('orders',ascending=False)
    states.to_csv(out/'state_performance.csv',index_label='state')
    mature = d.loc[d.purchase.ge('2017-01-01') & d.purchase.lt('2018-07-01')]
    monthly = mature.groupby('month').agg(orders=('order_id','size'),items=('item_count','sum'))
    cm = mature.loc[mature.eligible_cycle].groupby('month').cycle_days.agg(
        completed='size',median='median',p90=lambda x:x.quantile(.9))
    monthly = monthly.join(cm)
    monthly['completion_coverage_pct'] = monthly.completed / monthly.orders * 100
    monthly.to_csv(out/'monthly_performance.csv')
    cols = ['cycle_days','freight_brl','order_value_brl','weight_kg','volume_litres','item_count']
    corr_data = c[cols].dropna()
    # Pearson correlation of average ranks is Spearman correlation, with ties handled.
    spearman = corr_data.rank(method='average').corr(method='pearson')
    pearson = corr_data.corr(method='pearson')
    spearman.to_csv(out/'spearman_correlations.csv')
    pearson.to_csv(out/'pearson_correlations.csv')
    relation = c[['weight_kg','freight_brl']].dropna()
    relation['weight_band'] = pd.cut(relation.weight_kg,
        [0,.25,.5,1,2,5,10,np.inf],labels=['0 to .25','.25 to .5','.5 to 1','1 to 2','2 to 5','5 to 10','Over 10'])
    weight = relation.groupby('weight_band',observed=True).freight_brl.agg(
        n='size',median='median',q1=lambda x:x.quantile(.25),q3=lambda x:x.quantile(.75))
    weight.to_csv(out/'freight_by_weight.csv')
    # All valid observations contribute to the summaries; scatter is only a visual sample.
    relation.sample(n=min(3000,len(relation)),random_state=2026).to_csv(out/'scatter_sample.csv',index=False)
    hist,edges = np.histogram(c.cycle_days,bins=np.arange(0,62,2))
    pd.DataFrame({'left_days':edges[:-1],'right_days':edges[1:],'orders':hist}).to_csv(out/'cycle_histogram.csv',index=False)
    ecdf = pd.DataFrame({'days':np.arange(0,61),
        'cumulative_pct':[(c.cycle_days.le(x).sum()/len(c)*100) for x in range(61)]})
    ecdf.to_csv(out/'cycle_ecdf.csv',index=False)

    # Separate hypothetical shipment dataset; coefficients are assumptions, not estimates.
    rng = np.random.default_rng(20261022)
    n = 2000
    sim = pd.DataFrame({'shipment_id':[f'SIM{i:04d}' for i in range(1,n+1)],
        'dispatch_date':pd.Timestamp('2026-07-01') + pd.to_timedelta(rng.integers(0,31,n),unit='D'),
        'distance_km':rng.uniform(50,1200,n),
        'weight_kg':np.clip(rng.lognormal(np.log(2),.8,n),.2,30),
        'item_units':rng.integers(1,6,n),
        'extra_delay_days':rng.choice([0,1,2,4],n,p=[.65,.2,.1,.05])})
    sim['delivery_days'] = 1 + sim.distance_km/300 + sim.extra_delay_days
    sim['promised_days'] = np.ceil(1 + sim.distance_km/300) + 1
    sim['on_time'] = sim.delivery_days.le(sim.promised_days)
    sim['base_cost_brl'] = 12.0
    sim['distance_cost_brl'] = .035 * sim.distance_km
    sim['weight_cost_brl'] = 1.2 * sim.weight_kg
    sim['delay_cost_brl'] = 4 * sim.extra_delay_days
    components = ['base_cost_brl','distance_cost_brl','weight_cost_brl','delay_cost_brl']
    sim['transport_cost_brl'] = sim[components].sum(axis=1)
    sim['cost_distance_minus10pct_brl'] = sim.transport_cost_brl - .1*sim.distance_cost_brl
    sim['cost_delay_minus1day_brl'] = sim.transport_cost_brl - 4*np.minimum(sim.extra_delay_days,1)
    sim.to_csv(out/'hypothetical_shipments.csv',index=False)
    sensitivity = {'baseline':float(sim.transport_cost_brl.mean()),
        'distance_minus10pct':float(sim.cost_distance_minus10pct_brl.mean()),
        'delay_minus1day':float(sim.cost_delay_minus1day_brl.mean())}
    synthetic = {'n':n,'seed':20261022,'description':'Entirely simulated; not Olist observations',
        'cost':describe(sim.transport_cost_brl),'delivery':describe(sim.delivery_days),
        'on_time_pct':float(sim.on_time.mean()*100),'item_units':int(sim.item_units.sum()),
        'distance_cost_correlation':float(sim.distance_km.corr(sim.transport_cost_brl)),
        'mean_components':sim[components].mean().to_dict(),
        'sensitivity_mean_cost_brl':sensitivity,
        'mean_savings_brl':{k:sensitivity['baseline']-v for k,v in sensitivity.items() if k!='baseline'},
        'assumed_formula':'12 + 0.035 * distance_km + 1.2 * weight_kg + 4 * extra_delay_days'}
    summary = {'source_orders':len(d),'delivered_status':int(d.order_status.eq('delivered').sum()),
        'cycle_n':len(c),'otd_n':len(o),'on_time_n':int(o.on_time.sum()),
        'on_time_pct':float(o.on_time.mean()*100),'late_n':int((~o.on_time).sum()),
        'descriptive':descriptive,'item_count_mode':float(c.item_count.mode().iat[0]),
        'over30_days':int(c.cycle_days.gt(30).sum()),'over60_days':int(c.cycle_days.gt(60).sum()),
        'stage_n':len(stage),'stage_means':stages['mean'].to_dict(),
        'transit_share_pct':float(stage.transit_days.mean()/stage.cycle_days.mean()*100),
        'corr_n':len(corr_data),'relation_n':len(relation),'zero_freight_n':int(relation.freight_brl.eq(0).sum()),
        'monthly_orders':int(monthly.orders.sum()),'monthly_completed':int(monthly.completed.sum()),
        'mature_window':['2017-01-01','2018-06-30'],
        'top2_late_share_pct':float(states.loc[['SP','RJ'],'late'].sum()/sum(states.late)*100),
        'synthetic':synthetic,'environment':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__},
        'input_sha256':hashlib.sha256(Path(input_path).read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,default=Path('data/orders_audit.csv.gz'))
    p.add_argument('--output',type=Path,default=Path('results'))
    args=p.parse_args(); main(args.input,args.output)
