---
name: integration-board
description: Render a team-integration status board — a single self-contained HTML page showing whether many teams' work still fits together as one product. Fixed engine + per-project config + per-run data, so every run produces the identical layout and only the numbers change. Three bands (executive verdict, delivery status as kanban/gantt, quality baseline), a click-to-trace overlay linking a verdict card to the work items, shared assets and automated checks it depends on, and a Ground Control dark theme. Use when someone wants a cross-team/cross-part status board, an integration or program dashboard, a "what needs a decision" overview, or when /sysreport needs to publish its formal roll-up. Do NOT hand-author a new dashboard HTML — fill config + data and run the engine.
label_ko: 통합 현황판
summary_ko: 여러 팀의 일이 하나의 제품으로 맞물리는지 보여 주는 현황판 HTML을 매번 동일한 판으로 생성합니다. 종합 판정·실행 현황(칸반/간트)·품질 기준선 3단 구성에 연결 보기(카드를 누르면 얽힌 작업·공용 자산·검사만 밝아짐)를 갖췄고, 숫자와 판정은 엔진이 데이터에서 직접 계산합니다.
---

# Integration Board

여러 팀(파트·스쿼드)의 일이 **하나의 제품으로 맞물리고 있는지**를 한 장으로 보여 주는 현황판을 만든다. 산출물은 자체완결 HTML 하나이고, **매 실행 같은 판**이 나온다. 달라지는 것은 숫자뿐이다.

## 왜 이 스킬이 있나

현황판을 매번 새로 작성하면 세 가지가 무너진다. 첫째, 판이 매번 달라져 보는 사람이 매번 새로 해석해야 한다. 둘째, 숫자가 손으로 옮겨 적히다 틀린다. 셋째, 설명 자리에 그때그때의 산문이 들어가 보고서가 점점 길어진다.

그래서 이 스킬은 **화면을 만드는 일과 사실을 채우는 일을 갈라 놓는다.** 화면은 창고에 고정된 엔진이 그리고, 사람(또는 클로드)이 하는 일은 **사실을 스키마대로 채우는 것뿐**이다. 판정과 숫자는 엔진이 계산하므로 손으로 넣을 수 없고, 자유 서술 필드는 스키마에 아예 없으므로 끼워 넣을 수 없다.

## 세 겹 구조 (이 스킬의 핵심)

```
창고(고정)                     프로젝트가 소유                    매 실행
─────────────                 ─────────────                     ─────────
integration_board_engine.py    .integration/board.config.json    .integration/board.json
board_template.html            (어휘·관심사·설명 문장)            (작업·상태·날짜·위반)
        │                              │                                │
        └──────────────────────────────┴────────────────────────────────┘
                                       ↓
                          검증 → 계산 → 주입 → integration-board.html
```

- **엔진**은 레이아웃·색·상호작용·계산 규칙·문장 문법을 갖는다. 프로젝트별로 고치지 않는다.
- **config**는 그 프로젝트의 말(팀·제품 영역·공용 자산·자동 검사의 이름과 "뜻/걸리면" 설명)과 무엇을 상시로 지켜볼지(카드)를 담는다. 분기에 한 번 정도 바뀐다.
- **data**는 이번 회차의 사실만 담는다. 실행할 때마다 바뀐다.

## 고정 산출물 (엔진이 그리는 것 — 다시 디자인하지 말 것)

- **밴드 1 · 종합 판정** — 왼쪽에 판정 램프(위험/주의/정상)와 "결정 필요 n건", 오른쪽에 관심사 열별 카드. 카드에는 읽는 문장 한 줄과 "뜻/걸리면" 두 줄이 붙는다. 한 열에 4장 이상이면 급한 순 3장만 펼치고 나머지는 접는다.
- **밴드 2 · 실행 현황** — 같은 작업 목록을 **칸반**(상태 축)과 **간트**(시간 축)로 전환해 본다. 간트는 제품 영역 롤업 행을 눌러 펼치며, 계획·진척·지연 빗금·의존선·오늘선·목표일선을 그린다. 날짜가 없는 작업은 "일정 미정" 그룹으로 따로 모인다. 아래에 공용 자산 레인이 붙는다.
- **밴드 3 · 품질 기준선** — 자동 검사별 통과/주의/위반과 걸린 항목, 기획 정합성 막대, 이 보드가 못 보는 것을 적은 한 문단.
- **연결 보기(Trace)** — 밴드 1의 카드를 누르면 그와 얽힌 작업·공용 자산·검사만 100%로 남고 나머지는 흐려지며, 세 밴드를 가로지르는 선이 그려진다. 한 번에 하나만 켜지고, 재클릭·여백 클릭·Esc로 해제된다. 간트에서 대상이 접힌 영역 안에 있으면 자동으로 펼친다.
- **테마** — 밝은 테마가 기본이고 Ground Control 다크로 토글된다.
- **고정 상태 링크** — `?theme=light|gc` · `?view=kanban|gantt` · `?trace=<카드 key>`로 특정 화면을 그대로 다시 열 수 있다(스크린샷·재게시용).

## 절대 규칙

