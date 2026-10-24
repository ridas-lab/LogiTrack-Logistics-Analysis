import pandas as pd

def delivery_kpis(orders, items):
    o = orders.copy()
    assert o.order_id.notna().all()
    assert o.order_id.is_unique
    assert items.order_id.notna().all()
    assert items.order_item_id.notna().all()
    assert not items.duplicated(
        ["order_id", "order_item_id"]).any()
    assert items.order_id.isin(o.order_id).all()
    agg = items.groupby("order_id").agg(
        item_count=("order_item_id", "size"),
        freight=("freight_value", lambda s:
                 s.sum() if s.notna().all() and
                 s.ge(0).all() else float("nan")))
    d = o.merge(agg, on="order_id", how="left",
                validate="one_to_one")
    aliases = {"buy": "order_purchase_timestamp",
               "actual": "order_delivered_customer_date",
               "promise": "order_estimated_delivery_date"}
    for short, source in aliases.items():
        d[short] = pd.to_datetime(d[source], errors="coerce",
                                  format="mixed")
    delivered = d.order_status.eq("delivered")
    valid_cycle = (delivered & d.buy.notna() &
                   d.actual.notna() & d.actual.ge(d.buy))
    valid_otd = (valid_cycle & d.promise.notna() &
                 d.promise.dt.normalize().ge(
                     d.buy.dt.normalize()))
    x = d.loc[valid_otd]
    days = (d.loc[valid_cycle, "actual"] -
            d.loc[valid_cycle, "buy"]).dt.total_seconds()/86400
    on_time = x.actual.dt.normalize().le(x.promise.dt.normalize())
    freight_ok = d.freight.notna()
    return {"orders": len(d),
            "status_counts": d.order_status.value_counts(
                dropna=False).to_dict(),
            "otd_n": len(x), "otd_excluded": len(d)-len(x),
            "otd_pct": 100*on_time.mean(),
            "cycle_n": int(valid_cycle.sum()),
            "cycle_median_days": days.median(),
            "cycle_p90_days": days.quantile(.90),
            "freight_n": int(freight_ok.sum()),
            "freight_per_order_brl": d.freight.mean()}
