"""Render every page, audit SVG geometry and controls, export five teaching GIFs."""
import pathlib,sys,json,math,hashlib
from PIL import Image
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
deps=ROOT/'data/local-archive/slide-python'
if deps.exists():sys.path.insert(0,str(deps))
from playwright.sync_api import sync_playwright
OUT=HERE/'rendered';OUT.mkdir(exist_ok=True);errors=[];requests=[];reports=[];checks=[];gifs=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True,args=['--disable-gpu'])
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
    page.goto((HERE/'deck.html').as_uri());page.evaluate('document.fonts.ready')
    count=page.locator('.slide').count();assert count==20
    def goto(n):
        page.evaluate('document.activeElement.blur()');page.keyboard.press('Home')
        if n>1:
            for c in str(n):page.keyboard.press(c)
        page.wait_for_function('(n)=>document.querySelectorAll(".slide")[n-1].classList.contains("active")',arg=n)
        page.wait_for_timeout(220)
    for n in range(1,count+1):
        goto(n);page.screenshot(path=str(OUT/f'slide-{n:02d}.png'))
        r=page.evaluate('''()=>{
          const sl=document.querySelector('.slide.active'),r=sl.getBoundingClientRect(),out={html:[],svg:[],boxes:[],textOverlaps:[],images:[]};
          sl.querySelectorAll('*').forEach(el=>{if(el instanceof SVGElement)return;const b=el.getBoundingClientRect();if(b.width&&b.height&&(b.left<r.left-1||b.right>r.right+1||b.top<r.top-1||b.bottom>r.bottom+1))out.html.push(el.tagName+':'+el.textContent.slice(0,60));});
          sl.querySelectorAll('svg').forEach(svg=>{const vb=svg.viewBox.baseVal,tt=[...svg.querySelectorAll('text')];tt.forEach(t=>{const b=t.getBBox();if(b.x<0||b.x+b.width>vb.width+1||b.y<0||b.y+b.height>vb.height+1)out.svg.push(t.textContent);
            for(const rr of svg.querySelectorAll('rect')){const c=rr.getBBox();if(b.x>=c.x&&b.x<c.x+c.width&&b.y>=c.y&&b.y<c.y+c.height&&(b.x+b.width>c.x+c.width-8||b.y+b.height>c.y+c.height-5))out.boxes.push(t.textContent);}
          });for(let i=0;i<tt.length;i++)for(let j=i+1;j<tt.length;j++){const a=tt[i].getBBox(),b=tt[j].getBBox();if(Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>2&&Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>2)out.textOverlaps.push([tt[i].textContent,tt[j].textContent]);}});
          sl.querySelectorAll('img').forEach(img=>out.images.push({src:img.getAttribute('src'),loaded:img.complete&&img.naturalWidth>0}));return out;
        }''');r['page']=n;reports.append(r)
        if page.locator('.slide.active.walk').count():
            root=page.locator('.slide').nth(n-1);assert root.get_attribute('data-playing')=='false';assert root.get_attribute('data-step')=='0'
            steps=json.loads(root.locator('.walk-data').text_content());frames=[]
            for k in range(len(steps)):
                if k:page.keyboard.press('j');page.wait_for_timeout(220)
                assert root.get_attribute('data-step')==str(k)
                if n in [4,5,6,13,16,18]:
                    shot=OUT/f'page-{n:02d}-step-{k}.png';page.screenshot(path=str(shot));frames.append(Image.open(shot).convert('RGB').resize((1280,720),Image.Resampling.LANCZOS).quantize(colors=128))
            page.screenshot(path=str(OUT/f'slide-{n:02d}-final.png'))
            if frames:
                file=HERE/'media'/f'教学流程-{n:02d}.gif';frames[0].save(file,save_all=True,append_images=frames[1:],duration=[1600]*(len(frames)-1)+[2600],loop=0,disposal=1)
                gifs.append({'page':n,'file':file.name,'frames':len(frames),'clock':'Teaching steps, no measured duration','sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
            page.keyboard.press('k');assert root.get_attribute('data-step')==str(len(steps)-2)
            root.locator('[data-act=reset]').click();assert root.get_attribute('data-step')=='0'
            page.keyboard.press('p');assert root.get_attribute('data-playing')=='true'
            page.keyboard.press('ArrowRight');assert root.get_attribute('data-playing')=='false'
            checks.append({'page':n,'steps':len(steps),'no_autoplay':True,'keyboard_steps':True,'reset':True,'play_and_leave_stop':True})
    page.keyboard.press('Home');assert page.evaluate('location.hash')=='#1';page.keyboard.press('End');assert page.evaluate('location.hash')=='#20'
    page.keyboard.press('g');page.locator('#nav-panel .it').nth(13).click();assert page.evaluate('location.hash')=='#14'
    for size in [{'width':1280,'height':800},{'width':1366,'height':768}]:
        page.set_viewport_size(size);page.wait_for_timeout(100);b=page.locator('#stage').bounding_box();assert b['width']<=size['width']+1 and b['height']<=size['height']+1
    browser.close()
sheet=Image.new('RGB',(1970,math.ceil(count/4)*280+10),'#CDD1D8')
for i in range(count):
    im=Image.open(OUT/f'slide-{i+1:02d}.png');sheet.paste(im.resize((480,270),Image.Resampling.LANCZOS),(10+(i%4)*490,10+(i//4)*280))
sheet.save(HERE/'预览-全部页面.png')
issues=[{'page':r['page'],'kind':k,'items':r[k]} for r in reports for k in ['html','svg','boxes','textOverlaps'] if r[k]]
failed=[im for r in reports for im in r['images'] if not im['loaded']]
external=[u for u in requests if u.startswith(('http://','https://'))]
result={'passed':not(issues or errors or failed or external),'pages':count,'issues':issues,'script_errors':errors,'failed_images':failed,'external_resources':external,'animation_checks':checks,'deck_sha256':hashlib.sha256((HERE/'deck.html').read_bytes()).hexdigest()}
(HERE/'qa-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');(HERE/'media/gif-manifest.json').write_text(json.dumps(gifs,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['passed'] else 1)