- **판을 새로 그리지 않는다.** 매번 HTML을 작성하는 대신 config·data를 채우고 엔진을 돌린다. 시각 디자인은 확정본이다.
- **숫자를 손으로 넣지 않는다.** 판정·건수·롤업·집계는 전부 엔진이 계산한다. 스키마에 그런 필드가 없다.
- **산문 슬롯을 만들지 않는다.** data에 자유 서술 필드가 없다. 설명 문장은 config에 한 번 적고 재사용한다. 여분 필드를 넣으면 엔진이 거부한다.
- **자체완결.** 인라인 CSS/JS만 쓰고 외부 요청이 0이다(Jira·Artifacts에서 바로 열린다). 엔진은 파이썬 표준 라이브러리만 쓰며 외부 패키지가 없다.
- **엔진에 프로젝트 어휘를 박지 않는다.** 팀·영역·자산·검사의 이름과 설명은 전부 config에서 온다. 엔진 코드에 특정 회사의 용어가 하드코딩되면 그것은 버그다.

## 절차

### 1단계 — 프로젝트에 config가 있는지 본다

`.integration/board.config.json`이 있으면 그것을 쓴다. 없으면 번들된 예시를 복사해 그 프로젝트의 어휘로 고친다.

```
mkdir -p .integration
cp <skill>/assets/board.config.example.json .integration/board.config.json
```

예시는 하드웨어팀 시스템(HTS)을 첫 인스턴스로 채워 둔 것이다. 다른 프로젝트라면 `areas`·`statuses`·`assets`·`checks`·`cards`의 이름과 "뜻/걸리면" 문장을 그 프로젝트의 말로 바꾼다. **엔진은 건드리지 않는다.**

config를 처음 쓸 때 정할 것은 결국 하나다 — **"우리는 무엇을 상시로 지켜보는가"**(`cards`). 카드마다 어떤 지표(`metric`)로 셀지를 고르면, 그 문장과 심각도는 엔진이 매 실행 계산한다. 지표 7종과 각각이 세는 것은 `reference/board-schema.md`의 표에 있다.

### 2단계 — 이번 회차 data를 만든다

`.integration/board.json`에 **사실만** 적는다. 근거는 실제 자료에서 읽는다(STATUS 문서, 열린 PR 목록, 최근 커밋, CI 결과 등). 지어내지 않는다.

```
cp <skill>/assets/board.example.json .integration/board.json    # 형태 참고용
```

적을 것은 작업 목록(`works`), 자동 검사에 걸린 것(`violations`), 날짜(`today`·`target`) 정도다. 무엇이 필수이고 무엇이 선택인지는 `reference/board-schema.md` 2절에 있다. **판정·건수·요약문을 적으려 하지 말 것** — 그런 필드는 없고, 넣으면 검증에서 거부된다.

### 3단계 — 엔진을 돌린다

```
python3 <skill>/assets/integration_board_engine.py \
  --config .integration/board.config.json \
  --data   .integration/board.json \
  --out    integration-board.html
```

인자를 모두 생략하면 번들된 예시로 데모가 나온다(엔진이 살아 있는지 확인할 때 쓴다).

검증에 걸리면 **아무 것도 만들지 않고** 오류를 전부 모아 보여 준 뒤 종료 코드 2로 끝난다. 메시지는 "어디가 · 무엇이 틀렸고 · 무엇을 쓸 수 있는지"를 함께 알려 준다. 조용히 넘어가는 일은 없으므로, 통과했다면 참조는 전부 성립한다는 뜻이다.

### 4단계 — 브라우저에서 확인한다 (필수)

헤드리스 Playwright(Chromium은 `/opt/pw-browsers`)로 산출 HTML을 열어 **페이지 오류가 0인지** 확인하고, 다음을 눌러 본다.

1. 칸반과 간트가 서로 전환되는지.
2. 밴드 1의 카드를 누르면 연결선이 그려지고 나머지가 흐려지는지, Esc로 해제되는지.
3. 간트에서 영역 행을 누르면 자식 작업이 펼쳐지는지.

### 5단계 — 게시한다

Artifact로 올리고 링크를 준다. **갱신할 때는 같은 파일 경로로 재게시**해 링크가 바뀌지 않게 한다. 산출물이 곧 보고이므로, 채팅에는 판정과 결정 필요 항목만 짧게 적고 설명을 HTML 밖에 늘어놓지 않는다.

## 지표를 고르는 감각

카드는 "우리가 무엇을 걱정하는가"의 목록이다. 걱정의 종류에 따라 지표를 고른다.

- 여러 팀이 같은 것을 서로 다르게 고치고 있는가 → `asset`
- 지켜야 할 선이 실제로 지켜지는가 → `check`
- 어느 영역이 막혀 뒤가 밀리는가 → `area_stalled`
- 어느 영역이 계획보다 늦는가 → `area_delay`
- 언제 끝날지 모르는 일이 남아 있는가 → `undated`
- 최근에 무엇이 실제로 나갔는가 → `status_recent`
- 만들다 보니 기획과 벌어진 곳이 쌓이는가 → `drift`

`decide: true`는 "사람이 답해야 진행되는 것"에만 붙인다. 배지는 그 카드가 실제로 위험·주의일 때만 나타나므로, 평소에는 조용하다가 걸릴 때만 눈에 띈다.

## 참고

- **스키마 정본**: [`reference/board-schema.md`](reference/board-schema.md) — config·data의 모든 항목, 지표 7종, 엔진이 계산하는 것, 검증이 막는 것.
- **번들 예시**: `assets/board.config.example.json`(HTS 어휘) · `assets/board.example.json`(작업 12건·위반 1건 표본).
- **템플릿**: `assets/board_template.html` — 시각·상호작용의 확정본. 주입 지점은 `/*__BOARD_DATA__*/null` 한 곳뿐이며, CSS/JS를 손으로 고치지 않는다.
- `/sysreport`(시스템층 통합 현황판 + 결정 큐)의 정식 종합은 이 스킬로 렌더한다.
