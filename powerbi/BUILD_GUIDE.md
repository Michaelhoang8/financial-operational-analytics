# Build the Power BI report

The ready-to-open PBIP is in `native/Financial_Operational_Analytics.pbip`. Open it in Desktop and click Refresh; no external datasource credentials are required. The supplied model was refreshed and all 28 measures executed successfully. `reports/powerbi_validation_results.json` records 18 comparisons to SQL.

Rebuild with `python src/build.py` then `python src/build_powerbi.py`. Keep Desktop closed while rebuilding. CSV fixtures are embedded as base64 in M partitions; they are synthetic and readable under `data/model`. No PBIX or Power BI Service deployment is included.

## Alternative manual assembly

These steps explain how to reconstruct the model from CSV files instead of using the bundled PBIP.

1. Open Power BI Desktop, select Transform data, and create the text parameter `DataFolder` pointing to this project's `data/model` folder.
2. Create blank query `LoadModelCsv`. Paste `import_function.pq` into Advanced Editor.
3. Create eight blank queries named `DimDate`, `DimBranch`, `DimAccount`, `DimProduct`, `FactActual`, `FactBudget`, `FactInventory`, and `FactOrders`. For each, enter `= LoadModelCsv("TableName")`, replacing TableName with its exact query name. Close & Apply.
4. Remove any automatically inferred relationships and configure the relationships below. Use active one-to-many relationships, single filter direction from dimension to fact. Never connect fact tables directly.
5. Mark DimDate as the date table using Date. Sort YearMonth by its text value (ISO format sorts chronologically). Disable automatic date/time for this file. Use Year and YearMonth slicers; facts are monthly even though the date dimension is daily.
6. Add the measures in `measures.dax` individually. Format currency measures as CAD, ratios as 0.0%, and counts as whole numbers. Hide fact numeric columns and keys from report consumers.
7. Import `theme.json` under View > Themes. Create the pages below. Save as `Financial_Operational_Analytics.pbix` in this folder.

## Relationships and grain

| Dimension key | Fact foreign key | Grain / coverage |
|---|---|---|
| DimDate.Date | Date in all four facts | Daily dimension, complete 2024–2025 calendar |
| DimBranch.BranchKey | BranchKey in all four facts | Three branches |
| DimAccount.AccountKey | AccountKey in Actual and Budget | Five management P&L accounts |
| DimProduct.ProductKey | FactInventory.ProductKey | Twelve SKUs; inventory only |

FactActual: one accepted transaction ID; ten postings per account, branch and month. FactBudget: one month-end / branch / account. FactInventory: one month-end / branch / product snapshot. FactOrders: one order, assigned to a reporting month. PromisedDate and ShippedDate are informational attributes, with no active calendar relationships.

Product slicers belong only on the inventory page because financial and order records do not contain product allocations. Account slicers belong only on the financial detail page. Otherwise a slicer can appear to affect a measure it cannot filter. Each snapshot month is complete across products and branches; sparse real snapshots would need a revised as-of policy.

## Report pages

1. **Executive overview:** Year and Branch slicers; Revenue, Operating Profit, Profit Variance, On-Time Delivery % cards; YearMonth revenue/budget clustered column chart; branch profit variance bar chart; monthly financial matrix. Use green for positive favorable variance and red for negative.
2. **Budget and cost control:** Year, YearMonth and Branch slicers; account rows with Actual Amount, Budget Amount and Favorable Account Variance; monthly operating profit trend. All amounts are positive magnitudes. Revenue actual minus budget is favorable; expense budget minus actual is favorable.
3. **Inventory and operations:** Year, YearMonth and Branch slicers; Closing Inventory, Closing Units and On-Time Delivery %; inventory by SKU and branch; on-time rate by month. Put any Product slicer in an inventory-only visual group and disable its interactions with order visuals.

## Native validation checklist

- Compare full-year 2025 Revenue and Operating Profit with `reports/management_brief.md`.
- Compare each branch and year with `reports/dashboard_data.json`; verify combined rates use summed numerators and denominators.
- Inventory total for 2025 must equal December, not the sum of twelve months; January selection must show January.
- Check 2025 prior-year Revenue against 2024. 2024 prior-year measures should be blank.
- Confirm account expense variance changes sign appropriately and zero budgets return blank percentage.
- Refresh and confirm all eight tables load without errors. Test slicer interactions and capture three page screenshots.

## Sources

Design reference: [Microsoft star-schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema). Relationship reference: [Microsoft model relationships](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-relationships-understand). These are technical references; the data is locally generated using seed 42.
