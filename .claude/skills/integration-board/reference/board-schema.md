# integration-board · config·data 스키마 정본

> **한 줄 요지:** 통합 현황판은 **세 겹**으로 나뉜다. 화면을 그리는 **엔진**은 창고에 고정돼 있고, 프로젝트의 어휘와 관심사는 **config**에, 이번 회차의 사실만 **data**에 담긴다. 화면에 나오는 숫자와 판정 문장은 사람이 쓰지 않고 **엔진이 계산한다.**

이 문서는 `assets/integration_board_engine.py`가 읽는 두 JSON 파일의 규격이다. 엔진은 여기 적힌 규격을 어기는 입력을 **거부하고 아무 것도 만들지 않는다**(종료 코드 2).

---

## 0. 세 겹이 각각 무엇을 담나

| 겹 | 사는 곳 | 누가 소유 | 무엇이 들어가나 | 얼마나 자주 바뀌나 |
|---|---|---|---|---|
| 엔진 | 창고 `.claude/skills/integration-board/assets/` | 창고(공통) | 레이아웃, 색, 상호작용, 계산 규칙, 문장 문법 | 거의 안 바뀜 |
| config | 프로젝트 `.integration/board.config.json` | 그 프로젝트 | 팀·제품 영역·공용 자산·자동 검사의 **이름과 설명**, 무엇을 지켜볼지(카드) | 분기에 한 번 정도 |
| data | 프로젝트 `.integration/board.json` | 매 실행 | 작업 목록, 상태, 날짜, 위반 — **사실만** | 실행할 때마다 |

이 구분의 목적은 하나다. **누군가 매번 보고서를 새로 쓰는 것을 막는 것.** 설명 문장은 config에 한 번 적어 두고 계속 재사용하며, data에는 자유 서술 필드가 아예 없다. 그래서 두 번 실행하면 판이 똑같고, 달라지는 것은 숫자뿐이다.

---

## 1. config — 프로젝트가 소유하는 어휘

최상위에 쓸 수 있는 항목은 아래가 전부다. 다른 이름을 넣으면 "스키마에 없는 항목입니다"로 실패한다.

```
필수:  board · lanes · statuses · areas · cards
선택:  bands · verdicts · assets · checks · drift · honesty · axis · text
```

### 1.1 board — 보드의 이름표 (필수)

```json
"board": {
  "title":    "통합 현황판",
  "eyebrow":  "HTS · Integration Board",
  "subtitle": "여러 팀의 일이 하나의 제품으로 맞물리는지 보는 한 장",
  "docTitle": "통합 현황판 — Integration Board · HTS"
}
```

`title`만 필수다. `docTitle`은 브라우저 탭에 뜨는 이름이며, 없으면 `title`을 쓴다.

### 1.2 lanes — 관심사 열 (필수, 1개 이상)

밴드 1(종합 판정)에서 카드를 묶는 세로 열이다. 화면에는 선언한 순서대로 놓인다.

```json
"lanes": [ { "key": "delivery", "label": "진척", "en": "Delivery" } ]
```

`key`는 id, `label`은 화면에 크게 나오는 이름, `en`(선택)은 그 옆에 작게 붙는 영문이다.

### 1.3 statuses — 칸반 열 (필수, 1개 이상)

작업이 놓일 수 있는 상태다. 칸반의 열이자 색 범례의 항목이 된다.

```json
"statuses": [
  { "key": "review", "label": "검토대기", "tone": "amber",
    "mean": "반영 요청(PR)이 열려 사람의 승인을 기다리는 중" }
]
```

- `tone`은 **정본 토큰 이름 중에서만** 고른다: `red` · `amber` · `green` · `blue` · `teal` · `dim` · `muted` · `neutral`. 색상 코드(`#ff00ff`)를 직접 쓰면 거부된다. 새 색을 지어내지 못하게 막는 장치다.
- `mean`(선택)은 열 아래 한 줄로 붙는 "이 상태가 무슨 뜻인가" 설명이다.

### 1.4 areas — 제품 영역 (필수, 1개 이상)

