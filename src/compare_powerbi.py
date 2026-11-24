import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
actual=json.loads((root/'reports/powerbi_native_results.json').read_text(encoding='utf-8-sig'))
expected=json.loads((root/'reports/dashboard_data.json').read_text())
lookup={(r['YearMonth'],r['Branch']):r for r in expected}
checks={}
checks['all_72_branch_months_present']=len(actual['monthly'])==len(lookup)==72
for key in ['Revenue','BudgetRevenue','Profit','BudgetProfit','Freight','Inventory','Orders','OnTime']:
 checks[key+'_matches_SQL_all_72_rows']=all(abs(r[key]-lookup[(r['Month'],r['Branch'])][key])<.005 for r in actual['monthly'])
checks['delivery_rates_weighted']=all(abs(r['Rate']-r['OnTime']/r['Orders'])<1e-10 for r in actual['monthly'])
for r in actual['annual']:
 year=r['Year'];yr=[e for e in expected if e['Year']==year];last=[e for e in yr if e['YearMonth'].endswith('-12')]
 checks[f'{year}_closing_inventory_is_December']=abs(r['Inventory']-sum(e['Inventory'] for e in last))<.005
 checks[f'{year}_YTD_matches_annual_revenue']=abs(r['RevenueYTD']-sum(e['Revenue'] for e in yr))<.005
 if year==2024:checks['first_year_prior_is_blank']=r['Prior'] is None
 else:checks['2025_prior_year_matches_2024']=abs(r['Prior']-sum(e['Revenue'] for e in expected if e['Year']==2024))<.005
checks['account_variance_direction']=all(abs(r['Favorable']-((r['Actual']-r['Budget']) if r['Category']=='Revenue' else (r['Budget']-r['Actual'])))<.005 for r in actual['accounts'])
checks['all_28_measures_executed']=actual['measureCount']==28
assert all(checks.values()),checks
(root/'reports/powerbi_validation_results.json').write_text(json.dumps(checks,indent=2))
print(f'{len(checks)} native Power BI validation checks passed.')
