#!/usr/bin/env python3
# drbfm-qa ENGINE — 고정 템플릿(FITogether 변경점/DRBFM-QA 양식). 편집 금지.
# 입력: 같은 폴더의 drbfm_data.py (META + ITEMS). 실행: python3 drbfm_engine.py → META['out'] HTML.
import html, json
from drbfm_data import META, ITEMS

# 고정 CheckList 11항목(FITogether 양식). 데이터는 항목별 [Y/N, 근거]만 채운다.
CHECKLIST = ['재료비 변경 여부','투자비 필요 여부','SVC 호환성 여부','불용재고 발생 여부',
             'FW호환성 여부','SPEC변경 여부','SW 영향 여부','HW↔FW 영향 여부',
             '사용자 시나리오 영향 여부','매뉴얼 변경 영향 여부','라벨 변경 영향 여부']
def e(s): return html.escape(str(s if s is not None else ''))
SEV = {'높음':'#d24a68','중간':'#d99320','낮음':'#2e9e68'}

def kv(label, val):
    return f'<div class="kv"><b>{e(label)}</b> {e(val)}</div>' if val else ''

def checklist_html(cl):
    rows=[]
    yn_count=0
    for lab in CHECKLIST:
        v = cl.get(lab)
        yn = (v[0] if v else '').upper()
        why = v[1] if v and len(v)>1 else ''
        if yn=='Y': yn_count+=1
        cls = 'y' if yn=='Y' else ('n' if yn=='N' else 'u')
        badge = {'y':'Y','n':'N'}.get(cls,'—')
        rows.append(f'<li class="cli {cls}"><span class="ck">{badge}</span>'
                    f'<span class="cl-lab">{e(lab)}</span>'
                    f'{f"<span class=cl-why>{e(why)}</span>" if why else ""}</li>')
    return f'<ul class="cklist">{"".join(rows)}</ul>', yn_count

def sol_block(title, d, keys):
    if not d: return ''
    inner=''.join(kv(k, d.get(k2)) for k,k2 in keys if d.get(k2))
    return f'<div class="solb"><div class="solh">{e(title)}</div>{inner}</div>' if inner else ''

def compare_html(ch):
    def col(rows):
        return ''.join(f'<div class="cmpr"><span class="cmpk">{e(k)}</span>'
                       f'<span class="cmpv">{e(v)}</span></div>' for k,v in (rows or []))
    def img(o):
        if not o: return ''
        src = o['src'] if isinstance(o, dict) else o
        ov = o.get('overlay', '') if isinstance(o, dict) else ''
        return f'<div class="cmpimg"><img src="{src}" alt="회로도">{ov}</div>'
    return (f'<div class="cmpcol asis"><div class="cmph">As Is</div>{img(ch.get("asis_img"))}{col(ch.get("asis"))}</div>'
            f'<div class="cmpcol tobe"><div class="cmph">To Be</div>{img(ch.get("tobe_img"))}{col(ch.get("tobe"))}</div>')

def item_html(it, idx):
    iss, cau, sol = it.get('issue',{}), it.get('cause',{}), it.get('solution',{})
    cl_html, ycnt = checklist_html(it.get('checklist',{}))
    whys = ''.join(f'<div class="why"><b>Why {i+1}</b> {e(w)}</div>' for i,w in enumerate(cau.get('whys',[])))
    attach = iss.get('attach') or []
    sev = it.get('severity','')
    return f'''<section class="item">
  <div class="ihd"><span class="ino">{e(it.get('no',''))}</span>
    <h2>{e(it.get('title',''))}</h2>
    <span class="sev" style="background:{SEV.get(sev,'#8b98a4')}">{e(sev or '—')}</span>
    <span class="date">{e(it.get('date',''))}</span></div>

  <div class="secttl">{idx}. 제품 개선 내용 정의</div>
  <div class="grid3">
    <div class="col"><div class="colh">Issue</div>
      <div class="colsub">문제점 / 개선점</div>
      {kv('Inquiry No', it.get('no'))}
      {kv('발견 날짜', it.get('date'))}
      {kv('문제 설명', iss.get('desc'))}
      {kv('영향 시스템·부품', iss.get('affected'))}
      {f'<div class="kv"><b>첨부</b> '+' · '.join(e(a) for a in attach)+'</div>' if attach else ''}
      <div class="kv"><b>심각도</b> <span class="sevtxt" style="color:{SEV.get(sev,'#8b98a4')}">{e(sev or '—')}</span></div>
    </div>
    <div class="col"><div class="colh">Cause Analysis</div>
      <div class="colsub">5 Why 분석</div>
      {kv('문제상황', cau.get('situation'))}
      {whys}
      <div class="colsub" style="margin-top:12px">CheckList <span class="ycnt">Y {ycnt}/{len(CHECKLIST)}</span></div>
      {cl_html}
    </div>
    <div class="col"><div class="colh">Solution</div>
      {sol_block('임시 대책', sol.get('temp'), [('대책 설명','desc'),('적용 일자','date'),('재고품 운용','stock'),('SVC 방법','svc')])}
      {sol_block('근본 대책', sol.get('perm'), [('대책 설명','desc'),('적용 계획','plan'),('적용 일자','date'),('재고품 운용','stock'),('SVC 방법','svc')])}
      {sol_block('테스트 필요 여부', sol.get('test'), [('필요','need'),('테스트 유형','type'),('테스트 계획','plan')])}
    </div>
  </div>

  <div class="secttl">변경점 (부품 비교)</div>
  <div class="cmp">{compare_html(it.get('change',{}))}</div>
</section>'''