작업이 속한 제품의 구획이다. 간트의 부모 행(롤업 행)이 된다.

```json
"areas": [ { "key": "items", "label": "부품", "en": "Items" } ]
```

### 1.5 assets — 공용 자산 (선택)

여러 팀이 같이 쓰는 것(디자인 토큰, 공용 데이터 계약 등). 하나도 선언하지 않으면 그 구획은 화면에서 사라진다.

```json
"assets": [
  { "key": "token", "label": "디자인 토큰",
    "plain": "화면의 색·글꼴·간격을 정해 둔 공용 규칙 값",
    "why": "팀마다 제각각 고치면 한 제품인데 화면이 서로 다른 제품처럼 보인다" }
]
```

`plain`은 "뜻"(이게 무엇인가)이고 `why`(선택)는 "걸리면"(어긋나면 무슨 일이 생기나)이다. 이 두 문장이 화면에 그대로 나온다.

### 1.6 checks — 자동 검사 (선택)

지켜야 할 선을 기계가 대신 확인하는 검사다. 밴드 3의 열이 된다.

```json
"checks": [
  { "key": "spine", "name": "개정 통제 원칙",
    "plain": "부품의 개정(Rev)·단계(Phase)는 오직 설계변경 승인으로만 바뀐다",
    "why": "우회하면 이력 없이 부품이 바뀌어 추적이 통째로 무너진다" }
]
```

**검사의 통과/위반 여부는 여기에 쓰지 않는다.** 그것은 data의 `violations`에서 나오며, 엔진이 계산한다(1.11 참고).

### 1.7 cards — 밴드 1에서 무엇을 지켜볼 것인가 (필수, 1개 이상)

가장 중요한 절이다. 카드는 "이 프로젝트가 상시로 지켜보는 관심사"이며, **그 카드에 뜨는 숫자와 심각도는 config가 아니라 엔진이 매 실행 계산한다.**

```json
{ "key": "ov-token", "lane": "cohesion", "title": "디자인 토큰",
  "plain": "화면의 색·글꼴·간격을 정해 둔 공용 규칙 값",
  "why": "먼저 정하지 않고 각자 반영하면 화면이 팀마다 달라진다",
  "metric": { "kind": "asset", "asset": "token" },
  "decide": true,
  "traceChecks": ["lint"] }
```

- `lane` — 어느 관심사 열에 놓을지. `lanes`에 없는 값이면 거부된다.
- `metric` — **무엇을 세어 이 카드의 문장을 만들지**(아래 표).
- `decide` — "사람이 정해 주기 전에는 진행할 수 없는 것"인지. `true`라도 배지는 **그 카드가 실제로 위험·주의일 때만** 붙는다. 늘 붙어 있으면 신호가 죽기 때문이다.
- `traceChecks` — 카드를 눌렀을 때 함께 밝힐 자동 검사. 작업·공용 자산 쪽 연결은 지표에서 자동으로 나오므로 적을 필요가 없다.

한 열에 카드가 4개 이상이면 급한 순(위험 → 주의 → 정상 → 참고)으로 3장만 펼치고 나머지는 "그 외 n건"으로 접는다. 같은 급끼리는 선언한 순서를 지킨다.

#### 지표 종류(metric.kind) — 7가지가 전부다

