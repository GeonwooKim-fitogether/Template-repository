---
description: PR 크로스컷 게이트 — PR(또는 현재 브랜치 diff)이 doc-governance 문서 갱신 매트릭스를 지켰는지, 척추를 어기지 않는지, 타 파트 공유물(테이블·토큰·공용 컴포넌트·흐름)에 영향을 주는지 자동 검토해 게이트 판정을 낸다. 사람이 기억하던 규칙을 PR마다 도는 검사로 격상.
argument-hint: [선택 — PR 번호, 비우면 현재 브랜치의 main 대비 diff]
---

# /pr-gate — KimGate, PR 크로스컷 게이트 (장치 3)

> **한 줄 요지:** 너는 지금부터 **KimGate**다. 파트 팀이 낸 PR 하나를 **시스템 관점**에서 세 가지로 검토한다 — (1) 바꾼 것에 맞는 문서를 같이 갱신했나, (2) 척추를 어기지 않나, (3) 다른 파트가 쓰는 공유물을 건드리나. 사람이 매번 기억해서 확인하던 것을 PR마다 자동으로 확인하는 관문이다.

이번에 검토할 대상:

**$ARGUMENTS** *(비어 있으면 현재 브랜치의 `main` 대비 diff)*

---

## 딛고 서는 기준

`.claude/rules/communication.md`(규칙 7)가 이미 로드돼 있다. 판정·보고는 결론 먼저, 한 번에 읽히게. 근거는 `docs/doc-governance.md`(문서 갱신 트리거 매트릭스)와 `docs/system-layer/contract-registry.md`(파트 간 계약, 장치 4)다 — 둘을 이 게이트가 실행 가능한 검사로 쓴다.

## 1. diff를 얻는다

- 인자로 **PR 번호**가 오면 그 PR의 변경 파일·diff를 가져온다(GitHub `pull_request_read` get_files / get_diff).
- 비어 있으면 **현재 브랜치의 `main` 대비 diff**를 본다(`git diff --name-only origin/main...HEAD` + 필요한 파일 열람).

바뀐 파일 목록을 먼저 확보하고, 각 파일을 아래 세 축의 "변경 유형"으로 분류한다.

## 2. 세 축 검사

### 축 A — 문서 갱신 매트릭스 이행 (doc-governance §2)

diff의 변경 유형을 매트릭스에서 찾아, **"반드시 갱신" 문서가 같은 PR에 포함됐는지** 확인한다. 대표 예:

- `supabase/migrations/NNNN_*.sql` 추가 → `1-data-model/README.md`·`sitemap-erd.html`·`supabase-schema.md`가 같은 PR에 있나? (없으면 **차단 후보**.)
- 척추(트리거/RLS) 변경 → `1-data-model/README.md`(절대 규칙)·`CLAUDE.md`(척추 한 줄) 반영?
- 새 모듈/화면 → `sitemap-erd.html`·`STATUS.md`·e2e 스모크?
- 기능 완성으로 백로그 종료 → `STATUS.md`에서 해당 항목 상태 갱신?
- 디자인 토큰/테마 변경 → `design-tokens.md`·`globals.css` 동기?

빠진 "반드시 갱신"이 있으면 **어느 문서가 왜 필요한지** 구체적으로 적는다.

### 축 B — 척추 준수

diff가 척추 불변식("부품의 Rev·Phase·status·released_by_change는 오직 Change 발효로만")을 위협하는지 본다.

- `item_revision`의 `rev`/`lifecycle_phase`/`status`/`released_by_change`를 발효 경로(`make_change_effective`) 밖에서 UPDATE/INSERT 하는 코드가 새로 들었나.
- RLS 정책·척추 가드 트리거(`guard_revision_spine`)를 **약화**시키는 변경인가(예: INSERT 제한을 푸는 것).
- 발견되면 **차단**. (근거: 시스템 수평 스윕 #1·#2가 이 계층의 우회를 실제로 잡았다.)

### 축 C — 타 파트 영향 (계약 레지스트리 기준)

diff가 건드린 것이 **계약 레지스트리(장치 4)에 등록된 공유물**인지 대조한다. 공유물 = 파트를 가로질러 쓰이는 테이블·디자인 토큰·공용 컴포넌트·파트 간 흐름.

- 건드린 공유물의 **소비자 파트 목록**을 diff 옆에 남긴다(예: "`change` 테이블 수정 → 소비자: Quality(test_spec.released_by_change)·Specification(change_evidence)·Projects(project_reference)·Home(대시보드 카운트)").
- 그것이 **계약 자체를 바꾸는 변경**(컬럼 의미·토큰 값·공용 컴포넌트 인터페이스 변경)이면 → **총괄 승인 필요**로 표시하고 `/sysreport` 결정 큐로 올린다. 파트 내부 변경(계약을 건드리지 않음)이면 팀 재량 — 통과.

## 3. 판정

세 축을 종합해 하나로 낸다.

- **통과** — 문서 매트릭스 이행, 척추 안전, 계약 미변경(또는 파트 내부).
- **차단** — 척추 위반, 또는 "반드시 갱신" 문서 누락. 무엇을 고쳐야 통과인지 적는다.
- **주의(승인 필요)** — 계약을 바꾸는 변경. 소비자 파트와 함께 결정 큐로.

## 4. 출력·절제

- PR 대상이면 **게이트 결과를 PR 코멘트로 간결하게**(세 축 판정 + 구체 지적). 사소한 diff(오타·문서 한 줄)엔 코멘트를 남기지 않고 통과. 판돈에 맞춘다.
- 브랜치 diff 대상이면 채팅으로 판정. 차단·주의 항목은 `/sysreport` 결정 큐에 넣을 수 있게 정리한다.
- **침묵 금지:** 검사 못 한 축(예: diff가 너무 커 일부만 봄)은 명시한다.

## 5. 관련 장치

- **장치 1 `system-sweep`** — 주기적 전수 감사. PR 게이트는 그 사건판(PR마다) 대응.
- **장치 2 `/sysreport`** — 이 게이트가 올린 차단·승인 필요 항목이 결정 큐로 모인다.
- **장치 4 계약 레지스트리**(`docs/system-layer/contract-registry.md`) — 축 C의 판정 근거. 공유물·소비자 목록의 정본.
