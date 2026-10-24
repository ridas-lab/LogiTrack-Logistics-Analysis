# Data sources and attribution

## Historical benchmark

Source: [olist/work-at-olist-data](https://github.com/olist/work-at-olist-data), fixed commit [d9e49802f3e92d09ee94ab9ccc5e457f207a8959](https://github.com/olist/work-at-olist-data/tree/d9e49802f3e92d09ee94ab9ccc5e457f207a8959). Retrieved 22 October 2026.

Four source tables were used: orders (99,441 rows), order items (112,650), customers (99,441), and products (32,951). Week 2 aggregates item records before joining at order grain. Later weeks reuse the resulting audit table and feature data. The historical Brazilian marketplace records do not establish current company performance.

The upstream MIT notice is retained in [Week 2](week-2-data-preparation/data/LICENSE), [Week 3](week-3-analysis-visualization/data/SOURCE_LICENSE.txt), and [Week 4](week-4-modeling-optimization/data/SOURCE_LICENSE.txt). Preserve these notices with the attributed source material. No additional blanket license is assigned here to the authored reports and code.

Original acquisition URLs and checksums are retained in the weekly source manifests. Compressed and uncompressed hashes appear in the Week 3 and Week 4 provenance files. Some prepared datasets appear more than once to maintain independent weekly execution. Their underlying data bytes are preserved.

## Hypothetical shipments

Week 3 generates 2,000 shipments with seed 20261022; Week 4 reuses them. Dispatch dates, distance, weight, units, and added delay follow explicit rules. Delivery duration is `1 + distance_km/300 + extra_delay_days`. The transportation-cost formula is an assumption for illustration. These records are generated examples, not additional Olist observations. They never enter the historical regression or its evaluation.

## Interpretation

Completed-order accuracy excludes unusable or unavailable outcome labels and reports coverage. The review-allocation example selects across all eligible test approvals, then evaluates known outcomes. Selection is not evidence of prevented delays, causal effects, or savings. Approval-time feature availability must be checked in operational snapshots before deployment.
