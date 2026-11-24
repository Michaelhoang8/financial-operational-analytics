DROP VIEW IF EXISTS MonthlyReview;
CREATE VIEW MonthlyReview AS
SELECT c.Period,c.FiscalYear,c.Agency,c.Actual,c.Plan,
       c.Plan-c.Actual AS Variance,
       CASE WHEN c.Plan=0 THEN NULL ELSE (c.Plan-c.Actual)/ABS(c.Plan) END AS VarianceRate,
       y.Actual AS YTDActual,y.Plan AS YTDPlan,c.Publication
FROM Obligations c
LEFT JOIN Obligations y ON y.Period=c.Period AND y.Agency=c.Agency AND y.Basis='Year-to-Date'
WHERE c.Basis='Current';
