-- SQLite 3 dialect. Source amounts are positive magnitude CAD cents.
-- Rank identical ingestion duplicates; production conflicting IDs require investigation.
DROP TABLE IF EXISTS QualityExceptions;
CREATE TABLE QualityExceptions AS
WITH ranked AS (SELECT *, ROW_NUMBER() OVER(PARTITION BY TransactionID ORDER BY rowid) AS rn FROM RawLedger)
SELECT TransactionID, Date, BranchKey, AccountKey,
 CASE WHEN rn>1 THEN 'Duplicate transaction ID'
 WHEN BranchKey NOT IN(SELECT BranchKey FROM DimBranch) THEN 'Unknown branch'
 WHEN AccountKey NOT IN(SELECT AccountKey FROM DimAccount) THEN 'Unknown account'
 WHEN Date NOT IN(SELECT Date FROM DimDate) THEN 'Unknown date'
 ELSE 'Missing amount' END AS Reason, AmountCents
FROM ranked WHERE rn>1 OR BranchKey NOT IN(SELECT BranchKey FROM DimBranch)
 OR AccountKey NOT IN(SELECT AccountKey FROM DimAccount)
 OR Date NOT IN(SELECT Date FROM DimDate) OR AmountCents IS NULL;
DROP TABLE IF EXISTS FactActual;
CREATE TABLE FactActual AS
WITH ranked AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY TransactionID ORDER BY rowid) AS rn FROM RawLedger)
SELECT TransactionID,Date,BranchKey,AccountKey,AmountCents FROM ranked
WHERE rn=1 AND BranchKey IN(SELECT BranchKey FROM DimBranch)
AND AccountKey IN(SELECT AccountKey FROM DimAccount)
AND Date IN(SELECT Date FROM DimDate) AND AmountCents IS NOT NULL;
CREATE UNIQUE INDEX ActualID ON FactActual(TransactionID);
DROP VIEW IF EXISTS MonthlyPerformance;
CREATE VIEW MonthlyPerformance AS
WITH a AS (
 SELECT Date,BranchKey,SUM(CASE WHEN AccountKey=4000 THEN AmountCents ELSE 0 END)/100.0 Revenue,
 SUM(CASE WHEN AccountKey=5000 THEN AmountCents ELSE 0 END)/100.0 COGS,
 SUM(CASE WHEN AccountKey>=6100 THEN AmountCents ELSE 0 END)/100.0 Opex,
 SUM(CASE WHEN AccountKey=6200 THEN AmountCents ELSE 0 END)/100.0 Freight
 FROM FactActual GROUP BY Date,BranchKey),
b AS (
 SELECT Date,BranchKey,SUM(CASE WHEN AccountKey=4000 THEN AmountCents ELSE 0 END)/100.0 BudgetRevenue,
 SUM(CASE WHEN AccountKey=4000 THEN AmountCents ELSE -AmountCents END)/100.0 BudgetProfit,
 SUM(CASE WHEN AccountKey=6200 THEN AmountCents ELSE 0 END)/100.0 BudgetFreight
 FROM FactBudget GROUP BY Date,BranchKey),
i AS (SELECT Date,BranchKey,SUM(ValueCents)/100.0 Inventory FROM FactInventory GROUP BY Date,BranchKey),
o AS (SELECT Date,BranchKey,COUNT(*) Orders,SUM(OnTime) OnTime FROM FactOrders GROUP BY Date,BranchKey)
SELECT a.Date,d.Year,d.YearMonth,br.Branch,a.Revenue,a.COGS,a.Opex,a.Freight,
a.Revenue-a.COGS-a.Opex Profit,b.BudgetRevenue,b.BudgetProfit,b.BudgetFreight,i.Inventory,o.Orders,o.OnTime
FROM a JOIN b USING(Date,BranchKey) JOIN i USING(Date,BranchKey) JOIN o USING(Date,BranchKey)
JOIN DimDate d ON a.Date=d.Date JOIN DimBranch br ON a.BranchKey=br.BranchKey;
-- Aggregate each fact to a common grain BEFORE joining to prevent fan-out.
