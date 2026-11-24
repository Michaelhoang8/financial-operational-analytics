"""Generate a portable Power BI project for published NYC obligations."""
import csv,json,uuid,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'powerbi/native';NAME='NYC_Obligations'
REPORT=OUT/(NAME+'.Report');MODEL=OUT/(NAME+'.SemanticModel')
SCHEMA='https://developer.microsoft.com/json-schemas/fabric/item/report/'
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2),encoding='utf-8')
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'nyc-obligations/'+s))
def literal(v):return {'expr':{'Literal':{'Value':('true' if v else 'false') if isinstance(v,bool) else str(v)+'D' if isinstance(v,(int,float)) else "'"+v.replace("'","''")+"'"}}}
def color(v):return {'solid':{'color':literal(v)}}
def field(t,c,measure=False):return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':t}},'Property':c}}
def proj(t,c,measure=False):return {'field':field(t,c,measure),'queryRef':t+'.'+c,'nativeQueryRef':c}
def m(c):return proj('FactMonthly',c,True)
model={'name':NAME,'compatibilityLevel':1606,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':[],'relationships':[],'annotations':[{'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}}
for name in ['DimAgency','DimPeriod','FactMonthly','FactYTD']:
 source=ROOT/'data/model'/f'{name}.csv'
 with source.open() as f:headers=next(csv.reader(f))
 cols=[];types=[]
 for h in headers:
  dtype='int64' if h in ['AgencyKey','FiscalYear'] else 'double' if h in ['Actual','Plan'] else 'string'
  cols.append({'name':h,'dataType':dtype,'sourceColumn':h,'summarizeBy':'none','lineageTag':uid(name+h),'isHidden':name.startswith('Fact') or h=='AgencyKey'})
  types.append('{"'+h+'", '+('Int64.Type' if dtype=='int64' else 'type number' if dtype=='double' else 'type text')+'}')
 encoded=base64.b64encode(source.read_bytes()).decode()
 expression=['let',f' Source = Csv.Document(Binary.FromText("{encoded}", BinaryEncoding.Base64), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',' Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',' Typed = Table.TransformColumnTypes(Headers, {'+', '.join(types)+'}, "en-US")','in',' Typed']
 model['model']['tables'].append({'name':name,'columns':cols,'lineageTag':uid(name),'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]})
for fact in ['FactMonthly','FactYTD']:
 for key,dim in [('Period','DimPeriod'),('AgencyKey','DimAgency')]:model['model']['relationships'].append({'name':uid(fact+dim),'fromTable':fact,'fromColumn':key,'fromCardinality':'many','toTable':dim,'toColumn':key,'toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True})
measures={'Actual obligations':'SUM(FactMonthly[Actual])','Planned obligations':'SUM(FactMonthly[Plan])','Plan minus actual':'[Planned obligations] - [Actual obligations]','Variance %':'DIVIDE([Plan minus actual], ABS([Planned obligations]))','Reported months':'DISTINCTCOUNT(FactMonthly[Period])','Agency count':'DISTINCTCOUNT(FactMonthly[AgencyKey])','YTD actual at latest month':'VAR LastPeriod = MAX(DimPeriod[Period]) RETURN CALCULATE(SUM(FactYTD[Actual]), DimPeriod[Period] = LastPeriod)','YTD plan at latest month':'VAR LastPeriod = MAX(DimPeriod[Period]) RETURN CALCULATE(SUM(FactYTD[Plan]), DimPeriod[Period] = LastPeriod)','YTD plan minus actual':'[YTD plan at latest month] - [YTD actual at latest month]','YTD variance %':'DIVIDE([YTD plan minus actual], ABS([YTD plan at latest month]))'}
next(t for t in model['model']['tables'] if t['name']=='FactMonthly')['measures']=[{'name':n,'expression':e,'formatString':'0.0%' if '%' in n else '#,0;(#,0);0','lineageTag':uid(n),'description':'USD millions' if n not in ['Reported months','Agency count'] and '%' not in n else 'Count or ratio'} for n,e in measures.items()]
write(MODEL/'model.bim',model);write(MODEL/'definition.pbism',{'version':'4.0','settings':{}})
write(OUT/(NAME+'.pbip'),{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':NAME+'.Report'}}],'settings':{'enableAutoRecovery':True}})
write(REPORT/'definition.pbir',{'$schema':SCHEMA+'definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../'+NAME+'.SemanticModel'}}})
write(REPORT/'definition/version.json',{'$schema':SCHEMA+'definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
write(REPORT/'definition/report.json',{'$schema':SCHEMA+'definition/report/3.0.0/schema.json','themeCollection':{},'settings':{'useStylableVisualContainerHeader':True}})
(ROOT/'powerbi/measures.dax').write_text('\n'.join(n+' = '+e for n,e in measures.items()),encoding='utf-8')
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

latest=json.loads((ROOT/'reports/validation_results.json').read_text())['latest_period']
def common(p,title,filter_period=True):
 textbox(p,'NYC / '+title,16,12,1248,54,22)
 textbox(p,'Observed OMB financial statements | USD millions | July fiscal year start',16,72,1248,30,11,'#EDF2F5','#536A7A')
 obj,path=visual(p,'slicer','Reporting month','16' if False else 16,110,300,70,{'Values':[proj('DimPeriod','Period')]},{'data':[{'properties':{'mode':literal('Dropdown')}}]})
 if filter_period:
  condition={'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'p'}},'Property':'Period'}}],'Values':[[{'Literal':{'Value':"'"+latest+"'"}}]]}}
  obj['visual']['objects']['general']=[{'properties':{'filter':{'filter':{'Version':2,'From':[{'Name':'p','Entity':'DimPeriod','Type':0}],'Where':[{'Condition':condition}]}}}}];write(path,obj)
 visual(p,'slicer','Agency',340,110,550,70,{'Values':[proj('DimAgency','Agency')]},{'data':[{'properties':{'mode':literal('Dropdown')}}]})
def cards(p,names):
 for i,n in enumerate(names):visual(p,'card',n,16+i*316,200,300,110,{'Values':[m(n)]},{'labels':[{'properties':{'fontSize':literal(26),'labelDisplayUnits':literal(1)}}],'categoryLabels':[{'properties':{'show':literal(False)}}]})
p=page('Monthly','Monthly obligations');common(p,'Obligations against plan');cards(p,['Actual obligations','Planned obligations','Plan minus actual','Variance %'])
visual(p,'clusteredBarChart','Agency actual and plan (USD millions)',16,330,720,440,{'Category':[proj('DimAgency','Agency')],'Y':[m('Actual obligations'),m('Planned obligations')]})
visual(p,'tableEx','Agency variance review',752,330,512,440,{'Values':[proj('DimAgency','Agency'),m('Plan minus actual'),m('Variance %')]})
p=page('YTD','Year-to-date snapshot');common(p,'Year-to-date snapshot');cards(p,['YTD actual at latest month','YTD plan at latest month','YTD plan minus actual','YTD variance %'])
visual(p,'tableEx','YTD by agency at the latest selected month',16,330,1248,400,{'Values':[proj('DimAgency','Agency'),m('YTD actual at latest month'),m('YTD plan at latest month'),m('YTD plan minus actual')]})
textbox(p,'Cumulative YTD figures are never added across months. Missing months remain missing.',16,742,1248,40,12,'#EDF2F5','#536A7A')
p=page('History','Monthly history');common(p,'Published monthly history',False);cards(p,['Reported months','Agency count','Actual obligations','Planned obligations'])
visual(p,'lineChart','Current-month actual versus plan; available observations only',16,330,1248,300,{'Category':[proj('DimPeriod','Period')],'Y':[m('Actual obligations'),m('Planned obligations')]})
textbox(p,'Multi-month sums describe available observations, not complete fiscal-year totals. Obligations are not cash payments or profit. Signed adjustments and intra-city expenses are preserved.',16,658,1248,100,14,'#EDF2F5','#536A7A')
write(REPORT/'definition/pages/pages.json',{'$schema':SCHEMA+'definition/pagesMetadata/1.0.0/schema.json','pageOrder':pages,'activePageName':'Monthly'})
print('Built portable native model: 4 tables, 4 relationships, 10 measures, 3 pages')
