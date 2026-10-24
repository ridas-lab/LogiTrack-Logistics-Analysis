from pathlib import Path
import argparse
import numpy as np
import pandas as pd
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path('data'))
out=p.parse_args().output
out.mkdir(parents=True,exist_ok=True)
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