| kind | 묶이는 대상 | 엔진이 세는 것 | 나오는 문장(예) | 심각도 판정 |
|---|---|---|---|---|
| `asset` | `asset` | 이 자산을 건드린 팀 수, 그중 충돌·대기 팀 수 | "5팀 중 **3팀**이 서로 다르게 고쳤다" | 충돌 있으면 위험, 대기만 있으면 주의, 없으면 정상 |
| `check` | `check` | 이 검사의 위반 건수, 전체 검사 중 통과 수 | "위반 후보 **1건** · 자동 검사 6개 중 **5개** 통과" | 위반 있으면 주의, 없으면 정상 |
| `area_stalled` | `area` | 이 영역에서 가장 오래 멈춘 작업의 `stalledDays` | "검토대기가 **5일**째 움직이지 않는다" | 14일 이상 위험, 1일 이상 주의 |
| `area_delay` | `area` | 예상 종료가 계획을 넘긴 작업 수와 가장 큰 초과 일수 | "**1건**이 계획보다 **16일** 늦다" | 30일 이상 위험, 1일 이상 주의 |
| `undated` | (없음) | 계획 날짜가 없어 시간 축에 못 올린 작업 수 | "**2건**이 아직 시간 축에 올라가지 못했다" | 1건 이상 주의 |
| `status_recent` | `status` | 최근 7일 안에 그 상태로 끝난 작업 수 | "이번 주 배포완료 **1건**" | 항상 참고(좋은 소식은 경보가 아니다) |
| `drift` | (없음) | data의 `drift.gaps` / `drift.pivots` | "기획 이탈 **2건** 누적 · 기획 전환 후보 **1건**" | 항상 참고 |

경계값(14일 · 30일 · 7일 · 3장)은 엔진 상수다. 데이터가 바꿀 수 없고, 바꾸려면 엔진을 고쳐야 한다. 판정 기준이 프로젝트마다 흔들리지 않게 하려는 의도다.

**문장의 문법은 엔진이 고정한다.** config가 정하는 것은 그 안에 들어가는 이름(제품 영역 · 상태 · 공용 자산 · 기획 용어)뿐이다. 그래서 카드에 자유 서술을 넣을 자리가 없다.

### 1.8 bands — 세 밴드의 이름 (선택)

`overview` · `delivery` · `quality` 세 개만 쓸 수 있고, 각각 `n`(번호표) · `title` · `en` · `caption`을 덮어쓸 수 있다. 적지 않으면 "밴드 1 / 종합 판정 / Executive Overview / 지금 무엇을 결정해야 하나" 같은 기본값이 쓰인다.

### 1.9 verdicts — 종합 판정의 말 (선택)

```json
"verdicts": { "risk": { "word": "위험", "why": "공용 자산 충돌이 풀리지 않았다 — 해소 전에는 본선 반영을 멈춘다" } }
```

`risk` · `warn` · `ok` 세 가지에 각각 `word`(크게 나오는 한 단어)와 `why`(그 아래 한 줄)를 정할 수 있다. **색은 의미색이라 엔진이 고정한다**(위험은 빨강, 주의는 주황, 정상은 초록).

판정 자체는 다음 규칙으로 엔진이 정한다.

1. 카드 중 하나라도 **위험**이거나, 자동 검사 중 하나라도 **막힘(block) 위반**이 있으면 → 위험.
2. 그렇지 않고 카드 중 **주의**가 있으면 → 주의.
3. 둘 다 없으면 → 정상.

### 1.10 drift — 기획 정합성 막대 (선택)

```json
"drift": { "gapLabel": "기획 이탈", "pivotLabel": "기획 전환 후보",
           "note": "만들다 보니 원래 기획과 어긋난 곳 — 기획을 고칠지 사람이 정하는 입구",
           "linkLabel": "기획 정합성 상세 보드", "href": "#" }
```

`gapLabel`과 `pivotLabel`은 필수다. data에 `drift`가 있는데 config에 이 절이 없으면(또는 그 반대면) 엔진이 거부한다.

### 1.11 honesty — 이 보드가 못 보는 것 (선택)

보드 맨 아래 한 문단. 초록불이 곧 좋은 제품을 뜻하지 않는다는 식의 한계 고백을 적는다. 비워 두면 그 줄이 사라진다.

### 1.12 axis — 시간 축의 기하 (선택)

```json
"axis": { "leadDays": 14, "days": 84, "tickDays": 7 }
```

`leadDays`는 오늘 기준으로 축을 며칠 앞에서 시작할지, `days`는 축 전체 길이, `tickDays`는 눈금 간격이다. 축 시작일은 **오늘에서 계산**되므로 손으로 적지 않는다.

### 1.13 text — 화면 문구 덮어쓰기 (선택)

