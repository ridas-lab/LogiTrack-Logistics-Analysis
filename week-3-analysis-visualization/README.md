# Week 3 Logistics Analysis and Visualization

[Project overview](../README.md) · [Word report](Rida_Sahin_Week_3_Logistics_Analysis_and_Visualization_Report.docx) · [Submission description](Submission_Description.txt)

Prepared for Rida Sahin's Logistics Data Analyst internship.

This project examines delivery performance for a hypothetical ecommerce marketplace using historical Olist orders as a benchmark. It also includes a separate simulated shipment dataset for transportation-cost experiments. The Word report contains the analysis, eight embedded figures, interpretations, code excerpts, and recommendations.

## What was completed

1. Loaded the order-level audit data prepared during Week 2 and checked that each order appears once.
2. Defined a valid population for each calculation, so incomplete or invalid records do not silently distort the results.
3. Calculated central tendencies, variation, percentiles, and delivery performance.
4. Compared monthly demand, delivery-time distributions, destination states, and stages of the delivery process.
5. Examined associations between freight charges, product weight and volume, merchandise value, item count, and delivery time.
6. Created a separate set of 2,000 hypothetical shipments and tested two illustrative changes to an assumed transportation-cost formula.
7. Produced chart images, supporting tables, an uploadable Word report, and a submission description.

## Main findings

| Measure | Result | Population |
|---|---:|---|
| Orders in the audit data | 99,441 | All source orders |
| Eligible completed orders | 96,470 | Delivered orders with valid cycle evidence |
| On-time delivery | 93.23% | 89,936 of 96,470 eligible orders |
| Median delivery cycle | 10.22 days | 96,470 eligible completed orders |
| 90th percentile delivery cycle | 23.10 days | 96,470 eligible completed orders |
| Carrier transit share of mean elapsed time | 74.21% | 95,082 delivered orders with valid stage evidence |

São Paulo and Rio de Janeiro together account for 50.73% of late orders. This supports investigating high-volume destinations alongside destinations with lower on-time rates. These results do not prove that a particular carrier or process caused the delays.

The hypothetical shipment experiment has a mean transportation cost of BRL 39.53 per shipment. Reducing the assumed distance input by 10% lowers this modeled mean by BRL 2.19; removing up to one extra delay day lowers it by BRL 1.40. These are separate scenarios calculated from an assumed formula, not measured savings or combined intervention effects.

## Understand the data

The historical data originates from [Olist's official repository](https://github.com/olist/work-at-olist-data), fixed at commit `d9e49802f3e92d09ee94ab9ccc5e457f207a8959`. The Week 2 workflow joined orders, order items, customers, and products at order level. The original retrieval manifest and source license accompany this package. The historical purchase dates span September 2016 to October 2018; the monthly trend uses January 2017 through June 2018.

`data/orders_audit.csv.gz` is a compressed copy of the prepared audit table. Python reads this file directly; it does not need manual extraction. The analysis uses observed, unscaled values, not the imputed feature matrix prepared for possible predictive modeling. File checksums in the original source manifest refer to the original downloaded source files; `results/summary.json` records the analysis input checksum separately.

Freight is a recorded customer charge, not a measured operating cost. Product dimensions estimate product volume, not packed parcel volume. Order and item counts describe demand; the benchmark does not establish the exact number of physical parcels or vehicle trips.

`results/hypothetical_shipments.csv` is entirely simulated using the fixed random seed 20261022. It contains shipment dates, distances, weights, item units, delivery days, promises, and transportation costs. Its cost formula is:

```text
Cost in BRL = 12 + 0.035 × distance in km
             + 1.2 × weight in kg + 4 × extra delay days
```

These coefficients are illustrative assumptions. No simulated record is combined with the historical benchmark when calculating observed performance.

## Files in the project

- `README.md`: this explanation and the upload instructions.
- `analyze.py`: descriptive analysis and hypothetical shipment simulation.
- `make_charts.py`: chart generation from calculated results.
- `verify_outputs.py`: independent verification of 543 numerical results and consistency checks.
- `preparation/`: source acquisition and Week 2 preparation scripts for tracing the audit data.
- `data/`: compressed prepared input, provenance, and source license.
- `results/`: statistical tables, correlations, simulation records, and summary.
- `figures/`: the chart images and PDF versions.
- The Word report: the file to upload to the internship portal.
- The submission description: text to paste into the portal's description field.

## Run the analysis again

The supplied results and report are ready to review. Running Python is useful if you want to reproduce the calculations or change the experiment.

Use Python 3.12. The original run used pandas 3.0.1, NumPy 2.3.5, and ReportLab 4.4.9. Open a terminal in the extracted project's main folder, the folder containing `analyze.py`.

```powershell
python -m pip install pandas==3.0.1 numpy==2.3.5 reportlab==4.4.9
python analyze.py --input data/orders_audit.csv.gz --output results
python make_charts.py --results results --output figures
python verify_outputs.py --input data/orders_audit.csv.gz --results results
```

The chart script produces PDF figures. To regenerate the PNG images as well, install Poppler and supply the location of its `pdftoppm` program:

```powershell
python make_charts.py --results results --output figures --pdftoppm "C:/path/to/pdftoppm.exe"
```

Replace the example path with the real location on your computer. PNG images are already included, so this optional conversion is unnecessary for submission. Re-running analysis scripts does not automatically rewrite the Word report; update its narrative if you change the data or assumptions.

## Explain the work in simple terms

- **Exploratory data analysis:** looking at the data to understand typical performance, variation, unusual cases, and relationships.
- **Median:** the middle value; half the eligible deliveries took no more than about 10.22 days.
- **90th percentile:** about 90% of eligible deliveries took no more than 23.10 days.
- **On-time rate:** the percentage delivered on or before the promised calendar date.
- **Correlation:** two values tend to move together. It does not establish why that happens.
- **Simulation:** made-up records generated by explicit rules to explore an example. Simulation results describe those rules, not a real company's outcomes.

Be ready to explain why each chart helps a logistics decision, why different charts can use different valid populations, and why proposed actions still need operational testing. The project completed exploratory analysis; it did not train a predictive model or implement an operational intervention.

## Rebuild the historical audit input from the original source

This optional path requires internet access and is not needed for submission. Run from the project root:

```powershell
python preparation/download_data.py --data-dir preparation/data
python preparation/preprocess.py --data-dir preparation/data --output-dir preparation/results
python analyze.py --input preparation/results/orders_audit.csv --output rebuilt_results
python verify_outputs.py --input preparation/results/orders_audit.csv --results rebuilt_results
```

The original source file hashes are in `data/source_manifest.json`. Hashes of the packaged audit CSV, both compressed and uncompressed, are in `data/provenance.json`. The hash in `results/summary.json` identifies the exact compressed input used for the packaged rerun. The original source license is retained in `data/SOURCE_LICENSE.txt`.

The independent verifier passed all 543 checks on the packaged compressed input. Statistical tables agree with the report. The PNG figures are already supplied, so you can inspect the project without installing plotting or conversion tools.

## Visualization implementation

This week used ReportLab to draw the charts and Poppler to export PNG images. Week 4 uses Matplotlib and Seaborn. Eight chart images are embedded in this week's Word report.

## Place in the four week project

This folder is a self-contained weekly snapshot within the shared LogiTrack repository. Prepared data are repeated where needed to preserve independent reproduction and the original result hashes. See the [project overview](../README.md) for the complete progression.
