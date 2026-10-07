#!/usr/bin/env python3
"""Local browser verification: no model calls, no server mutations."""
import json
import pathlib
import re
import sys
LOCAL_DEPS=pathlib.Path(__file__).resolve().parents[2]/'data/local-archive/slide-python'
if LOCAL_DEPS.exists(): sys.path.insert(0,str(LOCAL_DEPS))
from playwright.sync_api import sync_playwright

HERE=pathlib.Path(__file__).resolve().parent
DECK=HERE/'deck.html'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True,args=['--disable-gpu'])
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    errors=[]; requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r: requests.append(r.url))
    page.goto(DECK.as_uri());page.evaluate('document.fonts.ready')
    count=page.locator('.slide').count(); assert count==48,count
    reports=[]
    for n in range(1,count+1):
        if n>1:page.keyboard.press('ArrowRight')
        page.wait_for_function(f'location.hash=="#{n}"')
        page.evaluate('document.fonts.ready')
        report=page.evaluate('''() => {
          const sl=document.querySelector('.slide.active');
          const out={title:sl.dataset.title,htmlOverflow:[],svgOverflow:[],boxTextOverflow:[],images:[]};
          const r=sl.getBoundingClientRect();
          sl.querySelectorAll('*').forEach(el=>{
            if(el instanceof SVGElement)return;
            const b=el.getBoundingClientRect();
            if(b.width&&b.height&&(b.left<r.left-1||b.right>r.right+1||b.top<r.top-1||b.bottom>r.bottom+1))
              out.htmlOverflow.push({tag:el.tagName,cls:el.className,text:el.textContent.slice(0,70),x:b.x,y:b.y,w:b.width,h:b.height});
            if(el.tagName==='PRE'&&(el.scrollWidth>el.clientWidth+2||el.scrollHeight>el.clientHeight+2))
              out.htmlOverflow.push({tag:'PRE',text:'scroll overflow',scrollWidth:el.scrollWidth,clientWidth:el.clientWidth});
          });
          sl.querySelectorAll('svg').forEach(svg=>{
            const vb=svg.viewBox.baseVal;
            svg.querySelectorAll('text').forEach(t=>{
              const b=t.getBBox();
              if(b.x<vb.x-1||b.x+b.width>vb.width+1||b.y<vb.y-1||b.y+b.height>vb.height+1)
                out.svgOverflow.push({text:t.textContent,x:b.x,y:b.y,w:b.width,h:b.height});
              let rect=null;
              for(const candidate of svg.querySelectorAll('rect')){
                const c=candidate.getBBox();
                if(b.x>=c.x&&b.x<=c.x+c.width&&b.y>=c.y&&b.y<=c.y+c.height)rect=c;
              }
              if(rect&&(b.x+b.width>rect.x+rect.width-10||b.y+b.height>rect.y+rect.height-8))
                out.boxTextOverflow.push({text:t.textContent,width:b.width,right:b.x+b.width,boxRight:rect.x+rect.width});
            });
          });
          sl.querySelectorAll('img').forEach(img=>out.images.push({src:img.getAttribute('src'),loaded:img.complete&&img.naturalWidth>0}));
          return out;
        }''')
        report['page']=n;reports.append(report)
    page.keyboard.press('Home');assert page.evaluate('location.hash')=='#1'
    page.keyboard.press('End');assert page.evaluate('location.hash')==f'#{count}'
    page.keyboard.press('g');assert page.locator('#nav-panel').evaluate('(e)=>e.classList.contains("open")')
    page.locator('#nav-panel .it').nth(23).click();assert page.evaluate('location.hash')=='#24'
    page.keyboard.press('2');page.keyboard.press('9');page.wait_for_function('location.hash=="#29"')
    animation_checks=[]
    animation_pages=page.locator('.slide').evaluate_all('(els)=>els.flatMap((el,i)=>el.querySelector("[data-flow]")?[i+1]:[])')
    for n in animation_pages:
        page.keyboard.press('Home')
        page.keyboard.press(str(n//10));page.keyboard.press(str(n%10))
        page.wait_for_function(f'location.hash=="#{n}"')
        root=page.locator('.slide').nth(n-1).locator('[data-flow]')
        assert root.get_attribute('data-step')=='0'
        assert root.get_attribute('data-playing')!='true'
        frames=root.locator('.flow-data').evaluate('(el)=>JSON.parse(el.textContent)')
        for i in range(1,len(frames)):
            page.keyboard.press('j');assert root.get_attribute('data-step')==str(i)
            assert root.locator('.flow-detail').inner_text()==frames[i]['detail']
            assert root.locator('.flow-node.current').count()==1
        page.keyboard.press('k');assert root.get_attribute('data-step')==str(len(frames)-2)
        root.get_by_role('button',name='从头开始',exact=True).click();assert root.get_attribute('data-step')=='0'
        root.get_by_role('button',name='播放流程',exact=True).click();assert root.get_attribute('data-playing')=='true'
        page.wait_for_function('document.querySelector(".slide.active [data-flow]").dataset.step==="1"',timeout=6000)
        root.get_by_role('button',name='暂停播放',exact=True).click();assert root.get_attribute('data-playing')=='false'
        page.keyboard.press('p');assert root.get_attribute('data-playing')=='true'
        page.keyboard.press('ArrowRight')
        assert root.get_attribute('data-playing')=='false'
        animation_checks.append({'page':n,'frames':len(frames),'manualSteps':True,'playPause':True,'leaveStops':True,'noAutoplay':True})
    for size in [{'width':1366,'height':768},{'width':1280,'height':800}]:
        page.set_viewport_size(size)
        page.wait_for_function('''() => {
            const r=document.getElementById('stage').getBoundingClientRect();
            return r.width<=innerWidth+1 && r.height<=innerHeight+1;
        }''')
        rect=page.locator('#stage').bounding_box();assert rect['width']<=size['width']+1 and rect['height']<=size['height']+1
    browser.close()
issues=[{'page':r['page'],'kind':k,'issues':r[k]} for r in reports for k in ['htmlOverflow','svgOverflow','boxTextOverflow'] if r[k]]
failed_images=[{'page':r['page'],**i} for r in reports for i in r['images'] if not i['loaded']]
external=[u for u in requests if re.match(r'https?://',u)]
result={'schema':'kernel-insight-deck-qa/v1','pages':count,'pageReports':reports,'issues':issues,'failedImages':failed_images,'scriptErrors':errors,'externalResourceRequests':external,
    'animationChecks':animation_checks,
    'navigation':{'arrows':True,'homeEnd':True,'directoryJump':True,'numericJump':True,'viewportScale':True},
    'passed':not(issues or failed_images or errors or external)}
(HERE/'qa-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='pageReports'},ensure_ascii=False,indent=2))
raise SystemExit(0 if result['passed'] else 1)