items = ''.join(item_html(it, 2) for it in ITEMS)
CSS = '''
*{box-sizing:border-box} body{margin:0;background:#eef1f5;color:#16212c;font:14px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.5}
.wrap{max-width:1240px;margin:0 auto;padding:22px 18px 60px}
.top{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:8px}
.top h1{font-size:22px;font-weight:800;margin:0}
.top .sub{color:#53626e;font-size:13px;margin-top:4px}
.conf{border:2px solid #d24a68;color:#d24a68;font-weight:800;font-size:13px;padding:5px 12px;border-radius:4px;white-space:nowrap;letter-spacing:.02em}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:11.5px;color:#53626e;margin:8px 0 18px}
.item{background:#fff;border:1px solid #dce2e8;border-radius:12px;box-shadow:0 1px 2px rgba(22,33,44,.05),0 8px 22px rgba(22,33,44,.06);padding:16px 18px;margin-bottom:22px}
.ihd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.ihd .ino{font-family:ui-monospace,Menlo,monospace;font-size:11px;font-weight:700;color:#53626e;background:#eef1f5;border-radius:5px;padding:2px 8px}
.ihd h2{font-size:16px;font-weight:800;margin:0;flex:1;min-width:220px}
.ihd .sev{font-size:10.5px;font-weight:800;color:#fff;padding:2px 9px;border-radius:6px}
.ihd .date{font-size:11px;color:#8b98a4;font-family:ui-monospace,monospace}
.secttl{font-size:12px;font-weight:800;color:#16212c;background:#e6eaef;border:1px solid #dce2e8;border-radius:6px;padding:6px 11px;margin:14px 0 10px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:0;border:1px solid #dce2e8;border-radius:8px;overflow:hidden}
@media(max-width:900px){.grid3{grid-template-columns:1fr}}
.col{padding:12px 14px;border-left:1px solid #dce2e8}
.col:first-child{border-left:0}
.colh{font-size:12px;font-weight:800;text-align:center;color:#16212c;background:#f4f6f8;margin:-12px -14px 10px;padding:7px;border-bottom:1px solid #dce2e8}
.colsub{font-size:11px;font-weight:800;color:#53626e;margin:8px 0 5px;letter-spacing:.02em}
.kv{font-size:12px;line-height:1.5;margin:3px 0;word-break:keep-all}
.kv b{color:#16212c;font-weight:700}
.why{font-size:12px;margin:2px 0;color:#16212c} .why b{color:#d24a68;font-family:ui-monospace,monospace;font-size:11px;margin-right:4px}
.cklist{list-style:none;margin:4px 0 0;padding:0;display:flex;flex-direction:column;gap:3px}
.cli{display:flex;align-items:flex-start;gap:7px;font-size:11.5px}
.cli .ck{flex:none;width:17px;height:17px;border-radius:5px;font-size:10px;font-weight:800;color:#fff;display:flex;align-items:center;justify-content:center}
.cli.y .ck{background:#d24a68} .cli.n .ck{background:#9aa7b2} .cli.u .ck{background:#cbd3da}
.cli.y .cl-lab{font-weight:700}
.cl-lab{color:#16212c} .cl-why{color:#8b98a4;margin-left:5px}
.ycnt{font-family:ui-monospace,monospace;font-weight:700;color:#d24a68;font-size:10.5px;margin-left:4px}
.solb{border:1px solid #dce2e8;border-radius:7px;padding:8px 10px;margin-bottom:8px}
.solh{font-size:11.5px;font-weight:800;color:#16212c;margin-bottom:5px}
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:0;border:1px solid #dce2e8;border-radius:8px;overflow:hidden}
.cmpcol{padding:10px 12px} .cmpcol.tobe{border-left:1px solid #dce2e8;background:#fbfcfd}
.cmph{font-size:12px;font-weight:800;text-align:center;padding:6px;margin:-10px -12px 8px;border-bottom:1px solid #dce2e8;background:#f4f6f8}
.cmpcol.tobe .cmph{background:#fdeef1;color:#d24a68}
.cmpimg{position:relative;background:#fff;border:1px solid #dce2e8;border-radius:6px;margin-bottom:8px;overflow:hidden;line-height:0}
.cmpimg img{display:block;width:100%;height:auto}
.cmpimg .cloud{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.cmpr{display:flex;gap:8px;font-size:12px;padding:3px 0;border-bottom:1px dotted #e6eaef}
.cmpk{flex:none;width:44%;color:#53626e;font-weight:600;word-break:keep-all}
.cmpv{font-family:ui-monospace,monospace;color:#16212c;word-break:break-all}
.foot{margin-top:16px;font-size:11px;color:#8b98a4}
@media print{body{background:#fff} .item{box-shadow:none;break-inside:avoid}}
'''
HTML = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(META.get('title','변경점 · DRBFM-QA'))}</title><style>{CSS}</style></head><body>
<div class="wrap">
  <div class="top">
    <div><h1>{e(META.get('title',''))}</h1><div class="sub">{e(META.get('sub',''))}</div></div>
    <div class="conf">CONFIDENTIAL OF FITOGETHER</div>
  </div>
  <div class="legend"><span>변경점 {len(ITEMS)}건</span><span>· CheckList Y = 영향 있음(점검 필요)</span>
    <span>· As Is=이전(기준) / To Be=변경(신규)</span></div>
  {items}
  <div class="foot">{e(META.get('source',''))} · FITogether 하드웨어팀 · DRBFM-QA (자동 초안 + 엔지니어 검토)</div>
</div></body></html>'''
open(META.get('out','drbfm-qa.html'), 'w', encoding='utf-8').write(HTML)
print('items:', len(ITEMS), '| bytes:', len(HTML), '| out:', META.get('out'))
