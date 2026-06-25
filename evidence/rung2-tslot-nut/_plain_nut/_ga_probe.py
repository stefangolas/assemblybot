"""Read the ga_products window state from a MISUMI search result SPA page."""
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
  const safe = v => { try { return JSON.parse(JSON.stringify(v)); } catch(e){ return String(v); } };
  return {
    res_num: window.ga_search_res_num,
    products: (window.ga_products || []).slice(0, 20).map(safe),
    fix: (window.ga_fixproducts || []).slice(0, 10).map(safe),
    unfix: (window.ga_unfixproducts || []).slice(0, 10).map(safe),
    pn: window.ga_products_pn_num,
    cls: window.ga_class_name_simple_product,
    pcode: window.ga_products_cd,
  };
})()
"""

url = sys.argv[1] if len(sys.argv) > 1 else 'https://us.misumi-ec.com/vona2/result/?Keyword=HNAT6&isReSearch=1'
tab = open_tab(url)
try:
    load(tab, 4.0)
    time.sleep(2)
    res = tab.evaluate(JS)
    s = json.dumps(res, indent=2, default=str)
    print(s.encode('ascii','replace').decode()[:6000])
finally:
    tid = tab.target_id
    tab.close()
    close_target(tid)
