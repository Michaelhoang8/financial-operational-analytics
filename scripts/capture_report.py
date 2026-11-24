from pathlib import Path
import argparse,json,subprocess,tempfile,hashlib
from datetime import datetime,timezone
from playwright.sync_api import sync_playwright
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=p.parse_args();r=args.root.resolve()
 out=r/'docs/screenshots';out.mkdir(parents=True,exist_ok=True);videoout=r/'docs/recordings';videoout.mkdir(parents=True,exist_ok=True)
 errors=[];captures=[]
 with tempfile.TemporaryDirectory() as temp,sync_playwright() as pw:
  browser=pw.chromium.launch(channel='msedge',headless=True)
  ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=temp,record_video_size={'width':1440,'height':1000})
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto((r/'reports/dashboard.html').as_uri(),wait_until='networkidle');page.wait_for_timeout(1500)
  page.screenshot(path=str(out/'dashboard.png'));captures.append('dashboard.png');page.wait_for_timeout(2500)
  # Exercise every native select before scrolling through actual rendered sections.
  for select in page.locator('select').all():
   options=select.locator('option').all()
   if len(options)>1:
    select.select_option(index=len(options)-1);page.wait_for_timeout(1500)
  page.screenshot(path=str(out/'filtered.png'));captures.append('filtered.png')
  for i,section in enumerate(page.locator('section').all()[:5],1):
   section.scroll_into_view_if_needed();page.wait_for_timeout(900);page.screenshot(path=str(out/f'detail-{i}.png'));captures.append(f'detail-{i}.png');page.wait_for_timeout(1800)
  video=page.video;ctx.close();src=video.path();browser.close()
  subprocess.run(['ffmpeg','-y','-loglevel','error','-i',src,'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(videoout/'walkthrough.mp4')],check=True)
 assert not errors,errors
 manifest={'captured_at':datetime.now(timezone.utc).isoformat(),'source':'Actual reports/dashboard.html browser render','recording':'Automated browser walkthrough, not manual development footage','page_errors':errors,'screenshots':[{ 'file':name,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in captures]}
 (videoout/'capture_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 (videoout/'README.md').write_text('# Recorded dashboard review\n\n[Watch/download walkthrough.mp4](walkthrough.mp4)\n\nContinuous automated browser walkthrough of the working local report. It shows observed public data, not a live Microsoft tenant or manual development session.\n',encoding='utf-8')
 (out/'README.md').write_text('# Dashboard captures\n\nActual browser captures. Excel-prefixed images, when present, are workbook renders. Powerbi-prefixed images are native Power BI Desktop captures.\n\n'+''.join(f'![{name}]({name})\n\n' for name in captures),encoding='utf-8')
 print(json.dumps({'project':r.name,'screenshots':len(captures),'browser_errors':errors}))
if __name__=='__main__':main()
