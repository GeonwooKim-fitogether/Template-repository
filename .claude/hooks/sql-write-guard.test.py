#!/usr/bin/env python3
"""sql-write-guard 훅의 판단이 맞는지 확인하는 시험.

실행: python3 .claude/hooks/sql-write-guard.test.py

두 방향을 모두 본다. 조회는 통과해야 하고(통과하지 않으면 확인 창이 계속 떠서
훅을 넣은 의미가 없다), 데이터를 바꾸는 쿼리는 반드시 걸려야 한다(걸리지 않으면
훅이 있으나 마나다).
"""

import importlib.util
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
GUARD = HERE / "sql-write-guard.py"

spec = importlib.util.spec_from_file_location("guard", GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

# 통과해야 하는 쿼리 — 읽기만 한다
SHOULD_PASS = [
    "select 1;",
    "select item_number, name from item where item_number in ('SMT18-0099');",
    "with vals as (select 1 as a) select * from vals;",
    "select attrs_non_rev->>'mfr' mfr from item order by item_number;",
    "show search_path;",
    "select count(*) from spec_value_provenance where source = 'datasheet';",
    # 문자열 안에 위험해 보이는 단어가 있어도 값일 뿐이므로 통과해야 한다
    "select * from log where action = 'delete';",
    "select 'drop table x' as note;",
    # 주석 안의 단어도 마찬가지
    "select 1; -- delete from item",
    "/* update 예정 */ select 1;",
    "select * from item offset 10 limit 5;",
]

# 반드시 걸려야 하는 쿼리 — 데이터나 구조를 바꾼다
SHOULD_DENY = [
    "delete from item where item_number = 'SMT18-0099';",
    "drop table item;",
    "truncate item;",
    "update item set name = 'x' where item_number = 'y';",
    "insert into item (item_number) values ('SMT99-9999');",
    "alter table item add column foo text;",
    "create index on item (item_number);",
    # 앞 문장이 조회라도 뒤에 쓰기가 붙어 있으면 걸려야 한다
    "select 1; delete from item;",
    # 쓰기를 품은 CTE
    "with d as (delete from item returning *) select * from d;",
    # select ... into 는 표를 만든다
    "select * into backup_item from item;",
    "grant select on item to anon;",
    "",
    "   ",
]


def check_classify() -> int:
    failures = 0
    for sql in SHOULD_PASS:
        ok, reason = guard.classify(sql)
        if not ok:
            print(f"  [실패] 통과해야 하는데 걸렸다: {sql!r} — {reason}")
            failures += 1
    for sql in SHOULD_DENY:
        ok, _ = guard.classify(sql)
        if ok:
            print(f"  [실패] 걸려야 하는데 통과했다: {sql!r}")
            failures += 1
    return failures


def run_hook(payload: dict) -> str:
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"훅이 0 이 아닌 코드로 끝났다: {result.returncode}"
    return result.stdout.strip()


def decision_of(out: str):
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return None


def check_hook_output() -> int:
    failures = 0

    out = run_hook({
        "tool_name": "mcp__Supabase__execute_sql",
        "tool_input": {"query": "select 1;"},
    })
    if out:
        print(f"  [실패] 조회인데 훅이 무언가를 출력했다: {out}")
        failures += 1

    out = run_hook({
        "tool_name": "mcp__Supabase__execute_sql",
        "tool_input": {"query": "delete from item;"},
    })
    if decision_of(out) != "deny":
        print(f"  [실패] 삭제 쿼리의 판정이 deny 가 아니다: {out!r}")
        failures += 1

    # 다른 도구의 호출에는 참견하지 않아야 한다
    out = run_hook({
        "tool_name": "Bash",
        "tool_input": {"command": "delete from item"},
    })
    if out:
        print(f"  [실패] 다른 도구인데 훅이 참견했다: {out}")
        failures += 1

    return failures


def check_unlock() -> int:
    """일회용 열쇠가 딱 한 번만 통하는지 확인한다."""
    failures = 0
    key = pathlib.Path(guard.unlock_path())
    existed = key.exists()
    if existed:  # 사람이 만들어 둔 열쇠를 시험이 소비해 버리면 안 된다
        print("  [건너뜀] 열쇠 파일이 이미 있어 이 시험은 돌리지 않는다")
        return 0

    key.write_text("시험용 열쇠\n")
    out = run_hook({
        "tool_name": "mcp__Supabase__execute_sql",
        "tool_input": {"query": "delete from item;"},
    })
    if out:
        print(f"  [실패] 열쇠가 있는데도 막혔다: {out}")
        failures += 1
    if key.exists():
        print("  [실패] 열쇠를 쓰고도 파일이 남아 있다 — 일회용이 아니다")
        failures += 1
        key.unlink()

    # 같은 쿼리를 한 번 더 — 이번에는 열쇠가 없으므로 막혀야 한다
    out = run_hook({
        "tool_name": "mcp__Supabase__execute_sql",
        "tool_input": {"query": "delete from item;"},
    })
    if decision_of(out) != "deny":
        print(f"  [실패] 열쇠를 쓴 뒤에도 계속 통과한다: {out!r}")
        failures += 1

    return failures


if __name__ == "__main__":
    total = check_classify() + check_hook_output() + check_unlock()
    if total:
        print(f"\n실패 {total}건")
        sys.exit(1)
    print(f"✓ 통과 — 조회 {len(SHOULD_PASS)}건은 그대로 지나가고, "
          f"쓰기 {len(SHOULD_DENY)}건은 모두 차단됐으며, "
          f"열쇠는 한 번만 통했습니다.")
