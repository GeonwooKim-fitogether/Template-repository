#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수집기 확인 — 녹여 둔 GitHub 응답으로 board.json 을 만들고, 그것이 엔진을 통과하는지 본다.

왜 이 시험이 있나. 수집기가 만드는 board.json 은 사람이 눈으로 훑지 않는다(사건마다
기계가 쓰고 기계가 읽는다). 그래서 수집 규칙이 조용히 어긋나면 아무도 모른 채 보드가
틀린 사실을 말하게 된다. 이 시험은 네트워크 없이 그 규칙을 못 박는다.

실제로 이 시험을 쓰다가 잡은 것이 하나 있다. main 에서 통과한 검사가 어떤 PR 에서
실패하면 "통과인데 위반 1건"이라는 앞뒤가 안 맞는 회차가 나왔고, 엔진이 그것을 거부했다.
그래서 '걸린 것이 있는 검사는 통과로 보고하지 않는다'를 규칙으로 세우고 여기 못 박았다.

실행:  python3 tools/integration-board/test_collect.py
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COLLECT = os.path.join(ROOT, ".claude", "workflows", "board-collect.mjs")
ENGINE = os.path.join(ROOT, ".claude", "skills", "integration-board", "assets",
                      "integration_board_engine.py")
FIXTURE = os.path.join(HERE, "board-collect.fixture.json")
MANUAL = os.path.join(HERE, "board-collect.manual-fixture.json")
CONFIG = os.path.join(ROOT, ".integration", "board.config.json")
MAP = os.path.join(ROOT, ".integration", "board.map.json")

npass = nfail = 0


def check(name, cond, detail=""):
    global npass, nfail
    npass += bool(cond)
    nfail += not cond
    print(f"  {'통과' if cond else '실패'}  {name}")
    if not cond and detail:
        print("        " + str(detail)[:500])


def work(data, wid):
    for w in data["works"]:
        if w["id"] == wid:
            return w
    return None


