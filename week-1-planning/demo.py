"""Run an illustrative KPI calculation on fictional data, not Olist data."""
import pandas as pd
from logistics_kpis import delivery_kpis

orders = pd.DataFrame({
    "order_id": ["a", "b", "c", "d"],
    "order_status": ["delivered", "delivered", "delivered", "canceled"],
    "order_purchase_timestamp": ["2018-01-01"] * 4,
    "order_delivered_customer_date": [
        "2018-01-03 15:00", "2018-01-05", "2018-01-02", None],
    "order_estimated_delivery_date": [
        "2018-01-03", "2018-01-04", "2018-01-04", "2018-01-04"],
})
items = pd.DataFrame({
    "order_id": ["a", "a", "b", "c", "d"],
    "order_item_id": [1, 2, 1, 1, 1],
    "freight_value": [5, 5, 20, None, 0],
})

if __name__ == "__main__":
    result = delivery_kpis(orders, items)
    assert result["orders"] == 4
    assert result["otd_n"] == 3
    assert abs(result["otd_pct"] - 200/3) < 1e-9
    assert result["freight_per_order_brl"] == 10
    print("FICTIONAL SAMPLE ONLY - NOT OLIST RESULTS")
    print(f"Total orders: {result['orders']}")
    print(f"Eligible completed orders: {result['otd_n']}")
    print(f"On-time delivery: {result['otd_pct']:.2f}%")
    print(f"Median cycle time: {result['cycle_median_days']:.3f} days")
    print(f"90th-percentile cycle time: {result['cycle_p90_days']:.3f} days")
    print(f"Freight per eligible order: BRL {result['freight_per_order_brl']:.2f}")
    print("The full real-data analysis is planned work.")
