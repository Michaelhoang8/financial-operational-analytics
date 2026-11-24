# First-person portfolio walkthrough

Use this narrative to explain the supplied implementation after reviewing and running it. It describes a synthetic personal project, not work for a real employer.

“I built a financial and operational analytics portfolio project for a fictional distribution business. I created two years of repeatable source data covering three branches, financial actuals and budgets, order delivery, and inventory snapshots.

I used SQL to identify duplicate and invalid financial records, preserve an exception log, and prepare reporting facts. I kept budget, transactions, orders and inventory at separate grains. Before comparing them, I aggregated each source to month and branch to prevent duplicated totals.

I produced a working interactive dashboard and a management brief from the validated model. The scenario highlighted Vancouver's freight pressure and budget shortfall, and I proposed targeted investigation rather than claiming savings that had not been measured.

I also prepared Power Query import logic, a star-schema relationship plan and DAX measures for the Power BI version. The native project now includes three pages and 28 measures. Desktop execution passed 18 SQL comparison checks.”

## Questions to prepare for

- **Why separate inventory?** It is a point-in-time balance. Adding January and February stock does not give meaningful closing inventory.
- **Why use cents?** Integer storage preserves exact ledger reconciliation and avoids binary floating-point monetary drift.
- **Why not join raw facts?** Many transactions, orders and products share the same branch/month. Joining them directly multiplies rows and inflates totals.
- **How did you measure delivery?** Sum on-time flags divided by count of orders, which weights branches by their order counts.
- **What did you validate?** Referential keys, duplicate IDs, known exceptions, source reconciliation, stock valuation, delivery date rules and revenue totals.
- **What remains?** Desktop validation, native visuals and any deployment or stakeholder testing. No production adoption or time-saving claim has been measured.

Native screenshots and executed DAX results are included. Keep synthetic data provenance in the portfolio.
