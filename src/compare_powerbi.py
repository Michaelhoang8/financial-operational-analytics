import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
native=json.loads((root/'reports/powerbi_native_results.json').read_text(encoding='utf-8-sig'))
sql=json.loads((root/'reports/dashboard_data.json').read_text());lookup={(r['Period'],r['Agency']):r for r in sql}
checks={'all_agency_months_present':len(native['monthly'])==len(sql)}
for key in ['Actual','Plan','Variance','YTDActual','YTDPlan']:
 checks[key+'_matches_SQL']=all(abs(r[key]-lookup[(r['Period'],r['Agency'])][key])<.000001 for r in native['monthly'])
overall=native['overall'];overall=overall[0] if isinstance(overall,list) else overall
latest=max(r['Period'] for r in sql)
checks['YTD_total_is_latest_snapshot']=abs(overall['YTDActual']-sum(r['YTDActual'] for r in sql if r['Period']==latest))<.000001
checks['YTD_plan_is_latest_snapshot']=abs(overall['YTDPlan']-sum(r['YTDPlan'] for r in sql if r['Period']==latest))<.000001
checks['reported_month_count']=overall['Months']==len({r['Period'] for r in sql})
checks['all_ten_measures_executed']=native['measureCount']==10
assert all(checks.values()),checks
(root/'reports/powerbi_validation_results.json').write_text(json.dumps(checks,indent=2))
print(f'{len(checks)} native DAX checks passed across {len(sql)} agency-months')
