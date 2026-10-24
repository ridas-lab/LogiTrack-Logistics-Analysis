# Week 4 Predictive Modeling and Optimization in Logistics

[Project overview](../README.md) · [Word report](reports/Rida_Sahin_Week_4_Predictive_Modeling_and_Optimization_Report.docx) · [Submission description](Submission_Description.txt)

Prepared for Rida Sahin's Logistics Data Analyst Internship, 23 October 2026.

This project forecasts approval-to-delivery duration and demonstrates a daily order-review allocation rule. It includes executed Python analysis, a Word report, six embedded Matplotlib and Seaborn figures, and a separate hypothetical shipment experiment.

## What was completed

1. Reused the audited order-level data and training-fitted feature transformations from Week 2.
2. Created chronological cohorts, retaining at least 60 days of outcome follow-up at each cutoff.
3. Trained ten candidate regressors, including median/mean baselines, Ridge, decision trees, and gradient boosting.
4. Selected the lowest mature-validation MAE and froze that fitted model before final testing.
5. Measured test errors, variation across months and states, and long-delay weaknesses.
6. Calculated validation-only grouped permutation importance and a promise-removal diagnostic.
7. Allocated a fixed 100 reviews per active day and compared the ranking with FIFO at identical capacity.
8. Evaluated a separate 2,000-row simulated shipment model.
9. Exported charts, interpretations, code, data, and a submission description.

## Main results

The selected 15-leaf histogram gradient boosting model has mature validation MAE 5.234 days. Final test MAE is 4.667 days, RMSE 6.641 days, and R squared 0.257 across 19,654 eligible completed orders. The training-median baseline test MAE is 5.397 days. The small validation advantage over Ridge is not evidence of significant superiority.

At 100 reviews/day, both policies select 8,765 of 20,008 approvals. Model priority selects 428 known late orders; FIFO selects 355. Their selected outcome-unknown counts are 170 and 128 respectively. This identifies observed late outcomes; it does not establish prevented delays or savings. Only seven scores are positive, so the remaining selections rank the least predicted slack.

## Files

- `reports/`: uploadable Word report and submission description.
- `model.py`: actual model training, selection, evaluation, simulation modeling, and allocation.
- `make_charts.py`: six figures using Matplotlib and Seaborn, saved as PNG and PDF.
- `verify_results.py`: independent checks against original order timestamps and saved predictions.
- `data/`: compressed prepared inputs, original order records for verification, source license, preprocessing parameters, and checksums.
- `results/`: saved predictions, metrics, model, selection settings, cohort counts, and verification results.
- `figures/`: readable chart images already supplied.
- `preparation/`: original acquisition/preparation scripts and the exact synthetic generator.

![Validation comparison](figures/01_validation_comparison.png)

![Allocation comparison](figures/05_review_allocation.png)

## Run the analysis

Tested with Python 3.12.14. Open a terminal in this extracted project folder. Install dependencies into your Python environment and run:

```powershell
python -m pip install -r requirements.txt
python model.py --data data --output results
python make_charts.py --results results --output figures
python verify_results.py --data data --results results
```

The included CSV inputs remain compressed; pandas reads them directly. Model training may take a few minutes. If using a machine with many CPU cores, setting `OMP_NUM_THREADS` to `4` before launching Python can avoid unnecessary overhead. The code saves results deterministically with seed 20261023, subject to small platform differences. The supplied figures and report are usable without rerunning the code. Re-running analysis does not automatically rewrite the Word report.

The saved joblib object contains a fitted estimator, feature order, and plan. It is not a complete live production service; new raw orders would first need the same preparation rules. Only load model files from sources you trust.

## Understand the method

- **MAE:** average absolute forecast error in days; lower is better.
- **RMSE:** error in days with a stronger penalty for large mistakes.
- **R squared:** comparison with a constant sample-mean prediction, not percentage accuracy.
- **Validation:** later data used to choose the model.
- **Test:** an additional later period used only after selection.
- **Outcome maturity:** allowing time for deliveries to complete before measuring them.
- **Optimization:** choosing which orders receive a fixed number of review slots.
- **Simulation:** generated examples governed by explicit assumptions, not real observations.

Training uses 30,932 eligible labels on approvals before 2 November 2017, observed before 1 January 2018. Validation uses 6,753 labels on 1–30 January approvals, observed before 1 April. Test uses 19,654 labels from April–June approvals, observed before 1 September. The 60-day rule reduces, but does not eliminate, completion selection bias. Preprocessing was fitted on all 45,295 eligible pre-January approval feature rows without validation/test data.

Review allocation is an end-of-day batch simulation. The objective is maximum total predicted-minus-promised duration with exactly min(capacity, daily orders) selections. It is a ranking score, not a probability or a causal treatment benefit. A live queue needs arrival scheduling, current order status, and an intervention study. The model underpredicts all 488 test deliveries longer than 30 days, with MAE 23.39 days in that group.

## Source and reproducibility

Historical source: [Olist official repository](https://github.com/olist/work-at-olist-data), commit `d9e49802f3e92d09ee94ab9ccc5e457f207a8959`, retrieved 22 October 2026. Preserve `data/SOURCE_LICENSE.txt` when reusing the source. Data are historical Brazilian marketplace records and do not establish current logistics performance.

`data/source_manifest.json` records the original files. `data/provenance.json` records compressed and uncompressed hashes of packaged inputs. The original summary identifies uncompressed model input bytes; a rerun on gzip files records those compressed bytes instead. The source-content hashes can therefore be checked using the matching form.

Optional source rebuild, requiring internet:

```powershell
python preparation/download_data.py --data-dir preparation/data
python preparation/preprocess.py --data-dir preparation/data --output-dir preparation/results
python preparation/generate_simulation.py --output preparation/results
python model.py --data preparation/results --output rebuilt_results
```

The simulator uses seed 20261022 in the original draw order. It outputs 2,000 July 2026 shipments with target `1 + distance_km/300 + extra_delay_days`. The fixed Ridge experiment uses distance, weight and units only. Outcome-derived cost and delay fields are excluded. The synthetic results are kept separate from the historical results.


## Place in the four week project

This folder is a self-contained weekly snapshot within the shared LogiTrack repository. Prepared data are repeated where needed to preserve independent reproduction and the original result hashes. See the [project overview](../README.md) for the complete progression.
