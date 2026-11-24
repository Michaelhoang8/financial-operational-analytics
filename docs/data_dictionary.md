# Data dictionary and lineage

Lineage: seeded Python records → raw CSVs / SQLite tables → SQL ranking and validation → FactActual and MonthlyPerformance → model CSV exports → browser report; Power Query can import the CSV model into Power BI.

| Field | Definition |
|---|---|
| TransactionID | Financial source record business key; ingestion duplicate intentionally injected |
| Date | ISO reporting date; facts posted at month-end; daily in DimDate |
| Year, Month, Quarter, YearMonth | Calendar reporting attributes; YearMonth is YYYY-MM |
| BranchKey, Branch | Branch identifier and display name |
| AccountKey, Account, Category | Financial account ID, name and Revenue / COGS / Opex category |
| AmountCents | Positive revenue or expense magnitude in CAD cents; missing values invalid |
| ProductKey, SKU | Inventory product identifier and display code |
| DimProduct.Category | Industrial, Safety or Office product category; unrelated to account category |
| StandardCost | Product standard cost in CAD dollars |
| Units | Month-end quantity on hand |
| UnitCostCents, ValueCents | Standard unit cost and extended stock value in CAD cents |
| OrderID | Unique order; generated at 100 per branch per reporting month |
| PromisedDate, ShippedDate | ISO dates used to classify delivery timeliness |
| OnTime | 1 when shipped on or before promised date, otherwise 0 |
| Reason | Quarantine reason; duplicate, unknown branch, or missing amount in current dataset |

RawLedger has 3,603 rows; accepted FactActual has 3,600. FactBudget has 360 rows; FactInventory 864; FactOrders 7,200. Date dimension has 731 dates, including leap day. MonthlyPerformance has 72 rows (24 months × 3 branches).

Deduplication policy: preserve first ingestion row for repeated IDs. This simulation contains only an exact duplicate. A production source should distinguish exact replay from conflicting corrections using source version and timestamp, rather than silently taking the first row. Missing monetary values are not imputed as zero. The quarantine amount total excludes null because its value is unknown; report the missing count alongside monetary reconciliation.