버튼·라벨·안내문 같은 고정 문구 54개에 전부 기본값이 있어, 이 절이 없어도 보드는 그대로 동작한다. 프로젝트 어휘에 맞추고 싶을 때만 덮어쓴다. 목록에 없는 키를 쓰면 거부된다.

`metaPrefix` `metaSuffix` `metaNote` `themeLight` `themeDark` `legendTitle` `legendConflict` `legendWaiting` `legendTrace` `band1Hint` `verdictKicker` `decideCount` `decideHint` `decideBadge` `countUnit` `laneOk` `laneMore` `meanLabel` `whyLabel` `viewSwitchLabel` `viewNote` `tabKanban` `tabKanbanEn` `tabGantt` `tabGanttEn` `assetsTitle` `blockConflict` `blockWaiting` `ganttAxisLabel` `ganttEmptyArea` `ganttDelayTip` `ganttLegPlan` `ganttLegFill` `ganttLegDelay` `ganttLegDep` `ganttLegToday` `ganttLegDue` `ganttLegHint` `undatedGroup` `undatedSuffix` `undatedRow` `checkPass` `checkWarn` `checkBlock` `vioBlock` `vioWarn` `okNone` `traceChip` `traceOff` `checksLabel` `assetBadgeConflict` `assetBadgeWaiting` `assetBadgeOk` `recentPrefix`

`laneMore` · `undatedSuffix` · `assetBadgeConflict` · `assetBadgeWaiting`에는 `{n}` `{all}` 자리표시자가 들어간다(예: `"그 외 {n}건"`). 나머지는 그대로 출력된다.

---

## 2. data — 이번 회차의 사실

```
필수:  today · works
선택:  updated · target · violations · drift
```

### 2.1 머리

```json
"today": "2026-07-26",
"updated": "2026-07-26 14:30",
"target": { "date": "2026-09-04" }
```

`today`는 오늘선이 서는 자리이자 시간 축의 기준이다. `target`(선택)은 목표일 파선이다. 목표일의 이름은 config의 문구에서 온다.

### 2.2 works — 작업 목록 (필수, 1개 이상)

```json
{ "id": "PR105-A", "title": "디자인 토큰 --teal 조정",
  "area": "items", "team": "팀 A", "status": "review",
  "block": "conflict", "touches": "token",
  "planStart": "2026-07-13", "planEnd": "2026-07-27",
  "progress": 90, "eta": "2026-08-12",
  "deps": ["PR100-D"], "stalledDays": 5, "drift": true }
```

| 항목 | 필수 | 뜻과 규칙 |
|---|---|---|
| `id` | 필수 | 작업의 고유 id. 중복되면 거부된다. |
| `title` | 필수 | 작업 이름. 화면에 그대로 나오는 유일한 자유 문자열이다(설명이 아니라 **이름**이므로 허용). |
| `area` | 필수 | config의 `areas`에 있는 key여야 한다. |
| `team` | 필수 | 팀 이름. 공용 자산의 "n팀 중 m팀"을 셀 때 쓰인다. |
| `status` | 필수 | config의 `statuses`에 있는 key여야 한다. |
| `block` | 선택 | `conflict`(충돌) 또는 `waiting`(대기)만 쓸 수 있다. 막힘은 상태가 아니라 사정이므로 열이 아닌 표식으로 붙는다. |
| `touches` | 선택 | 이 작업이 건드리는 공용 자산의 key. |
| `planStart`·`planEnd` | 선택 | 계획 구간. **둘은 함께 있거나 함께 없어야 한다.** 없으면 "일정 미정" 그룹으로 간다. |
| `progress` | 선택 | 0~100 정수. 없으면 0. |
| `eta` | 선택 | 예상 종료일. `planEnd`가 있어야 쓸 수 있다. `planEnd`를 넘기면 지연 빗금이 그려진다. |
| `deps` | 선택 | 선행 작업 id 목록. 없는 id나 자기 자신을 넣으면 거부된다. |
| `stalledDays` | 선택 | 며칠째 움직이지 않았나. `area_stalled` 지표가 쓴다. |
| `drift` | 선택 | 기획과 어긋난 작업인지. `drift` 카드가 연결선을 그릴 때 쓴다. |

