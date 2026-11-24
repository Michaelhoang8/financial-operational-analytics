"""Build editable native Power BI project files from the prepared model exports."""
import base64,csv,json,re,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'powerbi/native'
NAME='Financial_Operational_Analytics'
REPORT=OUT/(NAME+'.Report');MODEL=OUT/(NAME+'.SemanticModel')
SCHEMA='https://developer.microsoft.com/json-schemas/fabric/item/report/'
def write(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2),encoding='utf-8')
def uid(name):return str(uuid.uuid5(uuid.NAMESPACE_URL,'northstar/'+name))
def literal(v):
 return {'expr':{'Literal':{'Value':('true' if v else 'false') if isinstance(v,bool) else str(v)+'D' if isinstance(v,(int,float)) else "'"+v.replace("'","''")+"'"}}}
def color(v):return {'solid':{'color':literal(v)}}
def field(t,c,measure=False):return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':t}},'Property':c}}
def proj(t,c,measure=False):return {'field':field(t,c,measure),'queryRef':t+'.'+c,'nativeQueryRef':c}
def m(c):return proj('FactActual',c,True)

model={'name':NAME,'compatibilityLevel':1606,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-CA','dataAccessOptions':{'legacyRedirects':True,'returnErrorValuesAsNull':True},'tables':[],'relationships':[],'expressions':[],'annotations':[{'name':'PBI_QueryOrder','value':json.dumps(['DimDate','DimBranch','DimAccount','DimProduct','FactActual','FactBudget','FactInventory','FactOrders'])},{'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}}
textcols={'Branch','Account','Category','SKU','YearMonth'}
datecols={'Date','PromisedDate','ShippedDate'}
for name in ['DimDate','DimBranch','DimAccount','DimProduct','FactActual','FactBudget','FactInventory','FactOrders']:
 with (ROOT/'data/model'/f'{name}.csv').open() as f:headers=next(csv.reader(f))
 cols=[];types=[]
 for h in headers:
  dtype='dateTime' if h in datecols else 'string' if h in textcols else 'decimal' if h=='StandardCost' else 'int64'
  c={'name':h,'dataType':dtype,'sourceColumn':h,'summarizeBy':'none','lineageTag':uid(name+'/'+h)}
  if name.startswith('Fact') or h.endswith('Key'):c['isHidden']=True
  if h in datecols:c.update(formatString='yyyy-mm-dd',annotations=[{'name':'UnderlyingDateTimeDataType','value':'Date'}])
  if name=='DimDate' and h=='Date':c['isKey']=True
  cols.append(c);types.append('{"'+h+'", '+('type date' if h in datecols else 'type text' if h in textcols else 'Currency.Type' if h=='StandardCost' else 'Int64.Type')+'}')
 expression=['let',f'    Source = Csv.Document(Binary.FromText("{base64.b64encode((ROOT/'data/model'/f'{name}.csv').read_bytes()).decode()}", BinaryEncoding.Base64), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),','    Typed = Table.TransformColumnTypes(Headers, {'+', '.join(types)+'}, "en-CA")','in','    Typed']
 table={'name':name,'lineageTag':uid(name),'columns':cols,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}],'annotations':[{'name':'PBI_ResultType','value':'Table'}]}
 if name=='DimDate':table['dataCategory']='Time'
 model['model']['tables'].append(table)
