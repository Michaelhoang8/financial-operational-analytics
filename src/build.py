"""Deterministic portfolio dataset and SQL reporting pipeline. Python standard library only."""
from pathlib import Path
import calendar, csv, datetime as dt, json, random, sqlite3

ROOT = Path(__file__).resolve().parents[1]
for name in ('data/raw','data/model','sql','reports','powerbi'):
    (ROOT/name).mkdir(parents=True, exist_ok=True)
rng = random.Random(42)
db = sqlite3.connect(ROOT/'data/analytics.sqlite')
def csv_out(path, headers, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(headers); w.writerows(rows)
def table(name, ddl, rows):
    db.execute(f'DROP TABLE IF EXISTS {name}')
    db.execute(f'CREATE TABLE {name} ({ddl})')
    db.executemany(f'INSERT INTO {name} VALUES ({",".join("?" for _ in rows[0])})',rows)
    csv_out(ROOT/'data/raw'/f'{name}.csv',[x[1] for x in db.execute(f'PRAGMA table_info({name})')],rows)

branches=[(1,'Edmonton'),(2,'Calgary'),(3,'Vancouver')]
accounts=[(4000,'Revenue','Revenue'),(5000,'Cost of goods sold','COGS'),(6100,'Payroll','Opex'),(6200,'Freight','Opex'),(6300,'Facilities','Opex')]
products=[(i,f'SKU-{i:03}',('Industrial','Safety','Office')[(i-1)%3],20+i*7) for i in range(1,13)]
dates=[]
d=dt.date(2024,1,1)
while d<=dt.date(2025,12,31):
    dates.append((d.isoformat(),d.year,d.month,d.strftime('%Y-%m'),(d.month-1)//3+1))
    d+=dt.timedelta(days=1)
table('DimDate','Date TEXT PRIMARY KEY, Year INTEGER, Month INTEGER, YearMonth TEXT, Quarter INTEGER',dates)
table('DimBranch','BranchKey INTEGER PRIMARY KEY, Branch TEXT',branches)
table('DimAccount','AccountKey INTEGER PRIMARY KEY, Account TEXT, Category TEXT',accounts)
table('DimProduct','ProductKey INTEGER PRIMARY KEY, SKU TEXT, Category TEXT, StandardCost REAL',products)
ledger=[]; budget=[]; inventory=[]; orders=[]; key=0
for year in (2024,2025):
  for month in range(1,13):
    end=f'{year}-{month:02}-{calendar.monthrange(year,month)[1]}'
    for branch,bname in branches:
      target=round((180000+branch*32000)*(1.10 if year==2025 else 1)*(1+.12*(month>=10)),2)
      revenue=round(target*rng.uniform(.94,1.08)*(0.9 if branch==3 and year==2025 and month>=7 else 1),2)
      amounts=[revenue,round(revenue*rng.uniform(.56,.61),2),round(34000*(1+.04*(year-2024)),2),round(revenue*(.062 if branch==3 and year==2025 and month>=7 else .04),2),14500]
      plans=[target,round(target*.575,2),35000,round(target*.04,2),14500]
      for (account,_,_),amount,plan in zip(accounts,amounts,plans):
        budget.append((end,branch,account,round(plan*100)))
        cents=round(amount*100)
        for part in range(10):
          key+=1
          ledger.append((key,end,branch,account,cents//10+(1 if part<cents%10 else 0)))
      for product,sku,cat,cost in products:
        units=rng.randint(60,240)+(180 if year==2025 and branch==3 and product<=3 else 0)
        inventory.append((end,branch,product,units,round(cost*100),round(units*cost*100)))
      for n in range(100):
        promised=dt.date(year,month,rng.randint(1,24))
        late=rng.random() < (.23 if branch==3 and year==2025 and month>=7 else .08)
        shipped=promised+dt.timedelta(days=rng.randint(1,4) if late else -rng.randint(0,2))
        orders.append((len(orders)+1,end,branch,promised.isoformat(),shipped.isoformat(),int(not late)))
# Three intentional exceptions. Duplicate amount must be excluded once; invalid rows quarantined.
ledger.extend([ledger[0],(key+1,'2025-12-31',99,4000,125000),(key+2,'2025-12-31',1,5000,None)])
table('RawLedger','TransactionID INTEGER, Date TEXT, BranchKey INTEGER, AccountKey INTEGER, AmountCents INTEGER',ledger)
table('FactBudget','Date TEXT, BranchKey INTEGER, AccountKey INTEGER, AmountCents INTEGER, PRIMARY KEY(Date,BranchKey,AccountKey)',budget)
table('FactInventory','Date TEXT, BranchKey INTEGER, ProductKey INTEGER, Units INTEGER, UnitCostCents INTEGER, ValueCents INTEGER, PRIMARY KEY(Date,BranchKey,ProductKey)',inventory)
table('FactOrders','OrderID INTEGER PRIMARY KEY, Date TEXT, BranchKey INTEGER, PromisedDate TEXT, ShippedDate TEXT, OnTime INTEGER',orders)
db.executescript((ROOT/'sql/transform.sql').read_text())
tables=['DimDate','DimBranch','DimAccount','DimProduct','FactActual','FactBudget','FactInventory','FactOrders']
for name in tables:
    cur=db.execute(f'SELECT * FROM {name}')
    csv_out(ROOT/'data/model'/f'{name}.csv',[x[0] for x in cur.description],cur.fetchall())
cur=db.execute('SELECT * FROM QualityExceptions')
exceptions=cur.fetchall()
csv_out(ROOT/'reports/data_quality_exceptions.csv',[x[0] for x in cur.description],exceptions)
monthly=[dict(zip([x[0] for x in cur.description],row)) for cur in [db.execute('SELECT * FROM MonthlyPerformance')] for row in cur.fetchall()]
checks={}
def check(name, condition):
    checks[name]=bool(condition)
    if not condition: raise AssertionError(name)
check('three intentional exceptions isolated',len(exceptions)==3)
check('3600 accepted transactions',db.execute('SELECT COUNT(*) FROM FactActual').fetchone()[0]==3600)
check('unique transaction IDs',db.execute('SELECT COUNT(*)-COUNT(DISTINCT TransactionID) FROM FactActual').fetchone()[0]==0)
check('ledger reconciliation in cents',db.execute('SELECT SUM(AmountCents) FROM RawLedger').fetchone()[0]==db.execute('SELECT SUM(AmountCents) FROM FactActual').fetchone()[0]+sum(x[-1] or 0 for x in exceptions))
check('72 branch months',len(monthly)==72)
check('inventory valuation',db.execute('SELECT COUNT(*) FROM FactInventory WHERE ValueCents<>Units*UnitCostCents').fetchone()[0]==0)
check('orders classified from dates',db.execute('SELECT COUNT(*) FROM FactOrders WHERE OnTime<>(ShippedDate<=PromisedDate)').fetchone()[0]==0)
for fact in ('FactActual','FactBudget','FactInventory','FactOrders'):
    check(f'{fact} date and branch keys valid',db.execute(f'SELECT COUNT(*) FROM {fact} f LEFT JOIN DimDate d ON f.Date=d.Date LEFT JOIN DimBranch b ON f.BranchKey=b.BranchKey WHERE d.Date IS NULL OR b.BranchKey IS NULL').fetchone()[0]==0)
for fact in ('FactActual','FactBudget'):
    check(f'{fact} account keys valid',db.execute(f'SELECT COUNT(*) FROM {fact} f LEFT JOIN DimAccount a ON f.AccountKey=a.AccountKey WHERE a.AccountKey IS NULL').fetchone()[0]==0)
check('inventory product keys valid',db.execute('SELECT COUNT(*) FROM FactInventory f LEFT JOIN DimProduct p ON f.ProductKey=p.ProductKey WHERE p.ProductKey IS NULL').fetchone()[0]==0)
check('monthly revenue reconciles to ledger',round(sum(x['Revenue'] for x in monthly)*100)==db.execute('SELECT SUM(AmountCents) FROM FactActual WHERE AccountKey=4000').fetchone()[0])
(ROOT/'reports/validation_results.json').write_text(json.dumps(checks,indent=2))
(ROOT/'reports/dashboard_data.json').write_text(json.dumps(monthly,indent=2))
template=(ROOT/'src/dashboard_template.html').read_text(encoding='utf-8')
(ROOT/'reports/dashboard.html').write_text(template.replace('__DATA__',json.dumps(monthly)),encoding='utf-8')
current=[r for r in monthly if r['Year']==2025]
rev=sum(r['Revenue'] for r in current); plan=sum(r['BudgetRevenue'] for r in current)
profit=sum(r['Profit'] for r in current); bp=sum(r['BudgetProfit'] for r in current)
branch_profit={b:sum(r['Profit']-r['BudgetProfit'] for r in current if r['Branch']==b) for _,b in branches}
worst=min(branch_profit,key=branch_profit.get)
(ROOT/'reports/management_brief.md').write_text(f'''# Financial and operational review — FY2025

Synthetic portfolio case. Currency: CAD. Comparisons use the original annual budget; these are simulated findings, not employer results.

- Revenue: ${rev:,.0f}, against ${plan:,.0f} budget ({(rev/plan-1):+.1%}).
- Operating profit: ${profit:,.0f}, against ${bp:,.0f} budget (${profit-bp:+,.0f} favorable variance).
- Largest unfavorable branch profit variance: {worst}, ${branch_profit[worst]:+,.0f}.

## Recommended decisions
1. Review Vancouver's second-half freight rates and shipment mix. The scenario deliberately includes a higher freight rate; compare Freight actual and budget before proposing carrier changes. Owner: operations manager; next review: monthly close.
2. Review Vancouver SKUs 001–003 for excess stock. The simulation increases these balances. Obtain demand and lead-time evidence before reducing replenishment; this dataset does not establish obsolete stock.
3. Review late orders by branch using the on-time delivery rate. Investigate carrier and warehouse causes; order records alone do not establish causality.
4. Correct the three source exceptions before close. Preserve the quarantine log and reconcile accepted plus rejected amounts to raw ledger totals.

## Limits
The data is seeded to illustrate analysis. No measured savings, stakeholder adoption, production deployment, or causal improvements are claimed. Inventory is a month-end snapshot and must not be summed across months. Orders are assigned to reporting month, not shipment month. The financial ledger is a simplified management P&L, not a balanced general ledger.
''',encoding='utf-8')
db.commit(); db.close()
print(json.dumps({'checks_passed':len(checks),'accepted_transactions':3600,'dashboard':str(ROOT/'reports/dashboard.html')},indent=2))
