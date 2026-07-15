# FITogether Claude Tools 🛠️

FITogether 팀의 **Claude Code 공용 자산 창고 + 새 프로젝트 템플릿**입니다.
"공용 자산"은 스킬·규칙·에이전트 세 가지를 말합니다. 이 repo 하나가 아래 네 가지 역할을 합니다:

1. **스킬 창고** — 모든 공용 스킬이 `.claude/skills/` 에 들어있습니다. 스킬은 여기서만 편집합니다.
2. **공용 규칙 창고** — 모든 프로젝트가 함께 지켜야 하는 규칙(예: 채팅·문서 어투 규칙)이 `.claude/rules/` 에 들어있습니다. 규칙도 여기서만 편집합니다. `.claude/rules/*.md` 는 세션 시작 시 Claude Code가 **자동으로 읽습니다**(CLAUDE.md와 같은 우선순위). 그래서 파일만 내려가면 별도 설정 없이 바로 적용됩니다.
3. **공용 에이전트 창고** — 모든 프로젝트에서 불러 쓰는 서브에이전트가 `.claude/agents/` 에 들어있습니다. 예를 들어 `doc-clarifier` 는 안 읽히는 마크다운 문서를 구조적·논리적·시각적으로 다시 써 주는 편집자 에이전트입니다. `.claude/agents/*.md` 는 서브에이전트로 **자동 등록**되므로, 파일만 내려가면 바로 부를 수 있습니다.
4. **프로젝트 템플릿** — 이 repo에서 **"Use this template"** 으로 새 프로젝트를 시작하면,
   스킬·규칙·에이전트가 그대로 따라가 **클라우드·로컬 어디서든 자동 로드**됩니다.

> 💡 Claude Code 웹/클라우드에는 플러그인·마켓플레이스 기능이 없습니다. 그래서 스킬을
> **파일 자체로 repo에 넣는(vendor)** 이 방식이 클라우드·로컬 모두에서 동작하는 정공법입니다.

---

## 🚀 새 프로젝트 시작하기

1. 이 repo에서 초록색 **`Use this template`** ▸ **`Create a new repository`** 클릭
2. 새 repo를 Claude Code(웹·데스크톱·터미널)로 열기
3. 끝. 세션 시작 시 세 가지가 모두 자동으로 붙습니다.
   - **스킬**: `/` 를 눌러 `humanizer`, `superpower` 등이 보이면 성공.
   - **규칙**: `.claude/rules/*.md` 가 세션 시작 시 자동 로드됩니다(예: 채팅·문서 어투 규칙).
   - **에이전트**: `.claude/agents/*.md` 가 서브에이전트로 자동 등록됩니다(예: `doc-clarifier`).

> 로컬에서 쓸 거면 만든 repo를 `git clone` 하면 됩니다. `.claude/skills/`·`.claude/rules/`·`.claude/agents/`
> 가 그대로 따라오니 로컬 Claude Code에서도 똑같이 자동 로드됩니다. 별도 설치·명령어 없음.

---

## 📚 포함된 스킬

| 스킬 | 무엇을 해주나요 |
|------|----------------|
| `agent-memory` | 세션 작업을 로컬에 저장하고 다음 세션에서 필요한 맥락만 복원 |
| `andrepathy` | AI의 흔한 코딩 실수 4가지를 막는 코딩 규칙 |
| `claude-video` | 영상을 빠르게 분석·요약·질의응답 (채팅, 파일 없음) |
| `claude-video-learning` | 영상을 **교육자료**로 — 영상별 폴더에 가로 PDF + 인터랙티브 HTML, 핵심 도식을 벡터(SVG)로 재구성 |
| `drbfm-qa` | 개정 전/후 스키매틱을 비교해 변경점을 도출하고 FITogether 표준 양식(개선 내용 정의 + As Is/To Be 회로도 + CheckList 11항목 자동 점검)의 DRBFM-QA HTML 생성 |
| `find-skill` | 목적에 맞는 스킬을 카탈로그에서 찾아줌 |
| `firmware-map` | 펌웨어/임베디드 C 코드베이스를 인터랙티브 HTML로 시각화 |
| `frontend-design` | 'AI 슬롭' 디자인을 막고 세련된 UI 결과물 유도 |
| `hardware-map` | 회로도(스키매틱) PDF를 기능 블록·버스 관계도 + 블록 상세 + 회로도·전 부품 역할표를 담은 인터랙티브 HTML로 생성 (DRBFM 회로 리뷰·비전문가 이해용) |
| `humanizer` | AI 문체를 제거하고 자연스러운 사람 말투로 재작성 |
| `qa-swarm` | 이해관계자 페르소나(L1·L2)를 subagent로 띄워 앱을 직접 써보게 하며 놓친 엣지·막힘·다자 마찰을 발견하는 QA 하네스 |
| `remotion` | React 기반 영상 제작의 타이밍·싱크 오류 교정 |
| `skill-creator` | 새 스킬을 코드·테스트·패키징까지 자동 생성 |
| `superpower` | 스펙→계획→테스트를 강제하는 시니어 개발 워크플로 |
| `understand` | 코드베이스 의존성 지식 그래프 생성 및 시각화 |
| `webapp-testing` | 로컬 웹앱을 Playwright로 구동·테스트·스크린샷·로그 확인 |
| `workflow-designer` | 업무·시스템 흐름을 점검하고 Mermaid 플로차트로 그려 아티팩트로 보여줌 |

