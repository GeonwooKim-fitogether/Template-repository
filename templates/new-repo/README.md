# 새 프로젝트 (FITogether 스킬 자동 적용)

이 폴더는 **새 프로젝트 repo의 시드(seed)** 입니다.
여기 들어있는 `.claude/settings.json` 한 개가 [fitogether-claude-tools](https://github.com/geonwookim-fitogether/fitogether-claude-tools)
마켓플레이스를 가리키고 있어서, 이 repo를 여는 모든 Claude Code 세션(웹/클라우드 포함)이
**세션 시작 시 최신 스킬을 자동으로 불러옵니다.** 로컬 설치도, 명령어도 필요 없습니다.

## 이 시드는 어떻게 쓰나

- **전용 템플릿 repo로 사용**: 이 폴더 내용을 템플릿 repo에 넣고 "Template repository"로 표시한 뒤,
  새 프로젝트를 만들 때 GitHub에서 **"Use this template"** 으로 시작하면 끝입니다.
- **기존 repo에 적용**: 이 폴더의 `.claude/` 를 그 repo 루트에 복사해 커밋하면 됩니다.

## 손댈 필요 없음 (수동 포인트 0)

`.claude/settings.json`은 [generate_docs.py](https://github.com/geonwookim-fitogether/fitogether-claude-tools/blob/main/scripts/generate_docs.py)가
마켓플레이스를 읽어 **자동 생성**합니다. 스킬이 추가/삭제되면 GitHub Actions가 이 파일을 다시 만들어 커밋하므로,
목록을 사람이 직접 고칠 일이 없습니다. 스킬 *내용* 수정은 마켓플레이스에서만 하면 모든 프로젝트에 자동 반영됩니다.

> 이 파일과 `.claude/settings.json`은 자동 생성/배포됩니다. 직접 수정하지 마세요.
