"""Breadth-first discovery probe: search MISUMI for M5 / 8 mm slot T-slot nuts."""
import sys, time, json
sys.path.insert(0, 'candidate_evidence/rung2-tslot-nut/_plain_nut')
from _scout_lib import open_tab, close_target

def load(tab, wait_s=2.0):
    for i in range(30):
        ready = tab.evaluate('document.readyState')
        url = tab.evaluate('location.href')
        if ready == 'complete' and 'misumi' in (url or ''):
            break
        time.sleep(0.5)
    time.sleep(wait_s)

JS_ANCHORS = r"""
(() => {
  const out = [];
  document.querySelectorAll('a').forEach(a => {
    const t = (a.innerText || '').trim();
    const h = a.href || '';
    if (t || h) out.push({t: t.slice(0, 80), h: h.slice(0, 150)});
  });
  return out.slice(0, 60);
})()
"""

def probe(url, wait_s=3.0):
    tab = open_tab(url)
    try:
        load(tab, wait_s)
        title = tab.evaluate('document.title')
        final_url = tab.evaluate('location.href')
        print('=== URL:', url)
        print('=== FINAL:', final_url)
        print('=== TITLE:', title)
        anchors = tab.evaluate(JS_ANCHORS) or []
        # filter to interesting
        keep = [a for a in anchors if 'detail' in a['h'] or 'HNAT' in a['t'].upper()
                or 'HNTS' in a['t'].upper() or 'nut' in a['t'].lower() or 'HNSDR' in a['t'].upper()
                or 'HNTHR' in a['t'].upper()]
        for a in keep[:40]:
            print(f"  {a['t']!r} -> {a['h']}")
        return tab
    except Exception as e:
        print('ERR', e)
        tid = tab.target_id
        tab.close()
        close_target(tid)
        raise

if __name__ == '__main__':
    queries = sys.argv[1:] or [
        'https://us.misumi-ec.com/vona2/result/?Keyword=HNAT6&PNSearch=HNAT6',
        'https://us.misumi-ec.com/vona2/result/?Keyword=HNTAS6&PNSearch=HNTAS6',
        'https://us.misumi-ec.com/vona2/result/?Keyword=HNSDR6&PNSearch=HNSDR6',
    ]
    for q in queries:
        try:
            tab = probe(q, 3.5)
            tid = tab.target_id
            tab.close()
            close_target(tid)
        except Exception as e:
            print('probe failed', q, e)
        print()