---

## 📦 포함된 규칙·에이전트

스킬 외에 공용 규칙과 에이전트도 함께 배포됩니다.

| 종류 | 이름 | 무엇을 해주나요 |
|------|------|----------------|
| 규칙 | `communication.md` | 채팅·문서를 압축된 기호 대신 한 번에 읽히는 문장으로 쓰게 하는 어투 규칙. 세션 시작 시 자동 로드 |
| 에이전트 | `doc-clarifier` | 안 읽히는 마크다운을 구조적·논리적·시각적으로 다시 써 주는 편집자. "이 문서 정리해 줘"로 호출 |

---

## 🔄 스킬 추가 / 수정 / 삭제 (관리자용)

스킬은 **이 repo의 `.claude/skills/` 에서만** 관리합니다.

- **수정**: `.claude/skills/<스킬>/SKILL.md` 를 고치고 커밋.
- **추가**: `.claude/skills/<새스킬>/SKILL.md` 를 만들고 커밋.
- **삭제**: 해당 폴더를 지우고 커밋.

### 하위 프로젝트는 어떻게 최신이 되나 (수동 포인트 0)
이 템플릿에는 `.github/workflows/sync-skills.yml`(자가 동기화 봇)이 들어있습니다.
**"Use this template"로 만든 모든 repo가 이 봇을 함께 물려받아**, 매주 이 창고의
`.claude/skills/` · `.claude/rules/` · `.claude/agents/` 를 자기 repo로 다시 받아옵니다.
즉 창고만 고치면 하위 프로젝트들이 알아서 따라옵니다. (즉시 반영이 필요하면 그 repo의 Actions에서 워크플로를 수동 실행)

## 📏 공용 규칙 (관리자용)

규칙도 스킬과 똑같이 **이 repo의 `.claude/rules/` 에서만** 관리합니다.

- **수정/추가**: `.claude/rules/<규칙>.md` 를 고치거나 새로 만들고 커밋.
- 파일 하나가 한 주제를 담습니다(예: `communication.md` = 채팅·문서 어투 규칙).
- 위 동기화 봇이 `.claude/rules/` 도 함께 내려 주므로, 하위 프로젝트는 손댈 것이 없습니다.
- 규칙 파일은 세션 시작 시 자동 로드되므로, `CLAUDE.md`에 `@`로 불러오는 줄을 넣지 않아도 됩니다.

## 🤖 공용 에이전트 (관리자용)

서브에이전트도 **이 repo의 `.claude/agents/` 에서만** 관리합니다.

- **수정/추가**: `.claude/agents/<이름>.md` 를 고치거나 새로 만들고 커밋. 파일 맨 위 frontmatter(`name`·`description`·`tools`)로 언제 불릴지와 쓸 도구를 정합니다.
- 예: `doc-clarifier` — 사용자가 "이 문서 이해가 안 된다 / 정리해 줘"라고 할 때 불러, 안 읽히는 마크다운을 다시 써 주는 편집자.
- 위 동기화 봇이 `.claude/agents/` 도 함께 내려 주므로, 하위 프로젝트는 손댈 것이 없습니다. 에이전트 파일은 서브에이전트로 자동 등록되어 바로 부를 수 있습니다.

---

## 🧩 기존 repo에 스킬 넣기

템플릿에서 시작하지 않은 기존 repo라면, 이 repo의 `.claude/skills/`·`.claude/rules/`·`.claude/agents/` 폴더와
`.github/workflows/sync-skills.yml` 을 복사해 커밋하면 동일하게 동작합니다.
(Claude Code 세션이면 "fitogether-claude-tools의 .claude/skills·rules·agents를 이 repo에 복사해줘" 라고 시키면 됩니다.)

---

## 📌 참고: fitogether-user-guide 스킬

제품 유저가이드 PDF 생성 스킬(`fitogether-user-guide`)은 폰트 등 약 9MB라 모든 프로젝트에
따라붙지 않도록 이 템플릿에서 제외했습니다. 필요하면 이 repo의 git 히스토리(마켓플레이스 구조 시절)
에서 가져오거나 별도 repo로 분리해 쓰세요.
