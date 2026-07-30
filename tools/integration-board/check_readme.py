#!/usr/bin/env python3
"""사용 안내서(USER-GUIDE.html)가 다시 산문 덩어리로 불어나지 않았는지 검사한다.

이 안내서는 한 번 644줄까지 자랐다가 거부당했다. 원인은 길이 자체가 아니라 중복이었다.
스키마 항목 설명은 reference/board-schema.md에, 화면 설명은 보드 화면 자체에, 오류 해설은
엔진 출력에 이미 있는데 문서가 그것을 한 번 더 적었다. "짧게 구조적으로 써라"를 사람의
의지에 맡기면 또 불어나므로, 여기서 기계가 막는다.

안내서가 HTML이 되면서 재는 단위가 줄에서 글자로 바뀌었다. HTML은 한 줄에 태그가 길게
이어져 줄 수가 분량을 뜻하지 않기 때문이다. 그래서 표·코드·그림·스크립트를 걷어낸
'순수 산문'의 글자 수를 센다. 코드 블록과 그림은 세지 않는다(최소 예시와 실제 출력은
옮겨 적기가 아니라 산출물이다).

이 도구는 창고 전용이라 동기화로 프로젝트에 내려가지 않는다.
쓸 때: python3 tools/integration-board/check_readme.py
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude" / "skills" / "integration-board"
GUIDE, SCHEMA = SKILL / "USER-GUIDE.html", SKILL / "reference" / "board-schema.md"

# 산문은 현재 약 1,600자다. 여기서 크게 벌어지면 문서가 다시 설명을 떠안기 시작한 것으로 본다.
# 크기(kb) 상한은 넉넉하다 — 이 검사가 막으려는 것은 산문 비대이지 그림 무게가 아니다.
# 실제 보드 스크린샷 한 장이 첫 사용자에게 가장 값이 컸으므로, 그림에는 여유를 준다.
LIMITS = dict(prose_chars=2200, h2=6, names=8, kb=300, min_figures=1)

if not GUIDE.exists():
    sys.exit(f"안내서를 찾을 수 없습니다: {GUIDE}")
html = GUIDE.read_text(encoding="utf-8")

# 산문만 남긴다 — 스크립트·스타일·그림·코드·표를 걷어낸다.
stripped = html
for pat in (r"<script\b.*?</script>", r"<style\b.*?</style>", r"<svg\b.*?</svg>",
            r"<pre\b.*?</pre>", r"<table\b.*?</table>", r"<!--.*?-->"):
    stripped = re.sub(pat, " ", stripped, flags=re.S | re.I)
prose = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", stripped)).strip()

h2 = len(re.findall(r"<h2\b", html, re.I))
figures = len(re.findall(r"<svg\b", html, re.I))
size_kb = len(html.encode("utf-8")) / 1024

# 스키마 항목 이름이 산문에 등장하면 정본과 다시 겹치기 시작한 신호다.
names = set()
if SCHEMA.exists():
    src = SCHEMA.read_text(encoding="utf-8")
    names |= set(re.findall(r"^#{2,3} \d[\d.]* ([A-Za-z][\w]*) ", src, re.M))
    names |= set(re.findall(r"[a-zA-Z][\w]*", " ".join(
        re.findall(r"^(?:필수|선택):(.+)$", src, re.M))))
hit = sorted(n for n in names if len(n) > 3 and re.search(rf"(?<![\w.\-/]){re.escape(n)}(?![\w.\-/])", prose))

fails = []
def check(label, got, cap, unit=""):
    if got > cap:
        fails.append(f"  {label}: {got}{unit} (상한 {cap}{unit} · {got - cap}{unit} 초과)")

check("산문 글자 수", len(prose), LIMITS["prose_chars"], "자")
check("절 제목(h2) 수", h2, LIMITS["h2"], "개")
check(f"산문에 등장한 스키마 항목 이름 {hit[:8]}", len(hit), LIMITS["names"], "개")
check("파일 크기", round(size_kb), LIMITS["kb"], "KB")
if figures < LIMITS["min_figures"]:
    fails.append(f"  그림(인라인 SVG)이 {figures}개다 — 최소 {LIMITS['min_figures']}개는 있어야 한다."
                 " 이 안내서는 그림이 중심이고 글은 그 주변이다")

if fails:
    print("USER-GUIDE.html 검사 실패 — 다른 곳이 이미 답하는 것을 옮겨 적었는지 보라.")
    print("  스키마 규격은 reference/board-schema.md가, 화면 설명은 보드 자신이,")
    print("  오류 해설은 엔진 출력이 이미 한다. 그 셋과 겹치면 지운다.")
    print("\n".join(fails))
    sys.exit(1)
print(f"USER-GUIDE.html 검사 통과 — 산문 {len(prose)}자 · 절 {h2}개 · 그림 {figures}개 "
      f"· 스키마 이름 {len(hit)}개 · {size_kb:.0f}KB")
