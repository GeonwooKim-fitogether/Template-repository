---
name: new-project
description: 현재 프로젝트(repo)에 FITogether 공용 스킬 모음(fitogether-tools 마켓플레이스)을 한 번에 연결한다. 사용자가 "새 프로젝트 세팅", "이 repo에 스킬 추가", "fitogether 스킬 깔아줘", "스킬 세팅", "/new-project" 라고 하면 이 스킬을 사용한다. .claude/settings.json 을 생성/병합해서 마켓플레이스를 등록하고 모든 공용 스킬을 활성화한 뒤, 원하면 커밋까지 한다.
label_ko: 새 프로젝트 세팅
summary_ko: 현재 repo에 .claude/settings.json을 만들어 FITogether 공용 스킬 전부를 한 번에 연결합니다 (커밋까지).
---

# 새 프로젝트 세팅 (new-project)

현재 작업 중인 repo에 **FITogether 공용 스킬 모음**을 연결한다.
이 스킬을 실행하면 `.claude/settings.json`에 마켓플레이스를 등록하고, 모든 공용 스킬을 활성화한다.
그 repo를 여는 누구나(웹/클라우드 포함) 별도 설치 없이 같은 스킬을 쓰게 된다.

## 동작 원리 (요약)

Claude Code는 세션을 열 때 그 프로젝트의 `.claude/settings.json`을 읽는다.
거기에 `extraKnownMarketplaces`와 `enabledPlugins`가 적혀 있으면, 로컬 설치 없이도
GitHub의 `geonwookim-fitogether/fitogether-claude-tools` 마켓플레이스에서 스킬을 가져와 활성화한다.
이 스킬은 그 파일을 자동으로 만들어 주는 것이다.

## 워크플로

### 1단계: 최신 스킬 목록 가져오기
GitHub에서 현재 등록된 스킬 목록을 읽어, 항상 최신 상태로 활성화한다.

```bash
curl -sSL https://raw.githubusercontent.com/geonwookim-fitogether/fitogether-claude-tools/main/.claude-plugin/marketplace.json
```

이 JSON의 `plugins[].name` 들이 활성화할 스킬 목록이다.
(curl을 못 쓰는 환경이면 WebFetch로 같은 URL을 읽는다.)

### 2단계: 사용자에게 범위 확인
- 기본: **모든 공용 스킬**을 활성화
- 사용자가 특정 스킬만 원하면 그 목록만 활성화한다.
- `new-project` 자기 자신은 활성화 목록에서 제외한다.

### 3단계: `.claude/settings.json` 생성 또는 병합
- 파일이 없으면 새로 만든다.
- 이미 있으면 **기존 내용을 보존**하고 `extraKnownMarketplaces`와 `enabledPlugins`만 병합한다.
  (기존 키를 덮어쓰지 말 것 — 외과적으로 추가만 한다.)

생성할 형태(예시 — 스킬 목록은 1단계에서 읽은 실제 목록으로 채운다):

```json
{
  "extraKnownMarketplaces": {
    "fitogether-tools": {
      "source": { "source": "github", "repo": "geonwookim-fitogether/fitogether-claude-tools" }
    }
  },
  "enabledPlugins": {
    "andrepathy@fitogether-tools": true,
    "claude-video@fitogether-tools": true,
    "superpower@fitogether-tools": true,
    "understand@fitogether-tools": true,
    "agent-memory@fitogether-tools": true,
    "skill-creator@fitogether-tools": true,
    "remotion@fitogether-tools": true,
    "frontend-design@fitogether-tools": true,
    "humanizer@fitogether-tools": true,
    "find-skill@fitogether-tools": true,
    "fitogether-user-guide@fitogether-tools": true
  }
}
```

### 4단계: 결과 안내 및 커밋
- 어떤 스킬이 활성화됐는지 사용자에게 표로 보여준다.
- 사용자에게 물어본 뒤(또는 명시적으로 요청했으면 바로) 커밋한다:
  ```bash
  git add .claude/settings.json
  git commit -m "Enable fitogether-tools skills"
  ```
- 푸시는 사용자가 요청할 때만 한다.
- Claude Code를 재시작하거나 세션을 새로 열면 스킬이 로드된다고 안내한다.

## 주의

- 이 스킬이 동작하려면 **현재 세션에서 이미 `fitogether-tools`가 인식돼 있어야 한다**
  (전역 `~/.claude/settings.json`에 등록돼 있거나, 이 repo에 이미 등록됨).
  완전히 깨끗한 환경에서는 마켓플레이스를 먼저 한 번 등록해야 한다:
  `/plugin marketplace add geonwookim-fitogether/fitogether-claude-tools`
- `.claude/settings.json`은 그 repo의 모든 사용자에게 공유되므로, 팀 공용으로 적합한 스킬만 활성화한다.
