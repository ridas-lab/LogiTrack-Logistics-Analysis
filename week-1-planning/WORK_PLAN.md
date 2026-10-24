# Week 1 work explained step by step

Week 1 is the planning phase. The report specifies what to study, how to measure
it, which data to use, and how the future analysis should work.

## Step 1 Define the problem

The hypothetical ecommerce business wants to understand delayed deliveries and
decide which orders staff should review first. Its example capacity is 100 reviews
per day; that number is an assumption, not information measured from Olist.

## Step 2 Define the objectives

Measure delivery performance, investigate delay stages, predict remaining delivery
time, and allocate staff attention. The proposed solution helps operations decide
where to investigate and how to prioritize work.

## Step 3 Choose five KPIs

The report defines on-time delivery rate, order cycle time, seller dispatch lead
time, recorded freight per order, and delivered milestone completeness.
Each definition states which orders can be included. No real baseline has yet
been calculated.

## Step 4 Identify a public data source

The report identifies the Olist historical Brazilian ecommerce dataset and
explains relevant order, item, customer, seller, product, and geographic data.
Source descriptions were researched; the complete CSV dataset has not been
downloaded or analyzed in this project.

## Step 5 Plan cleaning and exploration

Validate identifiers and timestamps, record missing values, aggregate item rows
before joining orders, and avoid counting an order more than once. Then examine
monthly trends, seller and destination differences, and dispatch versus transit
durations. These steps are specified for future execution.

## Step 6 Select analysis methods

- Regression estimates remaining delivery days at approval.
- Clustering groups orders with similar characteristics.
- Review allocation prioritizes orders within available staff capacity.

Only information known at approval can enter an approval-time prediction. Future
delivery dates may be labels for evaluation, but must not become input features.

## Step 7 Illustrate the Python approach

The report includes an actual pandas KPI function and explicitly labeled
pseudocode for model evaluation and review allocation. The KPI function was
checked with fictional examples for same-day delivery, multiple items, missing
freight, duplicate records, and empty eligible groups. No predictive model was
trained on the Olist dataset.

## Step 8 Set the roadmap and expected outcomes

Week 1 defines the project. Later phases acquire and clean data, calculate
baselines, explore patterns, fit and evaluate models, and simulate allocation.
A controlled operational pilot is needed to establish whether reviews improve
service. The proposed percentage improvements are goals, not achieved results.

## Step 9 Publish the prepared work

Upload these files to a GitHub repository. GitHub stores and displays the files;
uploading them does not automatically run the Python demonstration or perform the
planned analysis. The README is the project explanation visitors see first.

## Step 10 Submit

Upload the Word report to the internship portal, paste the repository URL into
the GitHub field, and paste the supplied description into its separate field.
The portal submission and the GitHub upload are separate actions.
