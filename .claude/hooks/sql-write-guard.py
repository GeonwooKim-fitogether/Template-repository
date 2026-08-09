#!/usr/bin/env python3
"""데이터를 바꾸는 SQL 을 사람의 허락 없이는 실행하지 못하게 막는 PreToolUse 훅.

## 왜 이 훅이 필요한가

Supabase 의 SQL 실행 도구(`execute_sql`)는 권한 목록에서 통째로 열어 두었습니다.
조회 한 번마다 확인 창이 뜨면 작업이 계속 멈추기 때문입니다. 그런데 권한 규칙은
**도구 단위로만** 걸 수 있어서, 같은 도구 안에서 `select`(조회)와 `delete`·`drop`
(삭제)을 가를 방법이 없습니다. 그 결과 데이터를 지우는 쿼리까지 묻지 않고
실행되는 상태가 됩니다.

이 훅이 그 틈을 메웁니다. 도구가 호출되기 직전에 쿼리문을 읽어, 읽기만 하는
쿼리면 그대로 통과시키고, 데이터나 구조를 바꾸는 쿼리면 차단합니다.

## 두 도구를 본다 — 하나는 가려서, 하나는 무조건

| 도구 | 하는 일 | 이 훅의 처리 |
|---|---|---|
| `execute_sql` | 조회와 쓰기가 한 도구에 섞여 있다 | 쿼리문을 읽어 **가린다.** 조회면 통과, 쓰기면 차단 |
| `apply_migration` | 데이터베이스 구조를 바꾸는 스크립트를 적용한다 | 가릴 것이 없다. **전부 쓰기**이므로 내용과 무관하게 차단 |

`apply_migration` 을 함께 보는 이유는 실제 사고에서 나왔습니다. 한 세션이 이 도구를
여섯 번 불러 라이브 데이터베이스를 바꿨는데, 그 도구는 허용 목록에도 없고 이 훅도
보지 않던 경로여서 아무 확인 없이 지나갔습니다. `execute_sql` 만 막아 두면 옆문이
열려 있는 셈입니다.

## 왜 "확인 요청"이 아니라 "차단"인가 — 이 환경에서 실측한 결과

Claude Code 의 권한 판정에는 세 가지가 있습니다. `allow`(통과) · `ask`(사람에게
확인) · `deny`(차단). 설계대로라면 이 훅은 `ask` 를 내서 확인 창을 띄우는 것이
맞습니다. 그런데 이 원격 실행 환경에서 실제로 시험해 보니 **`ask` 판정이 무시되고
쿼리가 그대로 실행됐습니다.**

시험은 존재하지 않는 표를 지우는 쿼리(`delete from __permission_probe_...`)로
했고, 결과는 다음과 같았습니다.

| 확인한 것 | 결과 |
|---|---|
| 훅이 호출되는가 | 호출된다 |
| 훅이 `ask` 를 냈을 때 | 확인 창 없이 쿼리가 실행됐다 |
| 훅이 `deny` 를 냈을 때 | 데이터베이스에 닿기 전에 차단됐다 |

그래서 이 훅은 `ask` 가 아니라 `deny` 를 냅니다. 이 환경에서 실제로 막히는
판정이 그것뿐이기 때문입니다.

## 그러면 정말 필요한 쓰기는 어떻게 실행하나 — 일회용 열쇠

무조건 막기만 하면 정당한 작업까지 못 하게 됩니다. 그래서 사람이 허락했을 때만
열리는 통로를 하나 둡니다. **열쇠 파일**입니다.

    .claude/sql-write-unlock

이 파일이 있으면 쓰기 쿼리 **한 번**이 통과하고, 통과하는 즉시 파일이 지워집니다.
한 번 쓰면 없어지는 일회용 열쇠입니다. 그래서 열쇠를 한 번 만들어 두고 그 뒤로
계속 쓰는 일이 생기지 않습니다.

이 장치가 무엇을 보장하고 무엇을 보장하지 않는지 정직하게 적습니다.

- **보장하는 것:** 쓰기 쿼리는 열쇠를 만드는 별도의 동작 없이는 절대 실행되지
  않습니다. 그 동작은 대화 기록에 그대로 남아 사용자가 눈으로 봅니다. 즉 조용히
  지나가는 쓰기가 없습니다.
- **보장하지 않는 것:** Claude 가 파일을 만들 수 있으므로, Claude 가 스스로
  열쇠를 만드는 것을 기술적으로 막지는 못합니다. 이 훅이 막는 것은 **악의**가
  아니라 **부주의**입니다. 허락받지 않은 쓰기를 실수로 흘려보내는 일을 막고,
  모든 쓰기를 사용자 눈에 보이는 명시적 단계로 만듭니다.

## 판단 기준 — 확실할 때만 통과시킨다

이 훅은 "위험한 것을 찾아내면 막는" 방식이 아니라 **"안전한 것이 확실할 때만
통과시키는"** 방식입니다. 판단이 서지 않으면 통과가 아니라 차단 쪽으로 갑니다.
빠뜨린 패턴 하나가 곧 사고가 되기 때문입니다.

통과하려면 두 조건을 **모두** 만족해야 합니다.

1. 세미콜론으로 나눈 모든 문장이 조회를 여는 단어(`select`·`with`·`explain`·
   `show`·`values`·`table`)로 시작한다.
2. 쿼리 어디에도 데이터나 구조를 바꾸는 단어가 없다.

두 번째 조건을 검사하기 전에 주석과 문자열 리터럴을 먼저 지웁니다. 문자열 안의
`'delete'` 는 실행되는 명령이 아니라 그냥 글자이므로, 지우지 않으면 멀쩡한
조회가 차단되어 버립니다.

## 오탐은 감수한다

`explain analyze select ...` 처럼 실제로는 읽기만 하는 쿼리도 차단될 수 있습니다.
`analyze` 가 위험 단어 목록에 있기 때문입니다. 이것은 의도한 절충입니다. 한 번 더
열쇠를 만들어야 하는 불편과, 데이터가 조용히 지워지는 사고 중에서 앞을 택했습니다.
"""

