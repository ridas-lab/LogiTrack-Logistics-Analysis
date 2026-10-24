"""Week 4: leakage-aware regression and fixed-capacity review allocation.

Requires pandas, numpy, scikit-learn, joblib. Run from the packaged project:
python model.py --data data --output results
"""
from pathlib import Path
import argparse, hashlib, json, platform
import numpy as np
import pandas as pd
import sklearn
import joblib
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED=20261023
PLAN={
    'target':'remaining_delivery_days: approval to delivered customer, conditional on observable completed delivery',
    'minimum_followup_days':60,'cutoffs':{'train':'2018-01-01','validation':'2018-04-01','test':'2018-09-01'},
    'selection':'Lowest MAE on mature validation labels; deterministic tie by model name',
    'test_use':'Evaluate selected frozen model and baselines only; no test tuning or refitting',
    'prediction_postprocessing':'clip below zero; no upper clipping',
    'candidate_grid':{'ridge_alpha':[.1,1,10,100],'decision_tree_depth':[4,8],
        'tree_min_samples_leaf':50,'hgb_max_leaf_nodes':[15,31],
        'hgb_max_iter':200,'hgb_learning_rate':.05,'hgb_min_samples_leaf':50,
        'hgb_l2_regularization':1,'hgb_loss':'squared_error','hgb_early_stopping':False},
    'queue_capacity_primary':100,'capacity_sensitivity':[25,50,100,150],
    'queue_objective':'Maximize sum of prediction minus original promised duration at a fixed daily review count',
    'missing_promise_policy':'Flag for manual promise validation first; remaining slots ranked by score',
    'queue_comparator':'Earliest approval first within each approval day',
    'synthetic_probe':'Week 3 independent 2000-row simulation; Ridge alpha1 fixed, distance/weight/units only; chronological July split',
    'seed':SEED}

def save_json(path,obj):
    def convert(v):
        if isinstance(v,np.generic):return v.item()
        if isinstance(v,Path):return str(v)
        raise TypeError(type(v).__name__)
    path.write_text(json.dumps(obj,indent=2,default=convert,allow_nan=False),encoding='utf-8')

def metrics(y,p):
    return {'n':len(y),'mae_days':float(mean_absolute_error(y,p)),
        'rmse_days':float(np.sqrt(mean_squared_error(y,p))),'r2':float(r2_score(y,p)),
        'bias_days':float(np.mean(np.asarray(p)-np.asarray(y))),
        'median_absolute_error_days':float(np.median(np.abs(np.asarray(p)-np.asarray(y)))),
        'p90_absolute_error_days':float(np.quantile(np.abs(np.asarray(p)-np.asarray(y)),.9))}

def predict(model,x):return np.maximum(model.predict(x),0)

def locate(folder,name):
    plain=folder/(name+'.csv');compressed=folder/(name+'.csv.gz')
    return compressed if compressed.exists() else plain

def queue_select(t,capacity,policy):
    if policy=='Model priority':
        ordered=t.sort_values(['approval_day','missing_promise','priority_score','order_id'],
            ascending=[True,False,False,True],kind='stable')
    else:
        ordered=t.sort_values(['approval_day','order_approved_at','order_id'],kind='stable')
    return ordered.groupby('approval_day',sort=False).head(capacity).index

def queue_metrics(t,selected,capacity,policy):
    evaluated=t.outcome_known
    selected_known=t.loc[selected].outcome_known
    selected_late=t.loc[selected].loc[selected_known,'late'].sum()
    all_late=t.loc[evaluated,'late'].sum()
    return {'capacity':capacity,'policy':policy,'selected':len(selected),
        'selected_known':int(selected_known.sum()),'selected_unknown':int((~selected_known).sum()),
        'selected_late':int(selected_late),'total_known':int(evaluated.sum()),'total_late':int(all_late),
        'late_capture_pct':float(100*selected_late/all_late),
        'late_precision_pct':float(100*selected_late/selected_known.sum()),
        'outcome_coverage_pct':float(100*selected_known.mean())}