### 2.3 violations — 자동 검사에 걸린 것 (선택)

```json
"violations": [ { "check": "spine", "ref": "PR115", "severity": "block" } ]
```

- `check`는 config의 검사 key, `ref`는 **실제로 존재하는 작업의 id**여야 한다. 없는 것을 가리키면 거부된다.
- `severity`는 `block`(막힘) 또는 `warn`(주의)뿐이다.
- **위반을 설명하는 문장은 적지 않는다.** 화면에는 참조된 작업의 제목이 그대로 나온다. 매 실행 새로 쓰이는 설명문을 없애기 위해서다.
- 검사의 통과 여부는 여기서 도출된다. 막힘 위반이 있으면 위반, 주의 위반만 있으면 주의, 하나도 없으면 통과다.

### 2.4 drift — 기획 정합성 숫자 (선택)

```json
"drift": { "gaps": 2, "pivots": 1 }
```

---

## 3. 엔진이 계산하는 것 (사람이 쓰지 않는 것)

아래는 전부 도출값이다. data에 적을 자리가 없고, 적으려 하면 "스키마에 없는 항목"으로 거부된다.

1. **종합 판정**(위험·주의·정상)과 **결정 필요 건수**.
2. **밴드 1 카드의 문장과 심각도** — 지표 종류별 계산(1.7의 표).
3. **관심사 열의 카드 정렬**과 "그 외 n건".
4. **공용 자산별 집계** — 몇 팀이 건드렸고 그중 몇 팀이 충돌인가.
5. **칸반 열별 건수**.
6. **간트 영역 롤업** — 계획 구간은 자식의 최소~최대, 진척률은 기간 가중 평균, 예상 종료는 자식의 최댓값, 지연은 예상 종료가 계획 종료를 넘겼는지로 판정.
7. **"일정 미정" 그룹 분리** — 날짜가 없는 작업은 영역 아래에 두지 않고 따로 모은다(양쪽에 두면 같은 작업을 두 번 세게 된다).
8. **자동 검사별 위반 집계**와 통과 개수.
9. **시간 축** — 축 시작일, 눈금, 오늘선, 목표일선의 위치.
10. **연결 보기의 연결 대상** — 카드에서 작업·공용 자산·검사로 이어지는 선.

---

## 4. 검증이 막는 것

엔진은 오류를 하나 만나고 멈추지 않고 **찾을 수 있는 것을 전부 모아 한 번에** 보여 준 뒤 종료 코드 2로 끝난다. 이때 HTML은 만들어지지 않는다.

막히는 것은 다음과 같다.

1. 필수 항목 누락.
2. **스키마에 없는 여분 필드** — 산문이나 요약문을 끼워 넣으려는 시도가 여기서 막힌다.
3. 알 수 없는 값 — 상태·막힘 사유·위반 무게·지표 종류·색 이름·문구 키.
4. **없는 id 참조** — config에 없는 제품 영역·공용 자산·자동 검사·관심사 열, data에 없는 작업.
5. id 중복, 자기 자신을 선행 작업으로 지정.
6. 날짜 문제 — 형식 오류, 달력에 없는 날짜, 종료일이 시작일보다 빠른 경우, 계획 시작·종료 중 한쪽만 있는 경우.
7. 범위 문제 — 진척률이 0~100 밖, 눈금 간격이 축 길이보다 큼.
8. 짝이 안 맞는 선언 — `drift` 카드가 있는데 데이터가 없거나, 데이터가 있는데 config에 이름이 없는 경우.

오류 메시지는 "어디가(경로) · 무엇이 틀렸고 · 무엇을 쓸 수 있는지"를 함께 적는다.

```
통합 현황판 엔진 — 검증 실패 1건. 아무 것도 렌더하지 않았습니다.
  1. data.works[PR105-A].touches: 공용 자산 'tokenz'를 찾을 수 없습니다
       └ 선언된 값: contract, token
```