for fact in ['FactActual','FactBudget','FactInventory','FactOrders']:
 keys=[('Date','DimDate'),('BranchKey','DimBranch')]+([('AccountKey','DimAccount')] if fact in ['FactActual','FactBudget'] else [('ProductKey','DimProduct')] if fact=='FactInventory' else [])
 for key,dim in keys:model['model']['relationships'].append({'name':uid(fact+'/'+dim),'fromTable':fact,'fromColumn':key,'fromCardinality':'many','toTable':dim,'toColumn':key,'toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True})
measuretext=(ROOT/'powerbi/measures.dax').read_text(encoding='utf-8')
measures=[]
for line in measuretext.splitlines():
 if not line.strip() or line.startswith('//'):continue
 name,expr=line.split(' = ',1)
 fmt='0.0%' if '%' in name else '#,0' if name in ['Orders','On-Time Orders','Closing Units'] else '"$"#,0;("$"#,0);"$"0'
 measures.append({'name':name,'expression':expr,'formatString':fmt,'lineageTag':uid('measure/'+name),'displayFolder':'Financial' if name not in ['Orders','On-Time Orders','On-Time Delivery %','Closing Inventory','Closing Units'] else 'Operations'})
extras={'Freight':'CALCULATE([Actual Amount], DimAccount[AccountKey] = 6200)','Budget Freight':'CALCULATE([Budget Amount], DimAccount[AccountKey] = 6200)','Operating Margin %':'DIVIDE([Operating Profit], [Revenue])','Late Orders':'[Orders] - [On-Time Orders]','Budget Operating Costs':'CALCULATE([Budget Amount], DimAccount[Category] = "Opex")','Operating Cost Variance':'[Budget Operating Costs] - [Operating Costs]'}
for name,expr in extras.items():measures.append({'name':name,'expression':expr,'formatString':'0.0%' if '%' in name else '#,0' if name=='Late Orders' else '"$"#,0;("$"#,0);"$"0','lineageTag':uid('measure/'+name)})
next(t for t in model['model']['tables'] if t['name']=='FactActual')['measures']=measures
write(MODEL/'model.bim',model)
write(MODEL/'definition.pbism',{'version':'4.0','settings':{}})
write(OUT/(NAME+'.pbip'),{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':NAME+'.Report'}}],'settings':{'enableAutoRecovery':True}})
write(REPORT/'definition.pbir',{'$schema':SCHEMA+'definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../'+NAME+'.SemanticModel'}}})
write(REPORT/'definition/version.json',{'$schema':SCHEMA+'definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
theme=json.loads((ROOT/'powerbi/theme.json').read_text(encoding='utf-8'));theme.update(textClasses={'title':{'fontFace':'Segoe UI','fontSize':12,'color':'#172B40'},'label':{'fontFace':'Segoe UI','fontSize':10},'callout':{'fontFace':'Segoe UI','fontSize':28}})
write(REPORT/'StaticResources/RegisteredResources/Northstar.json',theme)
write(REPORT/'definition/report.json',{'$schema':SCHEMA+'definition/report/3.0.0/schema.json','themeCollection':{'customTheme':{'name':'Northstar.json','type':'RegisteredResources','reportVersionAtImport':{'visual':'1.8.0','report':'2.0.0','page':'1.3.0'}}},'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'Northstar.json','path':'Northstar.json','type':'CustomTheme'}]}],'settings':{'useStylableVisualContainerHeader':True,'useEnhancedTooltips':True}})
pages=[]
def page(name,title):
 pages.append(name);p=REPORT/'definition/pages'/name
 write(p/'page.json',{'$schema':SCHEMA+'definition/page/2.0.0/schema.json','name':name,'displayName':title,'displayOption':'FitToPage','width':1280,'height':800,'objects':{'background':[{'properties':{'color':color('#EDF2F5'),'transparency':literal(0)}}]}})
 return p
counter=0
def visual(p,vtype,title,x,y,w,h,roles=None,objects=None):
 global counter
 counter+=1;name=f'v{counter:019d}'
 config={'visualType':vtype,'drillFilterOtherVisuals':True,'visualContainerObjects':{'title':[{'properties':{'show':literal(bool(title)),'text':literal(title),'fontSize':literal(12),'fontColor':color('#172B40')}}],'background':[{'properties':{'show':literal(True),'color':color('#FFFFFF'),'transparency':literal(0)}}],'border':[{'properties':{'show':literal(False)}}]}}
 if roles:config['query']={'queryState':{k:{'projections':v} for k,v in roles.items()}}
 if objects:config['objects']=objects
 if vtype=='tableEx':config['objects']={'grid':[{'properties':{'rowPadding':literal(4)}}],'values':[{'properties':{'fontSize':literal(12)}}],'columnHeaders':[{'properties':{'fontSize':literal(12)}}]}
 obj={'$schema':SCHEMA+'definition/visualContainer/2.4.0/schema.json','name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':counter,'tabOrder':counter},'visual':config}
 write(p/'visuals'/name/'visual.json',obj);return obj,p/'visuals'/name/'visual.json'
def textbox(p,text,x,y,w,h,size=14,bg='#132E43',fg='#FFFFFF'):
 obj,path=visual(p,'textbox','',x,y,w,h,objects={'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':text,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':fg}}]}]}}]})
 obj['visual']['visualContainerObjects']['background'][0]['properties']['color']=color(bg);write(path,obj)
def header(p,title,subtitle):
 textbox(p,'NORTHSTAR  /  '+title,16,12,1248,54,22)
 textbox(p,subtitle+'  |  Synthetic portfolio data · CAD · 2024–2025',16,70,850,30,10,'#EDF2F5','#536A7A')
def slicer(p,title,t,c,x,w,year=False):
 obj,path=visual(p,'slicer',title,x,108,w,74,{'Values':[proj(t,c)]},{'data':[{'properties':{'mode':literal('Dropdown')}}],'selection':[{'properties':{'singleSelect':literal(year)}}]})
 if year:
  condition={'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'d'}},'Property':'Year'}}],'Values':[[{'Literal':{'Value':'2025L'}}]]}}
  selection={'Version':2,'From':[{'Name':'d','Entity':'DimDate','Type':0}],'Where':[{'Condition':condition}]}
  obj['visual']['objects']['general']=[{'properties':{'filter':{'filter':selection}}}]
 write(path,obj)
def common(p,title,subtitle):
 header(p,title,subtitle);slicer(p,'Reporting year','DimDate','Year',16,240,True);slicer(p,'Branch','DimBranch','Branch',272,300)
def cards(p,names):
 for i,name in enumerate(names):visual(p,'card',name,16+i*316,198,300,108,{'Values':[m(name)]},{'labels':[{'properties':{'fontSize':literal(26),'color':color('#132E43'),'labelDisplayUnits':literal(1),'labelPrecision':literal(1 if '%' in name else 0)}}],'categoryLabels':[{'properties':{'show':literal(False)}}]})
p=page('Executive','Executive Overview');common(p,'Financial & Operational Analytics','Budget accountability, business performance and service reliability');cards(p,['Revenue','Operating Profit','Profit Variance','On-Time Delivery %'])
visual(p,'clusteredColumnChart','Revenue versus budget by month',16,322,770,238,{'Category':[proj('DimDate','YearMonth')],'Y':[m('Revenue'),m('Budget Revenue')]})
visual(p,'clusteredBarChart','Operating profit variance by branch',802,322,462,238,{'Category':[proj('DimBranch','Branch')],'Y':[m('Profit Variance')]})
visual(p,'tableEx','Monthly financial and operational review',16,576,1248,208,{'Values':[proj('DimDate','YearMonth'),m('Revenue'),m('Budget Revenue'),m('Operating Profit'),m('Freight'),m('Closing Inventory'),m('On-Time Delivery %')]})
p=page('Budget','Budget & Costs');common(p,'Budget & Cost Control','Positive account variance is favorable; expense variance uses budget minus actual');cards(p,['Operating Costs','Budget Operating Costs','Operating Cost Variance','Operating Margin %'])
visual(p,'tableEx','Account-level budget control',16,322,710,290,{'Values':[proj('DimAccount','Account'),m('Actual Amount'),m('Budget Amount'),m('Favorable Account Variance')]})
visual(p,'lineChart','Freight actual versus budget',742,322,522,290,{'Category':[proj('DimDate','YearMonth')],'Y':[m('Freight'),m('Budget Freight')]})
visual(p,'clusteredColumnChart','Operating profit versus budget',16,628,1248,156,{'Category':[proj('DimDate','YearMonth')],'Y':[m('Operating Profit'),m('Budget Profit')]})
p=page('Inventory','Inventory & Delivery');common(p,'Inventory & Delivery','Closing inventory uses the last selected snapshot; delivery rate is weighted by orders');cards(p,['Closing Inventory','Closing Units','Orders','On-Time Delivery %'])
visual(p,'clusteredBarChart','Closing inventory by SKU',16,322,612,268,{'Category':[proj('DimProduct','SKU')],'Y':[m('Closing Inventory')]})
visual(p,'lineChart','On-time delivery by month',644,322,620,268,{'Category':[proj('DimDate','YearMonth')],'Y':[m('On-Time Delivery %')]})
visual(p,'tableEx','Branch service and stock review',16,606,1248,178,{'Values':[proj('DimBranch','Branch'),m('Closing Inventory'),m('Closing Units'),m('Orders'),m('Late Orders'),m('On-Time Delivery %')]})
write(REPORT/'definition/pages/pages.json',{'$schema':SCHEMA+'definition/pagesMetadata/1.0.0/schema.json','pageOrder':pages,'activePageName':'Executive'})
print(json.dumps({'project':str(OUT/(NAME+'.pbip')),'tables':len(model['model']['tables']),'relationships':len(model['model']['relationships']),'measures':len(measures),'pages':len(pages),'visuals':counter},indent=2))
