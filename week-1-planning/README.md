# Ecommerce Delivery Reliability

[Project overview](../README.md) · [Word report](Week_1_Report.docx) · [Submission description](Submission_Description.txt)

## Week 1 Strategic Planning and Data Exploration in Logistics

Prepared for Rida Sahin's Logistics Data Analyst internship submission.

This project plans how an ecommerce logistics team could identify delivery
bottlenecks, estimate delivery time, and prioritize limited staff review capacity.
The business scenario is hypothetical. The proposed historical benchmark is the
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

## Project status

Completed for Week 1:

- A strategic planning report with a defined business scenario and objectives.
- Five KPI definitions and proposed success thresholds.
- Background research and a public-data acquisition plan.
- A roadmap for cleaning, exploration, prediction, and review allocation.
- An illustrative Python function, checked on small synthetic examples.
- Modeling pseudocode, risk controls, expected outcomes, and a pilot plan.

Planned for later implementation:

- Downloading and auditing the full Olist data.
- Calculating real baseline performance and creating exploratory charts.
- Training and evaluating regression and clustering models.
- Simulating review allocation on real orders and evaluating a live pilot.

**No Olist analysis results, trained model, or measured service improvement are
claimed.** The 100-reviews-per-day capacity and performance targets in the report
are planning assumptions.

## What is included

| File | Purpose |
| --- | --- |
| `Week_1_Report.docx` | Main internship report to upload to the submission portal |
| `WORK_PLAN.md` | Plain-language explanation of the project steps |
| `MODEL_PLAN.md` | Python-style pseudocode for later modeling and allocation |
| `logistics_kpis.py` | Illustrative pandas KPI function from the report |
| `demo.py` | Runnable demonstration using four fictional orders |
| `requirements.txt` | Python dependency for the demonstration |

The example function computes on-time delivery, cycle-time summaries, and recorded
freight per order, with eligible counts. Dispatch lead time and delivered milestone
completeness are specified in the report for the full future pipeline.

## Understand the KPIs

1. **On-time delivery rate:** how many completed orders arrived by the promised date.
2. **Order cycle time:** how long delivery took from purchase; inspect both typical
   orders and the slowest tail.
3. **Seller dispatch lead time:** how long sellers took to hand orders to carriers.
4. **Recorded freight per order:** the average recorded freight amount; this is not
   total business logistics cost.
5. **Delivered milestone completeness:** whether delivered orders have the required
   milestone timestamps.

## Run the optional demonstration

Publishing this repository does not require running Python. If Python 3.10 or later
is installed, open a terminal in this folder and run:

```text
python -m pip install -r requirements.txt
python demo.py
```

**Synthetic demonstration only, not Olist results:** the example contains four
fictional orders. Three are eligible for on-time delivery calculation and two are
on time, so the demonstration prints 66.67%. The sample deliberately includes a
missing freight value to demonstrate exclusion from that metric.

The code checks order identifiers, duplicate item keys, and order-level joins.
It compares calendar dates so an afternoon delivery on the promised date counts
as on time. This is teaching code, not a production system; the report explains
the additional quality checks and operational inputs needed.

## Data and research

The real dataset is not bundled in this Week 1 folder. Acquire it from its source and check its current
reuse conditions before use. The report contains the full references, including:

- [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- [Scikit-learn data leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html)
- [Scikit-learn time-ordered evaluation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- [Pandas merge validation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html)
- [Google OR-Tools capacity-limited assignment](https://developers.google.com/optimization/assignment/assignment_cp)


## Place in the four week project

This folder is a self-contained weekly snapshot within the shared LogiTrack repository. Prepared data are repeated where needed to preserve independent reproduction and the original result hashes. See the [project overview](../README.md) for the complete progression.
