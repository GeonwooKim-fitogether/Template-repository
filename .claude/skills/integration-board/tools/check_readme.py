#!/usr/bin/env python3
"""USER-GUIDE.md가 다시 길어지지 않았는지 검사한다.

이 안내서가 한 번 644줄까지 자란 원인은 길이가 아니라 중복이었다. 스키마 항목 설명은
reference/board-schema.md에, 화면 설명은 보드 화면 자체에, 오류 설명은 엔진 출력에 이미 있다.
그래서 여기서는 '다른 곳이 이미 답하는 것을 옮겨 적었는가'를 숫자로 막는다.
코드 블록 안은 세지 않는다(최소 예시와 실제 출력은 옮겨 적기가 아니라 산출물이다).
"""
import re, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
GUIDE, SCHEMA = HERE / "USER-GUIDE.md", HERE / "reference" / "board-schema.md"
LIMITS = dict(total=120, h2=6, h3=0, prose_run=6, prose=30, names=8, first_board=25, cmds=3)

lines = GUIDE.read_text(encoding="utf-8").splitlines()
in_code, code_free, blocks, cur = False, [], [], None
for i, ln in enumerate(lines, 1):
    if ln.startswith("```"):
        in_code = not in_code
        if in_code: cur = []
        else: blocks.append(cur)
        continue
    (cur if in_code else code_free).append((i, ln))

def is_prose(ln):
    s = ln.strip()
    return bool(s) and not re.match(r"^(#|\||[-*+]\s|\d+[.)]\s|!\[|<)", s)

prose = [i for i, ln in code_free if is_prose(ln)]
# 산문 '구간'은 빈 줄로 끊기지 않는다. 표·코드·목록·그림·소제목이 나와야 끊긴다.
runs, run = [], []
for i, ln in code_free:
    if is_prose(ln): run.append(i)
    elif ln.strip():
        if len(run) > LIMITS["prose_run"]: runs.append(run[0])
        run = []
if len(run) > LIMITS["prose_run"]: runs.append(run[0])

# 스키마 항목 이름 — 정본에서 뽑아 안내서 산문·표와 대조한다(파일명 속 이름은 제외).
names = set(re.findall(r"^### \d[\d.]* ([A-Za-z][\w]*) ", SCHEMA.read_text(encoding="utf-8"), re.M))
names |= set(re.findall(r"[a-zA-Z][\w]*", " ".join(
    re.findall(r"^(?:필수|선택):(.+)$", SCHEMA.read_text(encoding="utf-8"), re.M))))
body = "\n".join(ln for _, ln in code_free)
hit = sorted(n for n in names if re.search(rf"(?<![\w.\-/]){re.escape(n)}(?![\w.\-/])", body))

run_line, cmds = None, []
for blk in blocks:
    if any("integration_board_engine.py" in ln for _, ln in blk):
        cmds = [i for i, ln in blk if ln.strip() and not ln.strip().startswith("#")]
        run_line = max(i for i, ln in blk if "integration_board_engine.py" in ln)
        break

fails = []
def check(label, got, cap):
    if got > cap: fails.append(f"  {label}: {got} (상한 {cap} · {got - cap} 초과)")

check("총 줄수", len(lines), LIMITS["total"])
check("'##' 소제목 수", sum(1 for l in lines if re.match(r"^## ", l)), LIMITS["h2"])
check("'###' 소제목 수", sum(1 for l in lines if re.match(r"^### ", l)), LIMITS["h3"])
check("산문 줄 총합", len(prose), LIMITS["prose"])
check(f"{LIMITS['prose_run']}줄 초과 산문 구간 — 시작 줄 {runs[:6]}", len(runs), 0)
check(f"본문에 등장한 스키마 항목 이름 {hit[:10]}", len(hit), LIMITS["names"])
check("첫 보드 명령이 나오는 줄", run_line or 999, LIMITS["first_board"])
check("첫 보드까지의 명령 수", len(cmds), LIMITS["cmds"])

if fails:
    print("USER-GUIDE.md 검사 실패 — 다른 곳이 이미 답하는 것을 옮겨 적었는지 보라.\n" + "\n".join(fails))
    sys.exit(1)
print(f"USER-GUIDE.md 검사 통과 — {len(lines)}줄 · 산문 {len(prose)}줄 · 스키마 이름 {len(hit)}개 "
      f"· 첫 보드 {run_line}줄째(명령 {len(cmds)}개)")
