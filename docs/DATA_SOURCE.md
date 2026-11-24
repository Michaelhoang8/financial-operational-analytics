# Data source and transformation policy

Publisher: NYC OMB Financial Plan Statements — Obligation

Dataset: https://data.cityofnewyork.us/d/hjjq-k984

Size: 3,304 published observations across 66 reporting months

Retrieved UTC: 2026-11-24T19:41:10.875163+00:00

Download: https://data.cityofnewyork.us/api/views/hjjq-k984/rows.csv?accessType=DOWNLOAD

Original SHA-256: `601572b62a283547f52e70fcb3f34f23e5693d2604bacedfef7a1ef681040f9c`

Reuse/attribution reference: https://cityofnewyork.github.io/opendatatsm/publicpolicies.html. Government sources are published for public reuse under their portal terms; this repository does not relicense the source data as project code. UCI Online Retail II is attributed to Daqing Chen (2012), DOI 10.24432/C5CG6D, under CC BY 4.0. No source publisher endorses this analysis.

The raw government CSV is gzip-compressed without altering field content. UCI's workbook is converted by the included XML streaming converter into a lossless-field CSV, with explicit sheet and row references and Excel dates converted to ISO timestamps. The original workbook download is available through the source manifest; the large ZIP is not committed.

## Grain, calculations and limitations

Current-month obligations, plan-minus-actual variance, and a separate cumulative YTD snapshot. Latest-publication selection prevents revision double-counting. Fiscal years start in July.

No revenue, profit, inventory, delivery data or complete annual expense totals are claimed. June and other missing observations are not filled. Amounts are source-rounded USD millions.

Pinned snapshots make builds reproducible. A new upstream download must be reviewed as a new data version: update its manifest and checksums, rebuild outputs, re-review AI claims where applicable and recapture media. Never silently change a pinned snapshot.
