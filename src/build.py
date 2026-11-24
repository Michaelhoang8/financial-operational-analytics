"""Build NYC obligation reporting from the pinned, unaltered OMB extract."""
import csv,gzip,json,sqlite3,hashlib,calendar
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MONTHS={name:i for i,name in enumerate(calendar.month_name) if name}
def normalize(rows):
 latest={};removed=0
 for row in rows:
  fy=int(row['FISCAL YEAR']);month=MONTHS[row['MONTH']];basis=row['CURRENT/YEAR-TO-DATE']
  if basis not in ('Current','Year-to-Date'):raise ValueError('Unknown reporting basis')
  period=f'{fy-1 if month>=7 else fy}-{month:02}'
  key=(period,basis,row['AGENCY']);pub=row['PUBLICATION DATE']
  value=(pub,fy,period,basis,row['AGENCY'],str(Decimal(row['ACTUAL '])),str(Decimal(row['PLAN'])))
  if key in latest:
   previous=latest[key];removed+=1
   if pub==previous[0] and value!=previous:raise ValueError('Conflicting same-publication facts')
   if pub<previous[0]:continue
  latest[key]=value
 return list(latest.values()),removed
def write_csv(name,headers,rows):
 with (ROOT/'data/model'/name).open('w',newline='',encoding='utf-8') as f:w=csv.writer(f);w.writerow(headers);w.writerows(rows)
def main():
 source=ROOT/'data/source/nyc_obligations.csv.gz'
 with gzip.open(source,'rt',encoding='utf-8-sig',newline='') as f:raw=list(csv.DictReader(f))
 rows,removed=normalize(raw)
 agencies=sorted({r[4] for r in rows});periods=sorted({(r[2],r[1]) for r in rows});aid={n:i+1 for i,n in enumerate(agencies)}
 db=sqlite3.connect(ROOT/'data/analytics.sqlite');db.executescript('DROP TABLE IF EXISTS Obligations; CREATE TABLE Obligations(Publication TEXT,FiscalYear INTEGER,Period TEXT,Basis TEXT,Agency TEXT,Actual REAL,Plan REAL,PRIMARY KEY(Period,Basis,Agency));')
 db.executemany('INSERT INTO Obligations VALUES(?,?,?,?,?,?,?)',rows)
 db.executescript((ROOT/'sql/analysis.sql').read_text(encoding='utf-8'));db.commit()
 monthly=[dict(zip([c[0] for c in cur.description],r)) for cur in [db.execute('SELECT * FROM MonthlyReview ORDER BY Period,Agency')] for r in cur]
 latest=max(r['Period'] for r in monthly);selected=[r for r in monthly if r['Period']==latest]
 checks={'raw_row_accounting':len(raw)==len(rows)+removed,'unique_fact_grain':len(rows)==len({(r[2],r[3],r[4]) for r in rows}),'monthly_basis_only':len(monthly)==sum(r[3]=='Current' for r in rows),'paired_current_ytd':len(rows)==2*len(monthly),'variance_reconciles':all(abs(r['Variance']-(r['Plan']-r['Actual']))<1e-8 for r in monthly),'source_totals_reconcile':abs(sum(float(r[5]) for r in rows if r[3]=='Current')-sum(r['Actual'] for r in monthly))<1e-6}
 assert all(checks.values()),checks
 write_csv('DimAgency.csv',['AgencyKey','Agency'],[(aid[n],n) for n in agencies]);write_csv('DimPeriod.csv',['Period','FiscalYear'],periods)
 for basis,name in [('Current','FactMonthly'),('Year-to-Date','FactYTD')]:write_csv(name+'.csv',['Period','AgencyKey','Actual','Plan','Publication'],[(r[2],aid[r[4]],r[5],r[6],r[0]) for r in rows if r[3]==basis])
 report={'title':'NYC obligation review','source_rows':len(raw),'model_rows':len(rows),'superseded_rows':removed,'periods':len(periods),'latest_period':latest,'units':'USD millions','checks':checks,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
 (ROOT/'reports/validation_results.json').write_text(json.dumps(report,indent=2))
 (ROOT/'reports/dashboard_data.json').write_text(json.dumps(monthly,indent=2))
 template=(ROOT/'src/dashboard_template.html').read_text(encoding='utf-8');(ROOT/'reports/dashboard.html').write_text(template.replace('__DATA__',json.dumps(monthly)).replace('__LATEST__',latest),encoding='utf-8')
 worst=min(selected,key=lambda r:r['Variance'])
 (ROOT/'reports/management_brief.md').write_text(f'''# NYC obligation review — {latest}

Source: NYC OMB Financial Plan Statements, dataset hjjq-k984. USD millions.

The latest available month reports {sum(r['Actual'] for r in selected):,.0f} actual obligations against {sum(r['Plan'] for r in selected):,.0f} planned. The largest negative plan-minus-actual difference is {worst['Agency']}: {worst['Variance']:,.0f} million. Investigate the underlying obligation timing and agency commentary before attributing a cause or calling a variance savings.

## Reporting decisions
- Current and cumulative year-to-date observations are separate facts. YTD values must never be summed across months.
- Where publication dates repeat a period, keep the latest publication for each agency/period/basis. Same-publication conflicts stop the build.
- Fiscal years start in July. The source does not contain every month (including missing June observations); no annual totals or fabricated gap fills are shown.
- Preserve signed adjustments and Intra-City Expenses as published. These are obligations, not cash payments, revenue, profit or audited net expenditure.
- Source amounts are rounded to millions. Month-to-YTD arithmetic can differ because of revisions and source rounding.
''',encoding='utf-8')
 db.close();print(json.dumps(report,indent=2))
if __name__=='__main__':main()
