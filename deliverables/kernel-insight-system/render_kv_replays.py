"""Render the full deck and five GIFs directly from its measured canvas player."""
import pathlib,sys,json,io,base64,hashlib
from PIL import Image,ImageDraw,ImageFont
HERE=pathlib.Path(__file__).resolve().parent
deps=HERE.parents[1]/'data/local-archive/slide-python'
if deps.exists():sys.path.insert(0,str(deps))
from playwright.sync_api import sync_playwright
OUT=HERE/'rendered';OUT.mkdir(exist_ok=True)
DATA=json.load(open(HERE/'media/kv/animation-data.json',encoding='utf-8'))
pages={'dchat-1x1-cold':50,'dchat-1x8-warm':51,'dchat-4x8-warm':52,'seqbatch-4x8-warm':54,'coldwarm-d4x8':55}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',29)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21)
reports=[];checks=[];errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True,args=['--disable-gpu'])
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto((HERE/'deck.html').as_uri());page.evaluate('document.fonts.ready')
    count=page.locator('.slide').count()
    def goto(n):
        page.evaluate('document.activeElement.blur()')
        page.evaluate('(n)=>location.hash="#"+n',n)
        # Native navigation uses key events, rather than observing hash changes.
        page.keyboard.press('Home')
        if n!=1:
            for digit in str(n):page.keyboard.press(digit)
        page.wait_for_function('(n)=>document.querySelectorAll(".slide")[n-1].classList.contains("active")',arg=n)
        page.evaluate('document.fonts.ready')
    if '--only-gifs' not in sys.argv and '--verify-only' not in sys.argv:
        for n in range(1,count+1):
            goto(n);page.screenshot(path=str(OUT/f'slide-{n:02d}.png'))
    tiles=[Image.open(OUT/f'slide-{n:02d}.png') for n in range(1,count+1)]
    sheet=Image.new('RGB',(1970,((count+3)//4)*280+10),(200,205,212))
    for i,im in enumerate(tiles):sheet.paste(im.resize((480,270),Image.Resampling.LANCZOS),(10+(i%4)*490,10+(i//4)*280))
    sheet.save(OUT/'contact.png');sheet.save(HERE/'预览-全部页面.png')
    extra=Image.new('RGB',(1970,850),(200,205,212))
    for i,n in enumerate(range(49,59)):extra.paste(tiles[n-1].resize((480,270),Image.Resampling.LANCZOS),(10+(i%4)*490,10+(i//4)*280))
    extra.save(HERE/'media/kv/新增页面预览.png')
    for scene,n in pages.items():
        goto(n);root=page.locator('.slide').nth(n-1).locator('.kv-player');s=DATA['scenes'][scene]
        assert root.get_attribute('data-playing')=='false'
        page.keyboard.press('j');assert float(root.get_attribute('data-time'))>0
        page.keyboard.press('k');assert float(root.get_attribute('data-time'))==0
        root.locator('[data-kv=play]').click();page.wait_for_timeout(150)
        assert float(root.get_attribute('data-time'))>0 and root.get_attribute('data-playing')=='true'
        page.keyboard.press('ArrowRight');assert root.get_attribute('data-playing')=='false'
        goto(n);root=page.locator('.slide').nth(n-1).locator('.kv-player')
        root.locator('input').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',s['end']/2)
        assert abs(float(root.get_attribute('data-time'))-s['end']/2)<.002
        checks.append({'scene':scene,'page':n,'manual_event_steps':True,'play_pause':True,'leave_stops':True,'scrub':True,'no_autoplay':True})
        if '--verify-only' in sys.argv:continue
        frames=[]
        for k in range(81):
            t=s['end']*k/80
            b64=page.evaluate('''(t)=>{const r=document.querySelector('.slide.active .kv-player');r._kv.setTime(t);return r.querySelector('canvas').toDataURL('image/png').split(',')[1];}''',t)
            image=Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
            combined=Image.new('RGB',(1600,650),'white');combined.paste(image,(0,90));d=ImageDraw.Draw(combined)
            d.text((20,8),s['title'],font=font,fill='#1D1D1F');d.text((20,48),f't = {t:.3f}s  /  {s["end"]:.3f}s   · 共同时间尺；8秒教学回放，不是原速录像',font=small,fill='#6E6E73')
            frames.append(combined.resize((1280,520),Image.Resampling.LANCZOS).quantize(colors=128,method=Image.Quantize.MEDIANCUT))
        gif=HERE/'media/kv'/(scene+'.gif');durations=[100]*80+[2000]
        frames[0].save(gif,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True,disposal=1)
        frames[-1].convert('RGB').save(HERE/'media/kv'/(scene+'-poster.png'))
        reports.append({'scene':scene,'file':gif.name,'bytes':gif.stat().st_size,'sha256':hashlib.sha256(gif.read_bytes()).hexdigest(),
                        'frames':81,'display_ms':10000,'model_seconds':s['end'],'representative_repeat':s['repeat'],'trial_ids':[a['trial'] for a in s['arms']]})
        print('GIF',scene,gif.stat().st_size,flush=True)
    goto(56);root=page.locator('.slide.active .kv-player');selector=root.locator('.kv-scenes')
    for key in [k for k in DATA['scenes'] if k.startswith('dchat-')]:
        selector.select_option(key);assert root.get_attribute('data-scene')==key and float(root.get_attribute('data-time'))==0
        root.locator('[data-kv=end]').click();assert abs(float(root.get_attribute('data-time'))-DATA['scenes'][key]['end'])<.002
    goto(52);root=page.locator('.slide').nth(51).locator('.kv-player')
    root.locator('.kv-rate').select_option('0.25');root.locator('[data-kv=play]').click();page.wait_for_timeout(180)
    assert 0<float(root.get_attribute('data-time'))<.14
    goto(53);assert root.get_attribute('data-playing')=='false'
    goto(52);assert root.locator('.kv-rate').input_value()=='0.25'
    root.locator('[data-kv=play]').click();page.wait_for_timeout(180);assert 0<float(root.get_attribute('data-time'))<.14
    root.locator('[data-kv=reset]').click();root.locator('.kv-rate').select_option('1')
    assert not errors,errors
    browser.close()
if '--verify-only' not in sys.argv:(HERE/'media/kv/gif-manifest.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'kv-animation-qa.json').write_text(json.dumps({'passed':True,'pages_rendered':count,'checks':checks,'explorer_conditions':8,'speed_and_reentry_verified':True,'script_errors':errors,'deck_sha256':hashlib.sha256((HERE/'deck.html').read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
print('FULL_DECK_RENDERED',count,flush=True)
