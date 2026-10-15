"""Render all 70 offline slides; verify new controls and export measured/teaching GIFs."""
import pathlib,sys,json,io,base64,hashlib,math
from PIL import Image,ImageDraw,ImageFont
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
deps=ROOT/'data/local-archive/slide-python'
if deps.exists():sys.path.insert(0,str(deps))
from playwright.sync_api import sync_playwright
OUT=HERE/'rendered';OUT.mkdir(exist_ok=True);MEDIA=HERE/'media/finetune'
FONT=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',27);SMALL=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
GIF_PAGES={59:'模型构建_LoRA',61:'真实微调_396微步',62:'RLCD训练机制',63:'Decision与Chat接口',64:'分类命中配对对比',65:'概率校准对比',66:'并发响应_KV_功耗对比',68:'微调前后内存对比',69:'完整Agent效果对比'}
selected=next((set(map(int,a.split('=',1)[1].split(','))) for a in sys.argv if a.startswith('--gif-pages=')),None)
checks=[];manifest=[];errors=[];requests=[]
if selected:
    manifest=[x for x in json.loads((MEDIA/'gif-manifest.json').read_text(encoding='utf-8')) if x['page'] not in selected]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True,args=['--disable-gpu'])
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
    page.goto((HERE/'deck.html').as_uri());page.evaluate('document.fonts.ready');count=page.locator('.slide').count();assert count==70
    def goto(n):
        page.evaluate('document.activeElement.blur()');page.keyboard.press('Home')
        if n>1:
            for c in str(n):page.keyboard.press(c)
        page.wait_for_function('(n)=>document.querySelectorAll(".slide")[n-1].classList.contains("active")',arg=n)
    if '--verify-only' not in sys.argv:
        for n in range(1,count+1):
            goto(n);page.screenshot(path=str(OUT/f'slide-{n:02d}.png'))
        tiles=[Image.open(OUT/f'slide-{n:02d}.png') for n in range(1,count+1)]
        sheet=Image.new('RGB',(1970,math.ceil(count/4)*280+10),'#C8CDD4')
        for i,im in enumerate(tiles):sheet.paste(im.resize((480,270)),(10+i%4*490,10+i//4*280))
        sheet.save(OUT/'contact.png');sheet.save(HERE/'预览-全部页面.png')
        sheet=Image.new('RGB',(1970,850),'#C8CDD4')
        for i,im in enumerate(tiles[58:]):sheet.paste(im.resize((480,270)),(10+i%4*490,10+i//4*280))
        sheet.save(MEDIA/'新增页面预览.png')
    for n in range(59,71):
        goto(n);root=page.locator('.slide.active .ft-player');assert root.get_attribute('data-playing')=='false'
        assert float(root.get_attribute('data-time'))==0
        page.keyboard.press('j');assert float(root.get_attribute('data-time'))>0
        page.keyboard.press('k');assert float(root.get_attribute('data-time'))==0
        root.locator('[data-ft=play]').click();page.wait_for_timeout(140);assert root.get_attribute('data-playing')=='true'
        page.keyboard.press('ArrowRight' if n<count else 'ArrowLeft');assert root.get_attribute('data-playing')=='false'
        goto(n);root=page.locator('.slide.active .ft-player');root.locator('input').evaluate('(e)=>{e.value=.5;e.dispatchEvent(new Event("input",{bubbles:true}));}')
        end=root.evaluate('(r)=>r._ft.end()');assert abs(float(root.get_attribute('data-time'))-end/2)<.002
        page.screenshot(path=str(MEDIA/f'page-{n}-mid.png'))
        checks.append({'page':n,'no_autoplay':True,'event_steps':True,'play_pause':True,'leave_stops':True,'scrub':True})
        if n not in GIF_PAGES or '--verify-only' in sys.argv or (selected and n not in selected):continue
        frames=[];title=page.locator('.slide.active').get_attribute('data-title');real=n in [61,66,68]
        for k in range(81):
            t=end*k/80
            b64=root.evaluate('(r,t)=>{r._ft.setTime(t);return r.querySelector("canvas").toDataURL("image/png").split(",")[1];}',t)
            im=Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
            combined=Image.new('RGB',(1600,680),'white');combined.paste(im,(0,90));d=ImageDraw.Draw(combined)
            d.text((25,7),title,font=FONT,fill='#1D1D1F')
            label=f'实测 t={t:.3f}s / {end:.3f}s · 两侧共同时间压缩；10秒教学回放' if real else f'教学进度 {t/end*100:.0f}% · 机制/统计揭示，不是实测计算耗时'
            d.text((25,49),label,font=SMALL,fill='#6E6E73')
            frames.append(combined.resize((1280,544),Image.Resampling.LANCZOS).quantize(colors=128))
        file=MEDIA/(GIF_PAGES[n]+'.gif');frames[0].save(file,save_all=True,append_images=frames[1:],duration=[120]*80+[2400],loop=0,optimize=True,disposal=1)
        frames[-1].convert('RGB').save(MEDIA/(GIF_PAGES[n]+'-poster.png'))
        manifest.append({'page':n,'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size,'requested_frames':81,'actual_frames':Image.open(file).n_frames,'display_ms':12000,'clock':'actual seconds, compressed equally' if real else 'teaching steps, no measured timing','recorded_seconds':end if real else None})
        print('GIF',n,file.name,file.stat().st_size,flush=True)
    goto(66);root=page.locator('.slide.active .ft-player');selector=root.locator('select');options=selector.locator('option').count();assert options==16
    for i in range(options):
        selector.select_option(index=i);assert float(root.get_attribute('data-time'))==0
        root.locator('[data-ft=end]').click();assert float(root.get_attribute('data-time'))>0
    assert not errors,errors
    assert not [u for u in requests if u.startswith(('http://','https://'))]
    browser.close()
if '--verify-only' not in sys.argv:(MEDIA/'gif-manifest.json').write_text(json.dumps(sorted(manifest,key=lambda x:x['page']),ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'finetune-animation-qa.json').write_text(json.dumps({'passed':True,'pages_rendered':70,'new_animation_checks':checks,'runtime_conditions':16,'script_errors':errors,'external_resource_requests':0,'deck_sha256':hashlib.sha256((HERE/'deck.html').read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
print('PASSED',len(checks),'animations;',options,'runtime conditions',flush=True)
