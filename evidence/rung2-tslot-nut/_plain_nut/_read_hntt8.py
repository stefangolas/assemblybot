"""Read the HNTT8 series detail page fully: spec table, dimensions, drawing images."""
import sys, time, json
sys.path.insert(0, 'candidate_evidence/rung2-tslot-nut/_plain_nut')
from _scout_lib import open_tab, close_target

url = 'https://us.misumi-ec.com/vona2/detail/110302256040/?HissuCode=HNTT8&PNSearch=HNTT8&seriesCode=110302256040&tab=drawingAndSpecifications&Page=1'
tab = open_tab(url)
try:
    for i in range(40):
        if tab.evaluate('document.readyState') == 'complete':
            break
        time.sleep(0.5)
    time.sleep(4)

    # 1. all spec table rows
    JS_TABLES = r"""
    (() => {
      const tables = Array.from(document.querySelectorAll('table'));
      const out = [];
      tables.forEach((t, ti) => {
        const rows = Array.from(t.querySelectorAll('tr')).map(tr =>
          Array.from(tr.querySelectorAll('th,td')).map(c => (c.innerText || '').trim().replace(/\s+/g, ' '))
        ).filter(r => r.some(c => c));
        if (rows.length) out.push({idx: ti, cls: t.className.slice(0,40), rows: rows.slice(0, 40)});
      });
      return JSON.stringify(out);
    })()
    """
    tables = tab.evaluate(JS_TABLES)
    if tables:
        print('=== TABLES ===')
        print(tables.encode('ascii', 'replace').decode()[:9000])

    # 2. drawing image srcs
    JS_IMGS = r"""
    (() => {
      const imgs = Array.from(document.querySelectorAll('img')).map(i => ({src: i.src, alt: (i.alt||'').slice(0,60)}))
        .filter(x => /drw|drawing|spec|dimension/i.test(x.src) || /drw|drawing|dimension/i.test(x.alt));
      return JSON.stringify(imgs.slice(0, 30));
    })()
    """
    print()
    print('=== DRAWING IMAGES ===')
    print((tab.evaluate(JS_IMGS) or 'none').encode('ascii','replace').decode()[:3000])

    # 3. configured specs area
    JS_CFG = r"""
    (() => {
      const nodes = document.querySelectorAll('[class*=config],[class*=spec],[class*=Spec]');
      const txt = Array.from(nodes).slice(0,15).map(n => (n.innerText||'').trim().slice(0,200)).filter(Boolean);
      return JSON.stringify(txt);
    })()
    """
    print()
    print('=== CONFIG/SPEC TEXT ===')
    print((tab.evaluate(JS_CFG) or 'none').encode('ascii','replace').decode()[:3000])
finally:
    tid = tab.target_id
    tab.close()
    close_target(tid)
