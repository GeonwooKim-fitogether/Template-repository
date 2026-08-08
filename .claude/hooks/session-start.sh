#!/bin/bash
# SessionStart hook — provisions the environment that bundled QA skills need.
#
# This repo is a GitHub template ("Use this template"). Every repo copied from
# it inherits this hook, so new repos get the same environment automatically.
#
# Job: install the Python `playwright` package that the `webapp-testing` skill
# uses. The managed web environment ships Chromium browser binaries in
# /opt/pw-browsers but NOT the pip package, and the package version must match
# the bundled Chromium build or the default launch() fails.
set -euo pipefail

# Only run in the remote (Claude Code on the web) environment. Locally, leave
# the user's own Python setup untouched.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Skip if there's no managed browser bundle (nothing to match against).
if [ ! -d /opt/pw-browsers ]; then
  echo "[session-start] /opt/pw-browsers not found; skipping playwright setup."
  exit 0
fi

# Pin the playwright version that matches the bundled Chromium build.
# Default 1.56.0 == Chromium build 1194 (this environment).
PLAYWRIGHT_VERSION="1.56.0"

# If a different Chromium build is present, surface it so the pin can be updated.
DETECTED_BUILD="$(ls -d /opt/pw-browsers/chromium-* 2>/dev/null | grep -oE '[0-9]+$' | head -1 || true)"
if [ -n "$DETECTED_BUILD" ] && [ "$DETECTED_BUILD" != "1194" ]; then
  echo "[session-start] WARNING: Chromium build $DETECTED_BUILD detected, but the"
  echo "[session-start]          hook pins playwright==$PLAYWRIGHT_VERSION (build 1194)."
  echo "[session-start]          If webapp-testing fails to launch, update PLAYWRIGHT_VERSION"
  echo "[session-start]          in .claude/hooks/session-start.sh to the matching version."
fi

# Idempotent: pip is a no-op if the exact version is already satisfied.
echo "[session-start] Installing playwright==$PLAYWRIGHT_VERSION (Python package)..."
pip install --quiet "playwright==$PLAYWRIGHT_VERSION"

echo "[session-start] Done. webapp-testing skill is ready."