def run(data,out):
    out.mkdir(parents=True,exist_ok=True)
    save_json(out/'analysis_plan.json',PLAN)  # Declared before fitting or evaluating test predictions.
    paths={name:locate(data,name) for name in ['orders_audit','prepared_features','feature_index_and_labels']}
    audit=pd.read_csv(paths['orders_audit'])
    x=pd.read_csv(paths['prepared_features'])
    labels=pd.read_csv(paths['feature_index_and_labels'])
    assert len(x)==len(labels)==86484 and labels.order_id.is_unique
    assert audit.order_id.is_unique and len(audit)==99441
    m=labels.merge(audit,on='order_id',how='left',validate='one_to_one',suffixes=('_label',''))
    assert m.order_id.tolist()==labels.order_id.tolist()
    assert (m['split_label']==m['split']).all()
    assert np.isfinite(x.to_numpy()).all()
    for col in ['order_approved_at','order_delivered_customer_date']:
        m[col]=pd.to_datetime(m[col])
    y=m.remaining_delivery_days.to_numpy(float)
    masks={};cohorts=[]
    for split,cutoff in PLAN['cutoffs'].items():
        approval_rows=m.split.eq(split)
        followup=m.order_approved_at.lt(pd.Timestamp(cutoff)-pd.Timedelta(days=60))
        eligible=m.label_eligible.astype(bool)
        masks[split]=(approval_rows & followup & eligible).to_numpy()
        cohorts.append({'split':split,'all_approvals':int(approval_rows.sum()),
            'all_eligible_labels':int((approval_rows&eligible).sum()),
            'mature_approvals':int((approval_rows&followup).sum()),
            'mature_eligible_labels':int(masks[split].sum()),
            'mature_without_label':int((approval_rows&followup&~eligible).sum()),
            'label_cutoff':cutoff,'approval_before':str(pd.Timestamp(cutoff)-pd.Timedelta(days=60))})
        assert (m.loc[masks[split],'order_delivered_customer_date']<pd.Timestamp(cutoff)).all()
        assert np.isfinite(y[masks[split]]).all() and (y[masks[split]]>=0).all()
    pd.DataFrame(cohorts).to_csv(out/'cohorts.csv',index=False)
    train=masks['train'];val=masks['validation'];test=masks['test']
    fullval=(m.split.eq('validation') & m.label_eligible).to_numpy()
    candidates={
        'Median baseline':DummyRegressor(strategy='median'),
        'Mean baseline':DummyRegressor(strategy='mean')}
    for alpha in PLAN['candidate_grid']['ridge_alpha']:
        candidates[f'Ridge alpha {alpha:g}']=Ridge(alpha=alpha)
    for depth in [4,8]:
        candidates[f'Decision tree depth {depth}']=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=50,random_state=SEED)
    for leaves in [15,31]:
        candidates[f'Gradient boosting leaves {leaves}']=HistGradientBoostingRegressor(
            max_leaf_nodes=leaves,max_iter=200,learning_rate=.05,min_samples_leaf=50,
            l2_regularization=1,loss='squared_error',early_stopping=False,random_state=SEED)
    comparison=[]
    for name,model in candidates.items():
        model.fit(x.loc[train],y[train])
        pred=predict(model,x.loc[val]);trpred=predict(model,x.loc[train])
        row={'model':name,**metrics(y[val],pred),'train_mae_days':metrics(y[train],trpred)['mae_days']}
        comparison.append(row)
        print(name,round(row['mae_days'],4),flush=True)
    comparison=pd.DataFrame(comparison).sort_values(['mae_days','model'])
    comparison.to_csv(out/'validation_model_comparison.csv',index=False)
    selected_name=comparison.model.iat[0];selected=candidates[selected_name]
    save_json(out/'selection.json',{'selected_model':selected_name,'criterion':'mature validation MAE only',
        'fitted_train_rows':int(train.sum()),'selection_rows':int(val.sum()),'test_not_used':True,
        'parameters':selected.get_params()})
    joblib.dump({'model':selected,'features':x.columns.tolist(),'plan':PLAN},out/'trained_model.joblib')
    # Validation diagnostics and feature inspection precede the final test scoring.
    valpred=predict(selected,x.loc[val]);valmae=mean_absolute_error(y[val],valpred)
    groups={name:[c for c in x.columns if c.startswith(name+'_')] for name in
        ['order_value_brl','freight_brl','item_count','seller_count','total_weight_g',
         'total_volume_cm3','promise_days','approval_wait_days']}
    groups['customer_state']=[c for c in x if c.startswith('customer_state__')]
    groups['approval_weekday']=[c for c in x if c.startswith('approval_weekday__')]
    rng=np.random.default_rng(SEED);importance=[]
    xv=x.loc[val].copy()
    for group,cols in groups.items():
        changes=[]
        for repeat in range(5):
            perm=rng.permutation(len(xv));xp=xv.copy();xp.loc[:,cols]=xv[cols].to_numpy()[perm]
            changes.append(mean_absolute_error(y[val],predict(selected,xp))-valmae)
        importance.append({'feature_group':group,'mean_mae_increase_days':np.mean(changes),
            'std_mae_increase_days':np.std(changes,ddof=1),'repeats':5})
    pd.DataFrame(importance).sort_values('mean_mae_increase_days',ascending=False).to_csv(out/'permutation_importance.csv',index=False)
    # Prespecified ablation, diagnostic only. It cannot replace the selected model.
    from sklearn.base import clone
    no_promise=[c for c in x if not c.startswith('promise_days_')]
    ablated=clone(selected).fit(x.loc[train,no_promise],y[train])
    ablation=metrics(y[val],predict(ablated,x.loc[val,no_promise]))
    valdetail=m.loc[val,['order_id','customer_state','order_approved_at','remaining_delivery_days']].copy()
    valdetail['prediction_days']=valpred;valdetail.to_csv(out/'validation_predictions.csv',index=False)

    # Final test is scored only after model selection has been saved.
    testmetrics=[];testpreds={}
    for name,model in [('Selected model',selected),('Median baseline',candidates['Median baseline']),('Mean baseline',candidates['Mean baseline'])]:
        pred=predict(model,x.loc[test]);testpreds[name]=pred
        testmetrics.append({'model':name,**metrics(y[test],pred)})
    pd.DataFrame(testmetrics).to_csv(out/'test_metrics.csv',index=False)
    t=m.loc[m.split.eq('test')].copy()
    t['prediction_days']=predict(selected,x.loc[m.split.eq('test')])
    t['approval_day']=t.order_approved_at.dt.strftime('%Y-%m-%d')
    t['approval_month']=t.order_approved_at.dt.strftime('%Y-%m')
    t['missing_promise']=t.promise_days.isna() | t.promise_days.lt(0)
    t['priority_score']=(t.prediction_days-t.promise_days).fillna(0)
    t['outcome_known']=t.label_eligible & t.eligible_otd & t.on_time.notna()
    t['late']=~t.on_time.fillna(True).astype(bool)
    chosen=queue_select(t,100,'Model priority');fifo=queue_select(t,100,'FIFO')
    t['selected_model_100']=t.index.isin(chosen);t['selected_fifo_100']=t.index.isin(fifo)
    queue=[]
    for cap in PLAN['capacity_sensitivity']:
        for policy in ['Model priority','FIFO']:
            sel=queue_select(t,cap,policy)
            expected=int(t.groupby('approval_day').size().clip(upper=cap).sum())
            assert len(sel)==expected
            queue.append(queue_metrics(t,sel,cap,policy))
    pd.DataFrame(queue).to_csv(out/'queue_metrics.csv',index=False)
    keep=['order_id','order_approved_at','approval_day','approval_month','customer_state','label_eligible',
        'remaining_delivery_days','promise_days','prediction_days','missing_promise','priority_score',
        'outcome_known','late','selected_model_100','selected_fifo_100']
    t[keep].to_csv(out/'test_all_approval_predictions.csv',index=False)
    te=t.loc[t.label_eligible].copy()
    assert len(te)==int(test.sum())
    residual=te.prediction_days-te.remaining_delivery_days
    te['residual_days']=residual;te['absolute_error_days']=residual.abs()
    te[['order_id','approval_month','customer_state','remaining_delivery_days','prediction_days',
        'residual_days','absolute_error_days']].to_csv(out/'test_predictions.csv',index=False)
    monthly=[];states=[]
    for month,g in te.groupby('approval_month'):
        monthly.append({'month':month,**metrics(g.remaining_delivery_days,g.prediction_days)})
    for state,g in te.groupby('customer_state'):
        states.append({'state':state,**metrics(g.remaining_delivery_days,g.prediction_days)})
    pd.DataFrame(monthly).to_csv(out/'monthly_test_metrics.csv',index=False)
    pd.DataFrame(states).sort_values('n',ascending=False).to_csv(out/'state_test_metrics.csv',index=False)
    daily=t.groupby('approval_day').agg(approvals=('order_id','size'),model_reviews=('selected_model_100','sum'),fifo_reviews=('selected_fifo_100','sum'))
    daily.to_csv(out/'daily_allocation.csv')
    errors_by_true=[]
    for label,mask in [('Up to 14 days',te.remaining_delivery_days.le(14)),
        ('14 to 30 days',te.remaining_delivery_days.gt(14)&te.remaining_delivery_days.le(30)),
        ('Over 30 days',te.remaining_delivery_days.gt(30))]:
        g=te.loc[mask];errors_by_true.append({'actual_duration_band':label,**metrics(g.remaining_delivery_days,g.prediction_days)})
    pd.DataFrame(errors_by_true).to_csv(out/'error_by_actual_duration.csv',index=False)
    # Separate simulated data: delay and cost fields are deliberately excluded.
    simpath=locate(data,'hypothetical_shipments');sim=pd.read_csv(simpath)
    sim['dispatch_date']=pd.to_datetime(sim.dispatch_date)
    simcols=['distance_km','weight_kg','item_units'];sx=sim[simcols];sy=sim.delivery_days
    smasks={'train':sim.dispatch_date.lt('2026-07-20'),
        'validation':sim.dispatch_date.ge('2026-07-20')&sim.dispatch_date.lt('2026-07-26'),
        'test':sim.dispatch_date.ge('2026-07-26')}
    sm=Ridge(alpha=1).fit(sx.loc[smasks['train']],sy.loc[smasks['train']])
    sb=DummyRegressor(strategy='median').fit(sx.loc[smasks['train']],sy.loc[smasks['train']])
    simmetrics=[]
    for split in ['validation','test']:
        for name,model in [('Ridge alpha 1',sm),('Median baseline',sb)]:
            simmetrics.append({'split':split,'model':name,**metrics(sy.loc[smasks[split]],predict(model,sx.loc[smasks[split]]))})
    pd.DataFrame(simmetrics).to_csv(out/'synthetic_metrics.csv',index=False)
    sp=sim.loc[smasks['test'],['shipment_id','distance_km','delivery_days']].copy()
    sp['prediction_days']=predict(sm,sx.loc[smasks['test']]);sp.to_csv(out/'synthetic_test_predictions.csv',index=False)
    coefficients={'intercept':float(sm.intercept_),**{c:float(v) for c,v in zip(simcols,sm.coef_)}}
    selection_month=m.loc[m.split.eq('validation')].groupby(m.loc[m.split.eq('validation'),'order_approved_at'].dt.strftime('%Y-%m')).agg(approvals=('order_id','size'),eligible_labels=('label_eligible','sum'))
    selection_month.to_csv(out/'validation_label_coverage.csv',index_label='month')
    summary={
        'selected_model':selected_name,'feature_count':x.shape[1],'cohorts':cohorts,
        'validation_selected':metrics(y[val],valpred),
        'validation_all_label_diagnostic':metrics(y[fullval],predict(selected,x.loc[fullval])),
        'validation_without_promise_diagnostic':ablation,
        'test':testmetrics,'primary_allocation':[r for r in queue if r['capacity']==100],
        'test_approval_days':len(daily),'test_calendar_days':91,
        'days_above_capacity100':int(daily.approvals.gt(100).sum()),
        'missing_test_promises':int(t.missing_promise.sum()),
        'test_actual_max_days':float(te.remaining_delivery_days.max()),
        'test_over60_days':int(te.remaining_delivery_days.gt(60).sum()),
        'negative_prediction_clipping':'All candidate and final predictions are lower-bounded at zero; no upper bound',
        'synthetic':{'rows':len(sim),'split_counts':{k:int(v.sum()) for k,v in smasks.items()},
            'features':simcols,'target':'delivery_days','ridge_alpha':1,'coefs':coefficients,'metrics':simmetrics,
            'target_generation':'1 + distance_km/300 + extra_delay_days',
            'excluded_outcomes':['extra_delay_days','transport_cost_brl','delay_cost_brl','on_time']},
        'software':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,
            'scikit_learn':sklearn.__version__,'joblib':joblib.__version__},
        'input_hashes':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}}
    save_json(out/'summary.json',summary)
    print(json.dumps({'selected':selected_name,'test':testmetrics,'allocation':summary['primary_allocation']},indent=2),flush=True)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path('data'))
    p.add_argument('--output',type=Path,default=Path('results'))
    a=p.parse_args();run(a.data,a.output)