import json
import os
import re
import sys

# 조회를 여는 단어. 문장이 이 중 하나로 시작하지 않으면 통과시키지 않는다.
READ_STARTERS = ("select", "with", "explain", "show", "values", "table")

# 데이터나 구조를 바꾸는 단어. 하나라도 나오면 통과시키지 않는다.
WRITE_WORDS = (
    "insert", "update", "delete", "drop", "truncate", "alter", "create",
    "replace", "merge", "upsert", "grant", "revoke", "copy", "call", "do",
    "execute", "prepare", "vacuum", "analyze", "reindex", "cluster",
    "refresh", "lock", "listen", "notify", "unlisten", "discard", "reset",
    "set", "begin", "start", "commit", "rollback", "savepoint", "declare",
    "fetch", "move", "close", "into", "rename", "attach", "detach",
    "nextval", "setval", "pg_terminate_backend", "pg_cancel_backend",
    "dblink", "comment", "security",
)

WRITE_PATTERN = re.compile(
    r"\b(" + "|".join(WRITE_WORDS) + r")\b", re.IGNORECASE
)

UNLOCK_FILENAME = "sql-write-unlock"

# 이 훅이 지켜보는 도구.
#
# `execute_sql` 은 조회와 쓰기가 한 도구에 섞여 있어 쿼리문을 읽어 가려야 한다.
# `apply_migration` 은 가릴 것이 없다 — 마이그레이션은 정의상 데이터베이스의 구조를
# 바꾸는 스크립트이므로 전부 쓰기다. 그래서 쿼리 내용과 무관하게 열쇠를 요구한다.
SQL_TOOL = "mcp__Supabase__execute_sql"
MIGRATION_TOOL = "mcp__Supabase__apply_migration"
WATCHED_TOOLS = (SQL_TOOL, MIGRATION_TOOL)


def unlock_path() -> str:
    """열쇠 파일의 경로. 훅 파일 위치를 기준으로 삼아 실행 위치와 무관하게 같은 곳을 본다."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        UNLOCK_FILENAME)


def consume_unlock() -> bool:
    """열쇠가 있으면 쓰고 없앤다. 썼으면 True."""
    path = unlock_path()
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def strip_noise(sql: str) -> str:
    """주석과 문자열 리터럴을 지운다.

    문자열 안에 든 단어는 실행되는 명령이 아니라 값이므로, 위험 단어를 찾기
    전에 지워야 멀쩡한 조회가 잘못 걸리지 않는다.
    """
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)          # /* 블록 주석 */
    sql = re.sub(r"--[^\n]*", " ", sql)                        # -- 줄 주석
    sql = re.sub(r"\$([A-Za-z_]*)\$.*?\$\1\$", " '' ", sql, flags=re.S)  # $$ 본문 $$
    sql = re.sub(r"'(?:[^']|'')*'", " '' ", sql)               # '문자열'
    return sql


def classify(query: str):
    """(통과시켜도 되는가, 왜 아닌가) 를 돌려준다."""
    cleaned = strip_noise(query)

    statements = [s.strip() for s in cleaned.split(";")]
    statements = [s for s in statements if s]
    if not statements:
        return False, "읽기 전용 쿼리가 아닙니다 — 쿼리가 비어 있어 무엇을 실행하는지 판단할 수 없습니다"

    for statement in statements:
        first = re.split(r"[\s(]+", statement.lstrip("("), 1)[0].lower()
        if first not in READ_STARTERS:
            return False, f"읽기 전용 쿼리가 아닙니다 — 조회로 시작하지 않는 문장이 있습니다 ({first})"

    found = WRITE_PATTERN.search(cleaned)
    if found:
        return False, f"읽기 전용 쿼리가 아닙니다 — 데이터나 구조를 바꾸는 단어가 있습니다 ({found.group(1).lower()})"

    return True, None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # 입력을 못 읽으면 판단하지 않고 원래 권한 흐름에 맡긴다.
        return 0

    tool = payload.get("tool_name")
    if tool not in WATCHED_TOOLS:
        return 0

    if tool == MIGRATION_TOOL:
        reason = "마이그레이션은 데이터베이스의 구조를 바꾸는 스크립트입니다"
    else:
        query = (payload.get("tool_input") or {}).get("query") or ""
        is_read_only, reason = classify(query)
        if is_read_only:
            return 0

    # 사람이 허락해 둔 일회용 열쇠가 있으면 이번 한 번만 통과시킨다.
    if consume_unlock():
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{reason}. "
                "데이터베이스의 데이터나 구조를 바꾸는 쿼리는 사용자의 허락 없이 실행할 수 없습니다. "
                f"사용자가 승인했다면 열쇠 파일({UNLOCK_FILENAME})을 만든 뒤 다시 실행하십시오. "
                "열쇠는 한 번 쓰면 사라집니다."
            ),
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
