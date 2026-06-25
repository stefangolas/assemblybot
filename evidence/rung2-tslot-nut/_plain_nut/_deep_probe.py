"""Deep-probe the SPA search result page to extract product codes / detail links."""
import sys, time, json
sys.path.insert(0, 'candidate_evidence/rung2-tslot-nut/_plain_nut')
from _scout_lib import open_tab, close_target

def load(tab, wait_s=3.0):
    for i in range(40):
        ready = tab.evaluate('document.readyState')
        url = tab.evaluate('location.href')
        if ready == 'complete' and 'misumi' in (url or ''):
            break
        time.sleep(0.5)
    time.sleep(wait_s)

JS = r"""
(() => {
  const out = {};
  // 1. all hrefs containing 'detail'
  out.detail_hrefs = Array.from(new Set(
    Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h && h.indexOf('detail') >= 0)
  )).slice(0, 30);
  // 2. all image srcs (often embed item/series code)
  out.img_srcs = Array.from(new Set(
    Array.from(document.querySelectorAll('img')).map(i => i.src).filter(s => s)
  )).slice(0, 40);
  // 3. any text that looks like an HNAT/HNTS/HNSDR/HNTH part number
  const body = document.body.innerText || '';
  const pnHits = [];
  const re = /(HNAT[A-Z0-9.-]+|HNTS[A-Z0-9.-]+|HNSDR[A-Z0-9.-]+|HNTH[A-Z0-9.-]+|HNTAS[A-Z0-9.-]+|HNTJ[A-Z0-9.-]+)/g;
  let m;
  while ((m = re.exec(body)) && pnHits.length < 40) pnHits.push(m[1]);
  out.pn_hits = Array.from(new Set(pnHits));
  // 4. any data-* attributes on product cards revealing codes
  out.data_codes = Array.from(new Set(
    Array.from(document.querySelectorAll('[data-part-number],[data-productcode],[data-seriescode],[data-code]'))
      .map(e => e.getAttribute('data-part-number') || e.getAttribute('data-productcode')
            || e.getAttribute('data-seriescode') || e.getAttribute('data-code'))
      .filter(Boolean)
  )).slice(0, 40);
  // 5. window state
  out.window_keys = Object.keys(window).filter(k => /result|product|search|item/i.test(k)).slice(0, 20);
  // 6. count of product-like cards
  out.card_count = document.querySelectorAll('[class*=product],[class*=item],[class*=card]').length;
  return out;
})()
"""

url = 'https://us.misumi-ec.com/vona2/result/?Keyword=HNAT6&isReSearch=1'
tab = open_tab(url)
try:
    load(tab, 4.0)
    # give SPA a moment more
    time.sleep(3)
    res = tab.evaluate(JS)
    print(json.dumps(res, indent=2, default=str).encode('ascii','replace').decode()[:4000])
finally:
    tid = tab.target_id
    tab.close()
    close_target(tid)
