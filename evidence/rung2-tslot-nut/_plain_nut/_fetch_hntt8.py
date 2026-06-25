"""Fetch the HNTT8 drawing image and reconstruct the exact M5 PN."""
import sys, time, json, base64
from pathlib import Path
sys.path.insert(0, 'candidate_evidence/rung2-tslot-nut/_plain_nut')
from _scout_lib import open_tab, close_target

OUT = Path('candidate_evidence/rung2-tslot-nut/_plain_nut')
url = 'https://us.misumi-ec.com/vona2/detail/110302256040/?HissuCode=HNTT8&PNSearch=HNTT8&seriesCode=110302256040&tab=drawingAndSpecifications&Page=1'
tab = open_tab(url)
try:
    for i in range(40):
        if tab.evaluate('document.readyState') == 'complete':
            break
        time.sleep(0.5)
    time.sleep(4)

    # 1. Find the configurator's PN-field structure (option labels for thread)
    JS_CFG = r"""
    (() => {
      // Look for select elements + their options (the configurator)
      const sels = Array.from(document.querySelectorAll('select')).map(s => ({
        name: s.name || s.id || s.getAttribute('aria-label') || '',
        label: (s.closest('tr,div')?.querySelector('label,th,.label')?.innerText || '').trim().slice(0,40),
        options: Array.from(s.options).slice(0,20).map(o => ({v: o.value, t: o.text.trim().slice(0,40)}))
      }));
      // Also find the displayed/configured PN and any "Part Number" value
      const pnNodes = Array.from(document.querySelectorAll('[class*=partNumber],[class*=PartNumber],[id*=partNumber]'))
        .map(n => (n.innerText||n.value||'').trim().slice(0,60)).filter(Boolean);
      // Find the HissuCode input value (the configured PN the user would order)
      const hissu = document.querySelector('[name=HissuCode],#HissuCode,input[name*=issu]')?.value || '';
      // Any hidden inputs carrying PN
      const hidden = Array.from(document.querySelectorAll('input[type=hidden]')).map(i=>({n:i.name,v:i.value})).filter(x=>/issu|part|pn/i.test(x.n)).slice(0,10);
      return JSON.stringify({sels, pnNodes, hissu, hidden});
    })()
    """
    cfg = tab.evaluate(JS_CFG)
    print('=== CONFIGURATOR ===')
    print((cfg or 'none').encode('ascii','replace').decode()[:6000])

    # 2. Fetch the drawing image as base64, save it, and also grab all related drawings
    JS_FETCH_IMGS = r"""
    (async () => {
      const urls = [
        'https://us.misumi-ec.com/linked/item/10302256040/img/drw_01.gif',
        'https://us.misumi-ec.com/linked/item/10302256040/img/drw_02.gif',
        'https://us.misumi-ec.com/linked/item/10302256040/img/drw_03.gif'
      ];
      const out = [];
      for (const u of urls) {
        try {
          const r = await fetch(u);
          if (!r.ok) { out.push({u, status: r.status}); continue; }
          const buf = new Uint8Array(await r.arrayBuffer());
          let bin = ''; const CH = 0x8000;
          for (let i = 0; i < buf.length; i += CH) bin += String.fromCharCode.apply(null, buf.subarray(i, i+CH));
          out.push({u, size: buf.length, b64: btoa(bin)});
        } catch(e) { out.push({u, err: String(e)}); }
      }
      return out;
    })()
    """
    imgs = tab.evaluate(JS_FETCH_IMGS, await_promise=True)
    if imgs:
        for im in imgs:
            if im.get('b64'):
                data = base64.b64decode(im['b64'])
                # gif index from URL
                idx = im['u'].split('drw_')[1].split('.')[0]
                p = OUT / f'hntt8_drw_{idx}.gif'
                p.write_bytes(data)
                print(f'saved {p} ({im["size"]} bytes)')
                # convert to png via PIL
                try:
                    from PIL import Image
                    pngp = OUT / ('hntt8_drw_' + idx + '.png')
                    Image.open(p).convert('RGB').save(str(pngp))
                    print('  -> png ' + str(pngp))
                except Exception as e:
                    print('  PIL convert failed:', e)
            else:
                print('img miss:', im)

    # 3. Screenshot the spec table area for the record
    tab.screenshot(str(OUT / 'hntt8_page_full.png'))
    print('screenshot saved')
finally:
    tid = tab.target_id
    tab.close()
    close_target(tid)
