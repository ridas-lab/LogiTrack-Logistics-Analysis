# Week 2 Ecommerce Logistics Data Preprocessing

[Project overview](../README.md) · [Word report](reports/Week_2_Report.docx) · [Submission description](Submission_Description.txt)

Prepared for Rida Sahin's Logistics Data Analyst internship.

This project continues the Week 1 delivery-reliability plan. It executes data
collection, quality checks, cleaning, imputation, outlier flagging, normalization,
and categorical encoding on an official public Olist repository snapshot.

## Completed results

- Acquired 99,441 orders, 112,650 items, 99,441 customer records, and 32,951 products.
- Retained all 99,441 orders in an audit table.
- Prepared 86,484 approval-time feature rows with 54 numeric columns.
- Fitted medians, IQR bounds, scaling parameters, and category vocabularies only
  on training approvals before 1 January 2018.
- Retained missing outcomes without inventing delivery dates or targets.
- Passed ten independent categories of artifact verification.

**The preprocessing was executed. No prediction model was trained, and no
operational improvement is claimed.** All counts describe the retrieved source
snapshot and the defined eligibility rules, not current Olist performance.

## Main deliverables

- `reports/Week_2_Report.docx`: the Word report required by the internship portal.
- `reports/Submission_Description.txt`: 225 words for the description field.
- `results/orders_audit.csv.gz`: all orders, raw-derived values, quality flags,
  metric eligibility, and split membership.
- `results/prepared_features.csv.gz`: numeric feature matrix.
- `results/feature_index_and_labels.csv.gz`: matching row identifiers, split,
  label eligibility, and target values; **do not use labels with false eligibility**.
- `results/audit_summary.json`: measured source issues and processing counts.
- `results/preprocessing_parameters.json`: saved training parameters and schema.
- `results/preprocessing_counts.csv`: per-feature, per-split transformation counts.
- `results/before_after_examples.csv`: actual records illustrating transformations.
- `results/verification.json`: independent verification results.

The three large CSV files are gzip-compressed for storage. Pandas can read them
directly, for example `pd.read_csv("results/orders_audit.csv.gz")`. The feature
matrix and identifier/label file have the same row order; keep them aligned.

## Reproduce the work

Tested with Python 3.12.14, pandas 3.0.1, and NumPy 2.3.5. Use Python 3.12 for
the same environment. From this project folder:

```text
python -m pip install -r requirements.txt
python download_data.py
python preprocess.py
python verify_results.py
```

The first command installs dependencies. The download script fetches four raw
CSV files from the fixed public commit into `data/`. The processing script writes
uncompressed CSV outputs and audit JSON to `results/`. The verification script
checks those regenerated files independently. Raw CSV files are not bundled;
their source URLs and original checksums are included in the manifest.

## Cleaning decisions

1. Load source keys as strings and validate unique grains.
2. Audit duplicates, missingness, timestamp parsing, and numeric ranges.
3. Mark four nonpositive product weights as missing in the working copy.
4. Aggregate item values before joining, preserving incomplete totals as missing.
5. Keep negative-duration flags and mask only the affected derived interval.
6. Keep all orders for audit; select valid approvals in the calendar windows for X.
7. Fill numeric predictor gaps with training medians and add missing indicators.
8. Flag IQR extremes without deleting legitimate high-value, heavy, or slow orders.
9. Apply log1p to monetary/physical totals, then training-fitted min-max scaling.
10. One-hot encode state and weekday with missing/unknown categories.
11. Validate, export, and independently reconstruct key calculations.

Missing outcomes are not imputed. Genuine extremes are not capped. Sixteen
held-out feature cells fall outside the fitted min-max range; they are preserved
and counted. Scaling does not itself fix outliers or imply improved accuracy.

## Chronological cohorts

| Approval window | Feature rows | Eligible labels |
| --- | ---: | ---: |
| Before 2018-01-01 | 45,295 | 41,173 |
| 2018-01-01 through 2018-03-31 | 21,181 | 16,837 |
| 2018-04-01 through 2018-06-30 | 20,008 | 19,654 |

Training labels must be observed before January 2018, validation labels before
April 2018, and test labels before September 2018. The feature fit uses all valid
training approvals without labels. Future modeling must respect label eligibility
and assess unequal follow-up; this static snapshot cannot prove all attributes
were unchanged after approval.

## Sources and attribution

Source: [Olist work-at-olist-data](https://github.com/olist/work-at-olist-data).
Fixed commit: `d9e49802f3e92d09ee94ab9ccc5e457f207a8959`.
Original retrieval date: 22 October 2026.

The repository's MIT license notice is retained in `data/LICENSE`, together with
its README. Prepared data are derived from these attributed source records;
retain the source notice when redistributing them. No claim is made that this
snapshot is byte-identical to every Kaggle release.

The report cites official pandas and scikit-learn methodology documentation.
Numeric normalization was implemented with pandas/NumPy arithmetic; scikit-learn
is not needed to run this project.


## Place in the four week project

This folder is a self-contained weekly snapshot within the shared LogiTrack repository. Prepared data are repeated where needed to preserve independent reproduction and the original result hashes. See the [project overview](../README.md) for the complete progression.