def main():
    tmp = tempfile.mkdtemp(prefix="board-collect-test-")
    out = os.path.join(tmp, "board.json")

    print("A. 녹여 둔 응답으로 사실을 모은다")
    r = subprocess.run([
        "node", COLLECT, "--fixture", FIXTURE, "--config", CONFIG, "--map", MAP, "--out", out,
    ], capture_output=True, text=True)
    check("수집기가 성공으로 끝난다", r.returncode == 0, r.stderr or r.stdout)
    if r.returncode != 0:
        print(f"\n결과: 통과 {npass} · 실패 {nfail}")
        return 1
    data = json.load(open(out, encoding="utf-8"))

    print("\nB. 작업 목록을 옳게 옮겼는가")
    ids = [w["id"] for w in data["works"]]
    check("열린 PR 과 최근 머지된 PR 만 담는다 (머지되지 않고 닫힌 것은 제외)",
          set(ids) == {"PR-50", "PR-49", "PR-48", "PR-47"}, ids)
    check("열린 PR 은 '검토대기'로 놓인다", work(data, "PR-50")["status"] == "review")
    check("머지된 PR 은 '배포완료'로 놓인다", work(data, "PR-49")["status"] == "shipped")
    check("변경 파일 경로로 제품 영역을 가른다 (.claude/skills → 스킬)",
          work(data, "PR-50")["area"] == "skills", work(data, "PR-50"))
    check("문서만 고친 요청은 문서 영역으로 간다",
          work(data, "PR-49")["area"] == "docs", work(data, "PR-49"))
    check("머지된 일은 진척 100 과 완료일을 갖는다",
          work(data, "PR-48")["progress"] == 100 and "completedAt" in work(data, "PR-48"))
    check("머지된 일은 시간 축에 올라간다 (계획 구간이 채워진다)",
          "planStart" in work(data, "PR-47") and "planEnd" in work(data, "PR-47"))
    check("열린 PR 은 며칠째 멈췄는지를 갖는다", "stalledDays" in work(data, "PR-50"))

    print("\nC. PR 본문 선언을 읽는가")
    w50 = work(data, "PR-50")
    check("계획 구간 선언을 읽는다",
          w50.get("planStart") == "2026-08-03" and w50.get("planEnd") == "2026-08-08", w50)
    check("진척률 선언을 읽는다", w50.get("progress") == 90, w50)
    check("해소 작업 선언을 읽는다", w50.get("fixes") == ["prgate"], w50)

    print("\nD. 검사 결과와 위반이 서로 어긋나지 않는가")
    vios = data.get("violations", [])
    runs = data.get("checkRuns", {})
    check("main 에서 실패한 검사는 지목 없는 위반이 된다",
          any(v["check"] == "sync" and "ref" not in v and v["severity"] == "block" for v in vios), vios)
    check("PR 에서 실패한 검사는 그 PR 을 지목하는 위반이 된다",
          any(v["check"] == "registry" and v.get("ref") == "PR-50" for v in vios), vios)
    check("걸린 것이 있는 검사는 통과로 보고하지 않는다 (엔진이 거부하던 모순)",
          all(runs.get(v["check"]) != "pass" for v in vios), runs)
    check("아직 도는 중인 체크는 결과로 세지 않는다", "overlap" not in runs, runs)
    check("대응표에 없는 체크는 싣지 않는다",
          all(k in {"prgate", "registry", "readme", "sync", "overlap"} for k in runs), runs)

    print("\nE. 사람이 선언한 사실을 얹는가 (board.manual.json)")
    # 이 층이 없으면 자동 수집으로 바꾼 순간 기계가 볼 수 없는 사실이 사라지고,
    # 사라진 만큼 판정이 좋아 보인다. 그 '거짓 초록불'을 막는 것이 이 절의 목적이다.
    out2 = os.path.join(tmp, "board-manual.json")
    r3 = subprocess.run([
        "node", COLLECT, "--fixture", FIXTURE, "--config", CONFIG, "--map", MAP,
        "--manual", MANUAL, "--out", out2,
    ], capture_output=True, text=True)
    check("얹은 채로도 수집기가 성공으로 끝난다", r3.returncode == 0, r3.stderr or r3.stdout)
    if r3.returncode == 0:
        d2 = json.load(open(out2, encoding="utf-8"))
        br = work(d2, "br-only-branch")
        check("PR 이 없는 브랜치 작업이 목록에 더해진다", br is not None, [w["id"] for w in d2["works"]])
        check("그 작업의 멈춘 기간이 그대로 실린다", br and br.get("stalledDays") == 19, br)
        check("이미 수집된 PR 은 적은 항목만 덮어쓴다 (제목·상태는 유지)",
              work(d2, "PR-50")["progress"] == 55
              and work(d2, "PR-50")["status"] == "review"
              and "판정 사유" in work(d2, "PR-50")["title"], work(d2, "PR-50"))
        check("PR 본문 선언은 얹지 않은 항목에 그대로 남는다",
              work(d2, "PR-50").get("fixes") == ["prgate"], work(d2, "PR-50"))
        vios2 = d2.get("violations", [])
        check("사람이 판정한 위반이 더해진다 (CI 가 알려 주지 않는 것)",
              any(v["check"] == "overlap" and v["severity"] == "block" for v in vios2), vios2)
        check("검사·무게가 같은 사람 발견 두 건이 하나로 줄지 않는다",
              sum(1 for v in vios2 if v["check"] == "overlap") == 2,
              [v for v in vios2 if v["check"] == "overlap"])
        check("기계가 모은 위반도 그대로 남는다",
              any(v["check"] == "sync" for v in vios2) and any(v["check"] == "registry" for v in vios2), vios2)
        check("얹은 뒤에도 통과와 위반이 어긋나지 않는다",
              all(d2["checkRuns"].get(v["check"]) != "pass" for v in vios2), d2["checkRuns"])
        r4 = subprocess.run([sys.executable, ENGINE, "--config", CONFIG, "--data", out2,
                             "--out", os.path.join(tmp, "board-manual.html")],
                            capture_output=True, text=True)
        check("얹은 결과도 엔진 검증을 통과한다", r4.returncode == 0, r4.stdout + r4.stderr)

    print("\nF. 엔진이 이 board.json 을 받아 보드를 그리는가")
    html = os.path.join(tmp, "board.html")
    r2 = subprocess.run([sys.executable, ENGINE, "--config", CONFIG, "--data", out, "--out", html],
                        capture_output=True, text=True)
    check("엔진이 검증을 통과하고 HTML 을 만든다", r2.returncode == 0, r2.stdout + r2.stderr)
    if r2.returncode == 0:
        body = open(html, encoding="utf-8").read()
        check("보드에 PR 제목이 실제로 실린다", "판정 사유가 원인을 이름으로" in body)
        check("걸린 검사에 해소 작업 표시가 실린다", "해소 작업" in body)

    print(f"\n결과: 통과 {npass} · 실패 {nfail}")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
