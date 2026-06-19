#!/bin/bash
# FITogether Claude Skills — 전역 설치 스크립트
# 사용법: curl -sSL https://raw.githubusercontent.com/geonwookim-fitogether/fitogether-claude-tools/main/install.sh | bash

set -e

REPO="https://raw.githubusercontent.com/geonwookim-fitogether/fitogether-claude-tools/main"
SKILLS_DIR="$HOME/.claude/skills"
SKILLS=(
  andrepathy
  claude-video
  superpower
  understand
  agent-memory
  skill-creator
  remotion
  frontend-design
  humanizer
  find-skill
)

echo "🚀 FITogether Claude Skills 설치 중..."
mkdir -p "$SKILLS_DIR"

for skill in "${SKILLS[@]}"; do
  mkdir -p "$SKILLS_DIR/$skill"
  curl -sSL "$REPO/plugins/$skill/skills/$skill/SKILL.md" -o "$SKILLS_DIR/$skill/SKILL.md"
  echo "  ✅ $skill"
done

echo ""
echo "✨ 완료! ${#SKILLS[@]}개 스킬이 $SKILLS_DIR 에 설치됐습니다."
echo "   Claude Code를 재시작하면 스킬이 자동으로 로드됩니다."
