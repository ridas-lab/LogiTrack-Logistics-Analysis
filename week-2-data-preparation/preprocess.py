"""Reproducible Week 2 Olist data preparation. Does not train a model."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import numpy as np
import pandas as pd

DATE_COLUMNS = ['order_purchase_timestamp','order_approved_at',
                'order_delivered_carrier_date','order_delivered_customer_date',
                'order_estimated_delivery_date']
NUMERIC = ['order_value_brl','freight_brl','item_count','seller_count',
           'total_weight_g','total_volume_cm3','promise_days','approval_wait_days']
LOG_FEATURES = {'order_value_brl','freight_brl','total_weight_g','total_volume_cm3'}
CATEGORICAL = ['customer_state','approval_weekday']
SPLITS = ['train','validation','test']

def save_json(path, data):
    def convert(x):
        if isinstance(x,np.generic): return x.item()
        if isinstance(x,pd.Timestamp): return str(x)
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(data,indent=2,default=convert,allow_nan=False),encoding='utf-8')

def run(data_dir, out):
    out.mkdir(parents=True,exist_ok=True)
    report={'source':{},'missing_before':{},'exact_duplicates_removed':{},
            'parse_failures':{},'invalid_numeric':{},'category_changes':{}}
    frames={}
    keys={'orders':['order_id'],'order_items':['order_id','order_item_id'],
          'customers':['customer_id'],'products':['product_id']}
    for name,key in keys.items():
        path=data_dir/f'olist_{name}_dataset.csv'
        df=pd.read_csv(path,dtype='string')
        report['source'][name]={'rows':len(df),'columns':len(df.columns),
                               'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        report['missing_before'][name]={k:int(v) for k,v in df.isna().sum().items() if v}
        report['exact_duplicates_removed'][name]=int(df.duplicated().sum())
        df=df.drop_duplicates().copy()
        for col in key:
            df[col]=df[col].str.strip().replace('',pd.NA)
        bad=df[key].isna().any(axis=1) | df.duplicated(key,keep=False)
        if bad.any():
            df.loc[bad].to_csv(out/f'{name}_key_conflicts.csv',index=False)
            raise ValueError(f'{name}: missing/conflicting key rows need resolution')
        frames[name]=df
    orders,items,customers,products=[frames[x] for x in keys]
    status_before=orders.order_status.copy()
    orders['order_status']=orders.order_status.str.strip().str.lower()
    report['category_changes']['order_status']=int(status_before.ne(orders.order_status).fillna(False).sum())
    state_before=customers.customer_state.copy()
    customers['customer_state']=customers.customer_state.str.strip().str.upper()
    report['category_changes']['customer_state']=int(state_before.ne(customers.customer_state).fillna(False).sum())
    # Source timestamps have no timezone offset; retain source wall-clock values.
    for col in DATE_COLUMNS:
        original=orders[col]
        orders[col]=pd.to_datetime(original,format='%Y-%m-%d %H:%M:%S',errors='coerce')
        report['parse_failures'][col]=int((original.notna() & orders[col].isna()).sum())
    for frame,cols,positive in [(items,['price','freight_value'],False),
        (products,['product_weight_g','product_length_cm','product_height_cm','product_width_cm'],True)]:
        for col in cols:
            raw=frame[col]
            vals=pd.to_numeric(raw,errors='coerce').astype(float)
            report['parse_failures'][col]=int((raw.notna() & vals.isna()).sum())
            invalid=vals.le(0) if positive else vals.lt(0)
            report['invalid_numeric'][col]=int(invalid.sum())
            frame[col]=vals.mask(invalid)
    products['volume_cm3']=products.product_length_cm*products.product_height_cm*products.product_width_cm
    ip=items.merge(products[['product_id','product_weight_g','volume_cm3']],
                   how='left',on='product_id',validate='many_to_one',indicator=True)
    report['item_rows_unmatched_product']=int(ip['_merge'].eq('left_only').sum())
    if not items.order_id.isin(orders.order_id).all():
        raise ValueError('Items refer to missing order IDs')
    def complete_sum(series):
        return series.sum(min_count=len(series))
    agg=ip.groupby('order_id').agg(
        order_value_brl=('price',complete_sum),freight_brl=('freight_value',complete_sum),
        item_count=('order_item_id','size'),seller_count=('seller_id','nunique'),
        total_weight_g=('product_weight_g',complete_sum),total_volume_cm3=('volume_cm3',complete_sum))
    d=orders.merge(agg,how='left',on='order_id',validate='one_to_one',indicator=True)
    report['orders_without_items']=int(d['_merge'].eq('left_only').sum())
    d=d.drop(columns='_merge').merge(customers[['customer_id','customer_state']],
         how='left',on='customer_id',validate='many_to_one',indicator=True)
    report['orders_unmatched_customer']=int(d['_merge'].eq('left_only').sum())
    d=d.drop(columns='_merge')
    assert len(d)==len(orders) and d.order_id.is_unique
    buy=d.order_purchase_timestamp; approval=d.order_approved_at
    handover=d.order_delivered_carrier_date; delivery=d.order_delivered_customer_date
    promise=d.order_estimated_delivery_date
    def days(a,b): return (a-b).dt.total_seconds()/86400
    d['approval_wait_days']=days(approval,buy)
    d['dispatch_days']=days(handover,approval)
    d['transit_days']=days(delivery,handover)
    d['cycle_days']=days(delivery,buy)
    d['remaining_delivery_days']=days(delivery,approval)
    # A date-based promise is inclusive of the whole promised day.
    d['promise_days']=days(promise.dt.normalize()+pd.Timedelta(days=1),approval)
    interval_cols=['approval_wait_days','dispatch_days','transit_days','cycle_days','remaining_delivery_days','promise_days']
    for col in interval_cols:
        d[f'{col}_invalid']=d[col].lt(0)
        d[col]=d[col].mask(d[f'{col}_invalid'])
    report['invalid_intervals']={col:int(d[f'{col}_invalid'].sum()) for col in interval_cols}
    delivered=d.order_status.eq('delivered')
    d['eligible_cycle']=delivered & d.cycle_days.notna()
    d['eligible_otd']=d.eligible_cycle & promise.notna() & promise.dt.normalize().ge(buy.dt.normalize())
    d['on_time']=pd.Series(pd.NA,index=d.index,dtype='boolean')
    valid=d.eligible_otd
    d.loc[valid,'on_time']=delivery.loc[valid].dt.normalize().le(promise.loc[valid].dt.normalize())
    d['approval_weekday']=approval.dt.day_name().astype('string')
    d['split']='outside_windows'
    d.loc[approval.lt('2018-01-01'),'split']='train'
    d.loc[approval.ge('2018-01-01') & approval.lt('2018-04-01'),'split']='validation'
    d.loc[approval.ge('2018-04-01') & approval.lt('2018-07-01'),'split']='test'
    d.loc[approval.isna(),'split']='missing_approval'
    # Preprocess all valid approvals, including orders with no delivery label.
    d['feature_eligible']=approval.notna() & ~d.approval_wait_days_invalid & d.split.isin(SPLITS)
    d['label_eligible']=False
    cutoff={'train':'2018-01-01','validation':'2018-04-01','test':'2018-09-01'}
    for split,stop in cutoff.items():
        mask=d.split.eq(split)&d.feature_eligible
        d.loc[mask,'label_eligible']=(delivered & d.remaining_delivery_days.notna() & delivery.lt(stop)).loc[mask]
    model=d.loc[d.feature_eligible].copy()
    train=model.loc[model.split.eq('train')]
    assert len(train)>0
    x=pd.DataFrame(index=model.index)
    params={'numeric':{},'categories':{},'fit_definition':'valid approval-time feature rows before 2018-01-01; no labels used',
            'log1p_features':sorted(LOG_FEATURES),'clip':False}
    numeric_audit=[]
    for col in NUMERIC:
        known=train[col].dropna()
        if known.empty:
            raise ValueError(f'Entirely missing training feature: {col}')
        median=float(known.median()); q1=float(known.quantile(.25)); q3=float(known.quantile(.75))
        lo=q1-1.5*(q3-q1); hi=q3+1.5*(q3-q1)
        raw=model[col].astype(float)
        x[col+'_missing']=raw.isna().astype(int)
        d.loc[model.index,col+'_iqr_flag']=((raw<lo)|(raw>hi)).astype(int)
        filled=raw.fillna(median)
        transformed=np.log1p(filled) if col in LOG_FEATURES else filled
        fit_vals=transformed.loc[train.index]
        minimum=float(fit_vals.min()); maximum=float(fit_vals.max())
        constant=maximum==minimum
        scale=maximum-minimum if not constant else 1.0
        x[col+'_scaled']=(transformed-minimum)/scale
        params['numeric'][col]={'median':median,'q1':q1,'q3':q3,'iqr_low':lo,'iqr_high':hi,
                               'transform':'log1p' if col in LOG_FEATURES else 'identity',
                               'min':minimum,'max':maximum,'denominator':scale,'constant':constant}
        for split in SPLITS:
            mask=model.split.eq(split)
            vals=raw.loc[mask]
            scaled=x.loc[mask,col+'_scaled']
            numeric_audit.append({'feature':col,'split':split,'rows':int(mask.sum()),
                'imputed':int(vals.isna().sum()),'iqr_flagged':int(((vals<lo)|(vals>hi)).sum()),
                'scaled_below_zero':int((scaled < -1e-12).sum()),
                'scaled_above_one':int((scaled > 1+1e-12).sum())})
    for col in CATEGORICAL:
        vals=model[col].fillna('__MISSING__').astype(str)
        learned=sorted(set(vals.loc[train.index])-{'__MISSING__','__UNKNOWN__'})
        categories=learned+['__MISSING__','__UNKNOWN__']
        vals=vals.where(vals.isin(categories),'__UNKNOWN__')
        params['categories'][col]=categories
        for category in categories:
            x[f'{col}__{category}']=vals.eq(category).astype(int)
    params['feature_columns']=x.columns.tolist()
    assert np.isfinite(x.to_numpy(dtype=float)).all()
    forbidden=set(DATE_COLUMNS+['order_status','on_time','remaining_delivery_days','dispatch_days','transit_days'])
    assert not forbidden.intersection(x.columns)
    for col in NUMERIC:
        values=x.loc[train.index,col+'_scaled']
        assert values.between(-1e-12,1+1e-12).all()
    for col in CATEGORICAL:
        assert x.filter(regex='^'+col+'__').sum(axis=1).eq(1).all()
    report['row_reconciliation']={'raw_orders':report['source']['orders']['rows'],
          'master_orders':len(d),'feature_rows':len(model),'feature_columns':len(x.columns),
          'excluded_from_features':len(d)-len(model)}
    report['split_counts']={split:{'all_approvals':int(d.split.eq(split).sum()),
         'feature_rows':int(model.split.eq(split).sum()),
         'label_eligible':int((d.split.eq(split)&d.label_eligible).sum()),
         'feature_rows_without_eligible_label':int((model.split.eq(split)&~model.label_eligible).sum())}
         for split in SPLITS}
    report['feature_exclusions']={'outside_windows':int(d.split.eq('outside_windows').sum()),
        'missing_approval':int(d.split.eq('missing_approval').sum()),
        'negative_approval_wait_in_windows':int((d.split.isin(SPLITS)&d.approval_wait_days_invalid).sum())}
    report['status_counts']={k:int(v) for k,v in d.order_status.value_counts().items()}
    report['date_ranges']={col:{'min':str(d[col].min()),'max':str(d[col].max())} for col in DATE_COLUMNS}
    report['derived_missing_all_orders']={col:int(d[col].isna().sum()) for col in NUMERIC}
    report['service_snapshot']={'delivered_status':int(delivered.sum()),
        'eligible_otd':int(d.eligible_otd.sum()),'on_time_orders':int(d.on_time.fillna(False).sum()),
        'otd_percent':float(d.loc[d.eligible_otd,'on_time'].mean()*100),
        'eligible_cycle':int(d.eligible_cycle.sum()),
        'cycle_median_days':float(d.loc[d.eligible_cycle,'cycle_days'].median()),
        'cycle_p90_days':float(d.loc[d.eligible_cycle,'cycle_days'].quantile(.9)),
        'complete_delivered_milestones':int(d.loc[delivered,DATE_COLUMNS].notna().all(axis=1).sum())}
    report['numeric_preprocessing']=numeric_audit
    report['validation_checks']=['unique source keys','no missing key fields','cardinality-validated joins',
        'master order count conserved','training-only fit parameters','finite model features',
        'training scaled ranges valid','one active encoded category per field','no outcome columns in X']
    report['software']={'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__}
    d.to_csv(out/'orders_audit.csv',index=False)
    x.to_csv(out/'prepared_features.csv',index=False)
    model[['order_id','split','label_eligible','remaining_delivery_days']].to_csv(out/'feature_index_and_labels.csv',index=False)
    pd.DataFrame(numeric_audit).to_csv(out/'preprocessing_counts.csv',index=False)
    # Select actual examples with missing and unusually high product weights.
    special=list(model.loc[model.total_weight_g.isna()].head(2).index)
    special+=list(model.nlargest(2,'total_weight_g').index)
    special+=list(model.head(2).index)
    special=list(dict.fromkeys(special))
    examples=model.loc[special,['order_id','split','total_weight_g','order_value_brl','freight_brl']].copy()
    examples['weight_filled']=model.loc[special,'total_weight_g'].fillna(params['numeric']['total_weight_g']['median'])
    examples=examples.join(x.loc[special,['total_weight_g_missing','total_weight_g_scaled','order_value_brl_scaled']])
    examples.to_csv(out/'before_after_examples.csv',index=False)
    save_json(out/'preprocessing_parameters.json',params)
    save_json(out/'audit_summary.json',report)
    print(json.dumps({'reconciliation':report['row_reconciliation'],'splits':report['split_counts'],
                      'invalid_intervals':report['invalid_intervals'],'snapshot':report['service_snapshot']},indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',type=Path,default=Path(__file__).parent/'data')
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).parent/'results')
    args=parser.parse_args()
    run(args.data_dir,args.output_dir)
