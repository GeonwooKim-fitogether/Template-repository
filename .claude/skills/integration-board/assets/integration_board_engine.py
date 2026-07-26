#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합 현황판(Integration Board) 고정 엔진.

무엇을 하나
-----------
프로젝트가 소유한 **config**(어휘·관심사 정의)와 매 실행 갱신되는 **data**(사실)를 읽어,
검증하고, 숫자와 판정을 **직접 계산한 뒤**, 고정 템플릿(board_template.html)에 주입해
자체완결 HTML 한 장을 만든다.

왜 이렇게 하나
--------------
사람이나 LLM이 매번 보고서를 새로 쓰면 판이 매번 달라지고, 숫자는 손으로 옮겨 적히다 틀린다.
그래서 이 엔진은 두 가지를 구조적으로 막는다.

1. **산문 슬롯이 없다.** data에 자유 서술 필드가 없다. 화면에 나오는 모든 문장은
   (a) config에 선언된 고정 설명이거나 (b) 이 엔진이 데이터에서 계산한 문장이다.
2. **스키마를 어기면 렌더하지 않는다.** 필수 누락·알 수 없는 값·없는 id 참조·여분 필드는
   전부 검증에서 걸려 종료 코드 2로 실패한다. 조용히 넘어가지 않는다.

실행
----
    python3 integration_board_engine.py --config <config.json> --data <data.json> --out <out.html>

인자를 모두 생략하면 번들된 예시(board.config.example.json + board.example.json)로 데모를 만든다.

의존성
------
파이썬 표준 라이브러리만 쓴다. 외부 패키지 0. 산출 HTML도 인라인 CSS/JS로 외부 요청 0.

스키마 정본: ../reference/board-schema.md
"""

import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HERE, "board_template.html")
MARKER = "/*__BOARD_DATA__*/null"

# ══════════════════════════════════════════════════════════════════════════
# 1. 엔진 상수 — 판정 규칙은 여기 한 곳에 고정한다. 데이터가 바꿀 수 없다.
# ══════════════════════════════════════════════════════════════════════════

STALL_RISK_DAYS = 14   # 이 일수 이상 멈춰 있으면 '위험', 1일 이상이면 '주의'
DELAY_RISK_DAYS = 30   # 계획보다 이 일수 이상 늦으면 '위험', 1일 이상이면 '주의'
RECENT_DAYS = 7        # "이번 주"의 정의 — 오늘로부터 뒤로 7일
LANE_MAX_CARDS = 3     # 관심사 열에 펼쳐 보이는 카드 수. 나머지는 "그 외 n건"으로 접는다.

SEV_ORDER = {"risk": 0, "warn": 1, "ok": 2, "info": 3}   # 급한 것이 위로
SEV_EM = {"risk": "r", "warn": "a", "ok": "g", "info": "i"}  # 숫자 강조 색 클래스

# 색은 미리 정해 둔 이름 중에서만 고른다 — 프로젝트가 새 색을 지어낼 수 없게.
TONES = {
    "red": "var(--red)", "amber": "var(--amber)", "green": "var(--green)",
    "blue": "var(--blue)", "teal": "var(--teal)", "dim": "var(--dim)",
    "muted": "var(--muted)", "neutral": "var(--border-strong)",
}

BLOCK_VALUES = ("conflict", "waiting")       # 작업이 막힌 사정
VIOLATION_SEVERITIES = ("block", "warn")     # 위반의 무게
METRIC_KINDS = (
    "asset", "check", "area_stalled", "area_delay", "undated", "status_recent", "drift",
)
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ── 화면 문구 기본값 ──────────────────────────────────────────────────────
# config의 text 절로 덮어쓸 수 있다. config가 비어도 보드가 그대로 동작하도록 전부 기본값을 갖는다.
TEXT = {
    "metaPrefix": "갱신", "metaSuffix": "· 자동", "metaNote": "고정 계기판 · 같은 링크로 재게시",
    "themeLight": "테마: 밝게", "themeDark": "테마: GC 다크",
    "legendTitle": "색으로 읽는 법", "legendConflict": "충돌 · 위반",
    "legendWaiting": "대기 · 주의", "legendTrace": "연결 보기 (카드를 누르면 켜짐)",
    "band1Hint": "카드를 누르면 아래 두 밴드에서 연결된 항목만 밝아집니다",
    "verdictKicker": "종합 판정", "decideCount": "결정 필요",
    "decideHint": "사람이 정해 주기 전에는 진행할 수 없는 것", "decideBadge": "결정 필요",
    "countUnit": "건", "laneOk": "이상 없음", "laneMore": "그 외 {n}건 (덜 급한 순으로 접힘)",
    "meanLabel": "뜻", "whyLabel": "걸리면",
    "viewSwitchLabel": "실행 현황 보기 전환",
    "viewNote": "같은 작업 목록을, 칸반은 상태 축으로 간트는 시간 축으로 봅니다.",
    "tabKanban": "칸반", "tabKanbanEn": "Kanban", "tabGantt": "간트", "tabGanttEn": "Gantt",
    "assetsTitle": "공용 자산 — 여러 팀이 같이 쓰는 것",
    "blockConflict": "충돌", "blockWaiting": "대기",
    "ganttAxisLabel": "제품 영역 / 작업",
    "ganttEmptyArea": '계획 날짜가 있는 작업 없음 — 아래 "일정 미정"에 있습니다',
    "ganttDelayTip": "예상 종료가 계획을 넘김",
    "ganttLegPlan": "계획", "ganttLegFill": "실행(진척률)",
    "ganttLegDelay": "지연 — 예상 종료가 계획을 넘김",
    "ganttLegDep": "의존 — 앞 작업이 끝나야 시작",
    "ganttLegToday": "오늘", "ganttLegDue": "목표일",
    "ganttLegHint": "영역 행을 누르면 그 안의 작업이 펼쳐집니다",
    "undatedGroup": "일정 미정", "undatedSuffix": "미정 {n}",
    "undatedRow": "계획 시작·종료일 미정 — 시간 축에 올릴 수 없음",
    "checkPass": "통과", "checkWarn": "주의", "checkBlock": "위반",
    "vioBlock": "막힘", "vioWarn": "주의", "okNone": "이상 없음",
    "traceChip": "연결 보기", "traceOff": "해제",
    "checksLabel": "자동 검사",
    "assetBadgeConflict": "{all}팀 중 {n}팀 충돌",
    "assetBadgeWaiting": "{n}팀 등록 대기",
    "assetBadgeOk": "이상 없음",
    "recentPrefix": "이번 주",
}

DEFAULT_BANDS = {
    "overview": {"n": "밴드 1", "title": "종합 판정", "en": "Executive Overview",
                 "caption": "지금 무엇을 결정해야 하나"},
    "delivery": {"n": "밴드 2", "title": "실행 현황", "en": "Delivery Status",
                 "caption": "일이 어디까지 왔고 어디서 막혔나"},
    "quality":  {"n": "밴드 3", "title": "품질 기준선", "en": "Quality Baseline",
                 "caption": "지켜야 할 선이 지켜지고 있나"},
}

DEFAULT_VERDICTS = {
    "risk": {"word": "위험", "tone": "red",
             "why": "공용 자산 충돌이 풀리지 않았다 — 해소 전에는 본선 반영을 멈춘다"},
    "warn": {"word": "주의", "tone": "amber", "why": "막는 것은 없지만 결정이 밀려 있다"},
    "ok":   {"word": "정상", "tone": "green", "why": "충돌 없음 — 순서대로 본선에 반영할 수 있다"},
}

DEFAULT_AXIS = {"leadDays": 14, "days": 84, "tickDays": 7}


# ══════════════════════════════════════════════════════════════════════════
# 2. 검증 — 어기면 렌더하지 않는다
# ══════════════════════════════════════════════════════════════════════════

class Validator:
    """오류를 모아 두었다가 한 번에 전부 보여 준다.

    하나 고치고 다시 돌리면 다음 오류가 나오는 방식은 사람을 지치게 한다.
    그래서 치명적이지 않은 오류는 모두 모아서 함께 낸다.
    """

    def __init__(self):
        self.errors = []

    def err(self, path, message, hint=None):
        self.errors.append((path, message, hint))
        return False

    # ── 기본 형태 ────────────────────────────────────────────────────────
    def obj(self, path, value, required=(), optional=()):
        if not isinstance(value, dict):
            return self.err(path, f"객체(JSON object)여야 하는데 {_typename(value)}가 왔습니다")
        ok = True
        for key in required:
            if key not in value:
                ok = self.err(f"{path}.{key}", "필수 항목이 빠졌습니다")
        allowed = set(required) | set(optional)
        for key in sorted(set(value) - allowed):
            ok = self.err(f"{path}.{key}", "스키마에 없는 항목입니다",
                          "쓸 수 있는 항목: " + ", ".join(sorted(allowed)))
        return ok

    def lst(self, path, value, min_len=0):
        if not isinstance(value, list):
            return self.err(path, f"배열(JSON array)이어야 하는데 {_typename(value)}가 왔습니다")
        if len(value) < min_len:
            return self.err(path, f"항목이 최소 {min_len}개 필요한데 {len(value)}개입니다")
        return True

    def text(self, path, value, allow_empty=False):
        if not isinstance(value, str):
            return self.err(path, f"문자열이어야 하는데 {_typename(value)}가 왔습니다")
        if not allow_empty and not value.strip():
            return self.err(path, "빈 문자열은 쓸 수 없습니다")
        return True

    def key(self, path, value):
        if not self.text(path, value):
            return False
        if not KEY_RE.match(value):
            return self.err(path, f"id로 쓸 수 없는 값입니다: {value!r}",
                            "영문/숫자로 시작하고 영문·숫자·  . _ : - 만 쓸 수 있습니다")
        return True

    def enum(self, path, value, allowed, what):
        if value not in allowed:
            return self.err(path, f"알 수 없는 {what}입니다: {value!r}",
                            "쓸 수 있는 값: " + ", ".join(sorted(allowed)))
        return True

    def ref(self, path, value, pool, what):
        if value not in pool:
            return self.err(path, f"{what} '{value}'를 찾을 수 없습니다",
                            ("선언된 값: " + ", ".join(sorted(pool))) if pool
                            else f"{what}가 하나도 선언돼 있지 않습니다")
        return True

    def day(self, path, value):
        if not isinstance(value, str) or not DATE_RE.match(value):
            return self.err(path, f"날짜는 YYYY-MM-DD 형식이어야 합니다: {value!r}")
        try:
            date.fromisoformat(value)
        except ValueError:
            return self.err(path, f"달력에 없는 날짜입니다: {value!r}")
        return True

    def whole(self, path, value, lo=None, hi=None):
        if isinstance(value, bool) or not isinstance(value, int):
            return self.err(path, f"정수여야 하는데 {_typename(value)}가 왔습니다")
        if lo is not None and value < lo:
            return self.err(path, f"{lo} 이상이어야 하는데 {value}입니다")
        if hi is not None and value > hi:
            return self.err(path, f"{hi} 이하여야 하는데 {value}입니다")
        return True

    def flag(self, path, value):
        if not isinstance(value, bool):
            return self.err(path, f"true/false여야 하는데 {_typename(value)}가 왔습니다")
        return True


def _is_day(value):
    """실제로 달력에 있는 YYYY-MM-DD인가. 형식만 맞는 '2026-02-31'은 False."""
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _typename(value):
    return {dict: "객체", list: "배열", str: "문자열", bool: "true/false",
            int: "정수", float: "소수", type(None): "null"}.get(type(value), type(value).__name__)


def _keyed(v, path, items, required, optional, keyfield="key"):
    """key가 있는 목록을 검증하고 {key: item} 사전을 만든다. 중복 key는 오류."""
    out = {}
    for i, item in enumerate(items):
        p = f"{path}[{i}]"
        if not v.obj(p, item, required, optional):
            continue
        if keyfield not in item:
            continue
        if not v.key(f"{p}.{keyfield}", item[keyfield]):
            continue
        k = item[keyfield]
        if k in out:
            v.err(f"{p}.{keyfield}", f"id가 중복됩니다: {k!r}")
            continue
        out[k] = item
    return out


def validate_config(v, cfg):
    """config를 검증하고, 기본값을 채운 정규화 결과를 돌려준다."""
    v.obj("config", cfg,
          required=("board", "lanes", "statuses", "areas", "cards"),
          optional=("bands", "verdicts", "assets", "checks", "drift", "honesty", "axis", "text"))
    if v.errors and not isinstance(cfg, dict):
        return None

    board = cfg.get("board", {})
    if v.obj("config.board", board, required=("title",),
             optional=("eyebrow", "subtitle", "docTitle")):
        for k in ("title", "eyebrow", "subtitle", "docTitle"):
            if k in board:
                v.text(f"config.board.{k}", board[k], allow_empty=(k != "title"))

    bands = dict((k, dict(b)) for k, b in DEFAULT_BANDS.items())
    if "bands" in cfg and v.obj("config.bands", cfg["bands"], optional=tuple(DEFAULT_BANDS)):
        for name, band in cfg["bands"].items():
            if name not in DEFAULT_BANDS:
                continue
            if v.obj(f"config.bands.{name}", band, optional=("n", "title", "en", "caption")):
                for k, val in band.items():
                    if v.text(f"config.bands.{name}.{k}", val, allow_empty=True):
                        bands[name][k] = val

    # 종합 판정의 말(위험/주의/정상)과 그 이유. 색(tone)은 의미색이라 엔진이 고정한다.
    verdicts = dict((k, dict(v0)) for k, v0 in DEFAULT_VERDICTS.items())
    if "verdicts" in cfg and v.obj("config.verdicts", cfg["verdicts"],
                                   optional=tuple(DEFAULT_VERDICTS)):
        for name, spec in cfg["verdicts"].items():
            if name not in DEFAULT_VERDICTS:
                continue
            if v.obj(f"config.verdicts.{name}", spec, optional=("word", "why")):
                for k, val in spec.items():
                    if v.text(f"config.verdicts.{name}.{k}", val, allow_empty=(k == "why")):
                        verdicts[name][k] = val

    axis = dict(DEFAULT_AXIS)
    if "axis" in cfg and v.obj("config.axis", cfg["axis"], optional=tuple(DEFAULT_AXIS)):
        for k, val in cfg["axis"].items():
            if v.whole(f"config.axis.{k}", val, lo=1, hi=3650):
                axis[k] = val
    if axis["tickDays"] > axis["days"]:
        v.err("config.axis.tickDays", "축 길이(days)보다 눈금 간격이 큽니다")

    text = dict(TEXT)
    if "text" in cfg and isinstance(cfg["text"], dict):
        for k, val in cfg["text"].items():
            if k not in TEXT:
                v.err(f"config.text.{k}", "알 수 없는 문구 키입니다",
                      "쓸 수 있는 키 목록은 reference/board-schema.md의 '문구(text)' 절에 있습니다")
            elif v.text(f"config.text.{k}", val, allow_empty=True):
                text[k] = val
    elif "text" in cfg:
        v.err("config.text", "객체여야 합니다")

    lanes = checks = assets = areas = statuses = {}
    if v.lst("config.lanes", cfg.get("lanes"), 1):
        lanes = _keyed(v, "config.lanes", cfg["lanes"], ("key", "label"), ("en",))
    if v.lst("config.areas", cfg.get("areas"), 1):
        areas = _keyed(v, "config.areas", cfg["areas"], ("key", "label"), ("en",))
    if v.lst("config.statuses", cfg.get("statuses"), 1):
        statuses = _keyed(v, "config.statuses", cfg["statuses"],
                          ("key", "label", "tone"), ("mean",))
        for k, st in statuses.items():
            v.enum(f"config.statuses[{k}].tone", st.get("tone"), TONES, "색 이름")
    if "assets" in cfg and v.lst("config.assets", cfg["assets"]):
        assets = _keyed(v, "config.assets", cfg["assets"], ("key", "label", "plain"), ("why",))
    if "checks" in cfg and v.lst("config.checks", cfg["checks"]):
        checks = _keyed(v, "config.checks", cfg["checks"], ("key", "name", "plain"), ("why",))

    drift = cfg.get("drift")
    if drift is not None:
        v.obj("config.drift", drift, required=("gapLabel", "pivotLabel"),
              optional=("note", "linkLabel", "href"))

    if "honesty" in cfg:
        v.text("config.honesty", cfg["honesty"], allow_empty=True)

    cards = {}
    if v.lst("config.cards", cfg.get("cards"), 1):
        cards = _keyed(v, "config.cards", cfg["cards"],
                       ("key", "lane", "title", "plain", "metric"),
                       ("why", "decide", "traceChecks"))
        for k, card in cards.items():
            p = f"config.cards[{k}]"
            v.ref(f"{p}.lane", card.get("lane"), set(lanes), "관심사 열(lane)")
            if "decide" in card:
                v.flag(f"{p}.decide", card["decide"])
            for i, ck in enumerate(card.get("traceChecks", []) or []):
                v.ref(f"{p}.traceChecks[{i}]", ck, set(checks), "자동 검사")
            _validate_metric(v, f"{p}.metric", card.get("metric"),
                             assets, checks, areas, statuses, drift)

    return {"board": board, "bands": bands, "verdicts": verdicts,
            "axis": axis, "text": text, "lanes": lanes,
            "areas": areas, "statuses": statuses, "assets": assets, "checks": checks,
            "cards": cards, "drift": drift, "honesty": cfg.get("honesty", ""),
            "laneOrder": [l["key"] for l in cfg.get("lanes", []) if isinstance(l, dict) and "key" in l],
            "cardOrder": [c["key"] for c in cfg.get("cards", []) if isinstance(c, dict) and "key" in c]}


_METRIC_BINDING = {
    "asset": ("asset", "assets", "공용 자산"),
    "check": ("check", "checks", "자동 검사"),
    "area_stalled": ("area", "areas", "제품 영역"),
    "area_delay": ("area", "areas", "제품 영역"),
    "status_recent": ("status", "statuses", "상태"),
    "undated": (None, None, None),
    "drift": (None, None, None),
}


def _validate_metric(v, path, metric, assets, checks, areas, statuses, drift):
    if not isinstance(metric, dict):
        return v.err(path, f"객체여야 하는데 {_typename(metric)}가 왔습니다")
    kind = metric.get("kind")
    if kind is None:
        return v.err(f"{path}.kind", "필수 항목이 빠졌습니다",
                     "쓸 수 있는 값: " + ", ".join(METRIC_KINDS))
    if not v.enum(f"{path}.kind", kind, METRIC_KINDS, "지표 종류(kind)"):
        return False
    field, pool_name, what = _METRIC_BINDING[kind]
    required = ("kind",) + ((field,) if field else ())
    if not v.obj(path, metric, required=required):
        return False
    if field:
        pool = {"assets": assets, "checks": checks, "areas": areas, "statuses": statuses}[pool_name]
        v.ref(f"{path}.{field}", metric.get(field), set(pool), what)
    if kind == "drift" and drift is None:
        v.err(path, "kind가 'drift'인 카드가 있는데 config.drift가 선언돼 있지 않습니다",
              "config에 drift: {gapLabel, pivotLabel} 를 넣으세요")
    return True


WORK_REQUIRED = ("id", "title", "area", "team", "status")
WORK_OPTIONAL = ("block", "touches", "planStart", "planEnd", "progress", "eta",
                 "deps", "stalledDays", "drift")


def validate_data(v, data, C):
    """data를 검증한다. config(C)에 선언되지 않은 것을 참조하면 오류."""
    if not v.obj("data", data, required=("today", "works"),
                 optional=("updated", "target", "violations", "drift")):
        return None

    if "today" in data:
        v.day("data.today", data["today"])
    if "updated" in data:
        v.text("data.updated", data["updated"])

    target = data.get("target")
    if target is not None and v.obj("data.target", target, required=("date",)):
        v.day("data.target.date", target["date"])

    works = {}
    if v.lst("data.works", data.get("works"), 1):
        works = _keyed(v, "data.works", data["works"], WORK_REQUIRED, WORK_OPTIONAL, keyfield="id")
        for wid, w in works.items():
            p = f"data.works[{wid}]"
            v.text(f"{p}.title", w.get("title"))
            v.text(f"{p}.team", w.get("team"))
            v.ref(f"{p}.area", w.get("area"), set(C["areas"]), "제품 영역")
            v.ref(f"{p}.status", w.get("status"), set(C["statuses"]), "상태")
            if "block" in w:
                v.enum(f"{p}.block", w["block"], BLOCK_VALUES, "막힘 사유(block)")
            if "touches" in w:
                v.ref(f"{p}.touches", w["touches"], set(C["assets"]), "공용 자산")
            if "progress" in w:
                v.whole(f"{p}.progress", w["progress"], 0, 100)
            if "stalledDays" in w:
                v.whole(f"{p}.stalledDays", w["stalledDays"], 0, 3650)
            if "drift" in w:
                v.flag(f"{p}.drift", w["drift"])

            has_start, has_end = "planStart" in w, "planEnd" in w
            if has_start != has_end:
                v.err(p, "planStart와 planEnd는 함께 있거나 함께 없어야 합니다",
                      "한쪽만 있으면 시간 축에 그릴 수 없습니다")
            for k in ("planStart", "planEnd", "eta"):
                if k in w:
                    v.day(f"{p}.{k}", w[k])
            # 날짜 비교는 두 값이 모두 '달력에 실제로 있는 날'일 때만 한다.
            # 형식만 맞는 값(2026-02-31)으로 비교하면 여기서 예외가 터져,
            # 이미 잡아 둔 다른 오류들까지 함께 보여 주지 못한다.
            if has_start and has_end and _is_day(w["planStart"]) and _is_day(w["planEnd"]):
                if date.fromisoformat(w["planEnd"]) < date.fromisoformat(w["planStart"]):
                    v.err(f"{p}.planEnd", "계획 종료일이 시작일보다 빠릅니다")
            if "eta" in w and not has_end:
                v.err(f"{p}.eta", "eta(예상 종료)는 planEnd가 있는 작업에만 쓸 수 있습니다")

        for wid, w in works.items():
            for i, dep in enumerate(w.get("deps", []) or []):
                path = f"data.works[{wid}].deps[{i}]"
                if v.ref(path, dep, set(works), "작업") and dep == wid:
                    v.err(path, "자기 자신을 선행 작업으로 둘 수 없습니다")

    violations = []
    if "violations" in data and v.lst("data.violations", data["violations"]):
        for i, vio in enumerate(data["violations"]):
            p = f"data.violations[{i}]"
            if not v.obj(p, vio, required=("check", "ref", "severity")):
                continue
            v.ref(f"{p}.check", vio["check"], set(C["checks"]), "자동 검사")
            v.ref(f"{p}.ref", vio["ref"], set(works), "작업")
            v.enum(f"{p}.severity", vio["severity"], VIOLATION_SEVERITIES, "위반 무게(severity)")
            violations.append(vio)

    drift = data.get("drift")
    if drift is not None:
        if v.obj("data.drift", drift, required=("gaps", "pivots")):
            v.whole("data.drift.gaps", drift["gaps"], 0)
            v.whole("data.drift.pivots", drift["pivots"], 0)
        if C["drift"] is None:
            v.err("data.drift", "data에 drift가 있는데 config.drift가 선언돼 있지 않습니다",
                  "표시할 이름(gapLabel·pivotLabel)이 없어 그릴 수 없습니다")

    for key, card in C["cards"].items():
        metric = card.get("metric") or {}
        if metric.get("kind") == "drift" and drift is None:
            v.err(f"config.cards[{key}].metric",
                  "kind가 'drift'인 카드가 있는데 data.drift가 없습니다",
                  "data에 drift: {gaps, pivots} 를 넣으세요")

    return {"today": data.get("today"), "updated": data.get("updated"),
            "target": target, "works": works, "violations": violations, "drift": drift,
            "workOrder": [w["id"] for w in data.get("works", [])
                          if isinstance(w, dict) and "id" in w]}


# ══════════════════════════════════════════════════════════════════════════
# 3. 도출 — 화면에 나오는 숫자와 판정은 전부 여기서 계산한다
# ══════════════════════════════════════════════════════════════════════════

def _josa(word, with_batchim, without):
    """받침에 따라 조사를 고른다(예: '검토대기'+가, '진행 중'+이)."""
    if not word:
        return without
    ch = word[-1]
    if "가" <= ch <= "힣":
        return with_batchim if (ord(ch) - 0xAC00) % 28 else without
    return without


def _seg(t, em=None):
    return {"t": t, "em": em} if em is not None else {"t": t}


def compute(C, D):
    """검증을 통과한 config·data에서 화면 모델을 만든다."""
    T = C["text"]
    today = date.fromisoformat(D["today"])
    axis0 = today - timedelta(days=C["axis"]["leadDays"])
    span = C["axis"]["days"]

    def di(iso):
        return (date.fromisoformat(iso) - axis0).days

    order = D["workOrder"]
    works = D["works"]
    block_refs = {v["ref"] for v in D["violations"] if v["severity"] == "block"}

    # ── 작업 뷰 모델 ──────────────────────────────────────────────────────
    wm = {}
    for wid in order:
        w = works[wid]
        dated = "planStart" in w and "planEnd" in w
        wm[wid] = {
            "id": wid, "title": w["title"], "team": w["team"], "status": w["status"],
            "area": w["area"], "areaLabel": C["areas"][w["area"]]["label"],
            "block": w.get("block", ""), "touches": w.get("touches"),
            "progress": w.get("progress", 0),
            "s": di(w["planStart"]) if dated else None,
            "e": di(w["planEnd"]) if dated else None,
            "et": di(w["eta"]) if "eta" in w else None,
            "risk": wid in block_refs,
        }

    def delay_days(wid):
        """예상 종료가 계획 종료를 넘긴 일수. 넘기지 않았으면 0."""
        w = wm[wid]
        if w["e"] is None or w["et"] is None:
            return 0
        return max(0, w["et"] - w["e"])

    # ── 칸반 열 ──────────────────────────────────────────────────────────
    columns = []
    for key, st in C["statuses"].items():
        columns.append({
            "key": key, "label": st["label"], "tone": TONES[st["tone"]],
            "mean": st.get("mean", ""),
            "works": [wid for wid in order if wm[wid]["status"] == key],
        })

    # ── 제품 영역 롤업 ────────────────────────────────────────────────────
    # 계획 구간은 자식의 min/max, 진척은 기간 가중 평균, 예상 종료는 자식의 max.
    # 손으로 넣는 숫자는 하나도 없다.
    rollup = []
    for key, area in C["areas"].items():
        ids = [wid for wid in order if wm[wid]["area"] == key]
        dated = [wid for wid in ids if wm[wid]["s"] is not None]
        conflicts = sum(1 for wid in ids if wm[wid]["block"] == "conflict")
        waits = sum(1 for wid in ids if wm[wid]["block"] == "waiting")
        badges = []
        if conflicts:
            badges.append({"label": f"{T['blockConflict']} {conflicts}", "tone": "r"})
        if waits:
            badges.append({"label": f"{T['blockWaiting']} {waits}", "tone": "a"})
        undated_n = len(ids) - len(dated)
        cnt = f"{len(dated)}{T['countUnit']}"
        if undated_n:
            cnt += " · " + T["undatedSuffix"].format(n=undated_n)
        row = {"key": key, "label": area["label"], "works": ids, "dated": dated,
               "badges": badges, "cntText": cnt, "empty": not dated}
        if dated:
            total = sum(wm[i]["e"] - wm[i]["s"] + 1 for i in dated)
            row.update({
                "s": min(wm[i]["s"] for i in dated),
                "e": max(wm[i]["e"] for i in dated),
                "et": max((wm[i]["et"] if wm[i]["et"] is not None else wm[i]["e"]) for i in dated),
                "progress": round(sum(wm[i]["progress"] * (wm[i]["e"] - wm[i]["s"] + 1)
                                      for i in dated) / total),
            })
        rollup.append(row)

    undated_ids = [wid for wid in order if wm[wid]["s"] is None]

    # ── 공용 자산 집계 ────────────────────────────────────────────────────
    all_teams = len({wm[wid]["team"] for wid in order})
    assets = []
    for key, a in C["assets"].items():
        linked = [wid for wid in order if wm[wid]["touches"] == key]
        teams = len({wm[wid]["team"] for wid in linked})
        c_teams = len({wm[wid]["team"] for wid in linked if wm[wid]["block"] == "conflict"})
        w_teams = len({wm[wid]["team"] for wid in linked if wm[wid]["block"] == "waiting"})
        if c_teams:
            sev, badge = "risk", T["assetBadgeConflict"].format(all=all_teams, n=c_teams)
        elif w_teams:
            sev, badge = "warn", T["assetBadgeWaiting"].format(n=w_teams)
        else:
            sev, badge = "ok", T["assetBadgeOk"]
        assets.append({"key": key, "label": a["label"], "plain": a["plain"],
                       "why": a.get("why", ""), "sev": sev, "badge": badge,
                       "links": linked, "teams": teams,
                       "conflictTeams": c_teams, "waitTeams": w_teams})
    assets_by_key = {a["key"]: a for a in assets}

    # ── 자동 검사 집계 ────────────────────────────────────────────────────
    sev_label = {"block": T["vioBlock"], "warn": T["vioWarn"]}
    status_label = {"pass": T["checkPass"], "warn": T["checkWarn"], "block": T["checkBlock"]}
    checks = []
    for key, c in C["checks"].items():
        vios = [v for v in D["violations"] if v["check"] == key]
        status = "block" if any(v["severity"] == "block" for v in vios) \
            else "warn" if vios else "pass"
        checks.append({
            "key": key, "name": c["name"], "plain": c["plain"], "why": c.get("why", ""),
            "status": status, "statusLabel": status_label[status],
            # 위반 문구는 참조된 작업의 제목을 그대로 쓴다 — 매번 새로 쓰는 설명문을 두지 않는다.
            "violations": [{"ref": v["ref"], "what": wm[v["ref"]]["title"],
                            "sevLabel": sev_label[v["severity"]]} for v in vios],
        })
    checks_by_key = {c["key"]: c for c in checks}
    pass_checks = sum(1 for c in checks if c["status"] == "pass")

    # ── 밴드 1 카드 — 읽는 문장과 심각도를 지표 종류별로 계산 ─────────────
    cards = {}
    traces = {}
    for key in C["cardOrder"]:
        card = C["cards"][key]
        sev, reading, trace = _metric(card["metric"], C, D, T, wm, order, assets_by_key,
                                      checks_by_key, len(checks), pass_checks, undated_ids, today)
        for ck in card.get("traceChecks", []) or []:
            trace.setdefault("checks", [])
            if ck not in trace["checks"]:
                trace["checks"].append(ck)
        cards[key] = {"id": key, "lane": card["lane"], "title": card["title"],
                      "plain": card["plain"], "why": card.get("why", ""),
                      "severity": sev, "reading": reading,
                      # '결정 필요'는 실제로 걸려 있을 때만 붙인다. 늘 붙어 있으면 신호가 죽는다.
                      "decide": bool(card.get("decide")) and sev in ("risk", "warn")}
        traces[key] = trace

    lanes = []
    for lkey in C["laneOrder"]:
        lane = C["lanes"][lkey]
        mine = [cards[k] for k in C["cardOrder"] if cards[k]["lane"] == lkey]
        mine.sort(key=lambda c: SEV_ORDER[c["severity"]])   # 안정 정렬 — 같은 급이면 선언 순서
        shown, rest = mine[:LANE_MAX_CARDS], len(mine) - min(len(mine), LANE_MAX_CARDS)
        lanes.append({"key": lkey, "label": lane["label"], "en": lane.get("en", ""),
                      "count": len(mine), "cards": shown,
                      "moreText": T["laneMore"].format(n=rest) if rest else ""})

    # ── 종합 판정 ────────────────────────────────────────────────────────
    has_risk = any(c["severity"] == "risk" for c in cards.values()) \
        or any(c["status"] == "block" for c in checks)
    has_warn = any(c["severity"] == "warn" for c in cards.values())
    vkey = "risk" if has_risk else "warn" if has_warn else "ok"
    verdict = dict(C["verdicts"][vkey])
    verdict["tone"] = TONES[DEFAULT_VERDICTS[vkey]["tone"]]
    decides = sum(1 for c in cards.values() if c["decide"])

    # ── 의존선 ───────────────────────────────────────────────────────────
    links = []
    for wid in order:
        for dep in works[wid].get("deps", []) or []:
            if wm[dep]["e"] is not None and wm[wid]["s"] is not None:
                links.append([dep, wid])

    # ── 축 ───────────────────────────────────────────────────────────────
    tick = C["axis"]["tickDays"]
    grid = list(range(0, span + 1, tick))
    axis = {
        "days": span,
        "gridlines": grid,
        "ticks": [{"d": d, "label": (axis0 + timedelta(days=d)).strftime("%m-%d")} for d in grid],
        "todayD": di(D["today"]),
        "targetD": di(D["target"]["date"]) if D["target"] else None,
    }

    # ── 기획 정합성 막대 ──────────────────────────────────────────────────
    drift_m = None
    if D["drift"]:
        drift_m = {"reading": [
            _seg(C["drift"]["gapLabel"] + " "), _seg(f"{D['drift']['gaps']}{T['countUnit']}", ""),
            _seg(" 누적 · " + C["drift"]["pivotLabel"] + " "),
            _seg(f"{D['drift']['pivots']}{T['countUnit']}", ""),
        ]}

    return {
        "updated": D["updated"] or D["today"],
        "byId": wm, "columns": columns, "rollup": rollup, "undated": undated_ids,
        "undatedCntText": f"{len(undated_ids)}{T['countUnit']}",
        "assets": assets, "checks": checks, "lanes": lanes, "traces": traces,
        "cardTitle": {k: c["title"] for k, c in cards.items()},
        "verdict": verdict, "decides": decides, "links": links, "drift": drift_m,
    }, axis


def _metric(metric, C, D, T, wm, order, assets, checks, n_checks, pass_checks, undated, today):
    """지표 한 종류를 계산한다 → (심각도, 읽는 문장 조각들, 연결 대상).

    읽는 문장의 **문법**은 엔진이 고정하고, 그 안에 들어가는 **이름**(제품 영역·상태·
    공용 자산·기획 용어)만 config에서 온다. 그래서 매 실행 같은 문장이 나오고,
    사람이 새 문장을 지어 넣을 자리가 없다.
    """
    kind = metric["kind"]
    unit = T["countUnit"]

    if kind == "asset":
        a = assets[metric["asset"]]
        all_teams = len({wm[w]["team"] for w in order})
        if a["conflictTeams"]:
            reading = [_seg(f"{all_teams}팀 중 "), _seg(f"{a['conflictTeams']}팀", "r"),
                       _seg("이 서로 다르게 고쳤다")]
        elif a["waitTeams"]:
            reading = [_seg(f"{a['waitTeams']}팀", "a"), _seg("이 등록을 마치고 승인을 기다린다")]
        else:
            reading = [_seg("충돌 없음 — "), _seg(f"{a['teams']}팀", "g"), _seg("이 같은 값을 쓴다")]
        return a["sev"], reading, {"work": list(a["links"]), "assets": [a["key"]]}

    if kind == "check":
        c = checks[metric["check"]]
        n = len(c["violations"])
        tail = [_seg(f"{T['checksLabel']} {n_checks}개 중 "), _seg(f"{pass_checks}개", "g"),
                _seg(" 통과")]
        if n:
            reading = [_seg("위반 후보 "), _seg(f"{n}{unit}", "a"), _seg(" · ")] + tail
            sev = "warn"
        else:
            reading = [_seg("위반 없음 · ")] + tail
            sev = "ok"
        return sev, reading, {"work": [v["ref"] for v in c["violations"]], "checks": [c["key"]]}

    if kind == "area_stalled":
        ids = [w for w in order if wm[w]["area"] == metric["area"]]
        stalled = [(D["works"][w].get("stalledDays", 0), w) for w in ids]
        days, worst = max(stalled) if stalled else (0, None)
        if not days:
            return "ok", [_seg("멈춰 있는 작업 없음")], {"work": ids}
        label = C["statuses"][wm[worst]["status"]]["label"]
        reading = [_seg(label + _josa(label, "이", "가") + " "), _seg(f"{days}일", "a"),
                   _seg("째 움직이지 않는다")]
        return ("risk" if days >= STALL_RISK_DAYS else "warn"), reading, {"work": ids}

    if kind == "area_delay":
        ids = [w for w in order if wm[w]["area"] == metric["area"]]
        late = [(w, wm[w]["et"] - wm[w]["e"]) for w in ids
                if wm[w]["e"] is not None and wm[w]["et"] is not None and wm[w]["et"] > wm[w]["e"]]
        if not late:
            return "ok", [_seg("계획보다 늦은 작업 없음")], {"work": ids}
        worst = max(d for _, d in late)
        reading = [_seg(f"{len(late)}{unit}", "a"), _seg("이 계획보다 "),
                   _seg(f"{worst}일", "a"), _seg(" 늦다")]
        return ("risk" if worst >= DELAY_RISK_DAYS else "warn"), reading, \
               {"work": [w for w, _ in late]}

    if kind == "undated":
        if not undated:
            return "ok", [_seg("모든 작업이 시간 축에 올라가 있다")], {"work": []}
        return "warn", [_seg(f"{len(undated)}{unit}", "a"),
                        _seg("이 아직 시간 축에 올라가지 못했다")], {"work": list(undated)}

    if kind == "status_recent":
        skey = metric["status"]
        label = C["statuses"][skey]["label"]
        recent = []
        for w in order:
            if wm[w]["status"] != skey:
                continue
            end = D["works"][w].get("planEnd")
            if end and 0 <= (today - date.fromisoformat(end)).days <= RECENT_DAYS:
                recent.append(w)
        reading = [_seg(f"{T['recentPrefix']} {label} "), _seg(f"{len(recent)}{unit}", "g")]
        return "info", reading, {"work": recent}

    if kind == "drift":
        d = D["drift"]
        reading = [_seg(C["drift"]["gapLabel"] + " "), _seg(f"{d['gaps']}{unit}", "i"),
                   _seg(" 누적 · " + C["drift"]["pivotLabel"] + " "),
                   _seg(f"{d['pivots']}{unit}", "i")]
        return "info", reading, {"work": [w for w in order if D["works"][w].get("drift")]}

    raise AssertionError(f"검증을 통과했는데 모르는 지표 종류: {kind}")   # 도달 불가


# ══════════════════════════════════════════════════════════════════════════
# 4. 렌더 — 고정 템플릿에 한 곳으로 주입한다
# ══════════════════════════════════════════════════════════════════════════

def render(C, D):
    m, axis = compute(C, D)
    payload = {
        "cfg": {
            "board": {
                "title": C["board"]["title"],
                "eyebrow": C["board"].get("eyebrow", ""),
                "subtitle": C["board"].get("subtitle", ""),
                "docTitle": C["board"].get("docTitle") or C["board"]["title"],
            },
            "bands": C["bands"],
            "drift": ({"note": C["drift"].get("note", ""),
                       "linkLabel": C["drift"].get("linkLabel", ""),
                       "href": C["drift"].get("href", "#")} if C["drift"] else None),
            "honesty": C["honesty"],
        },
        "text": C["text"],
        "axis": axis,
        "m": m,
    }
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        template = fh.read()
    if template.count(MARKER) != 1:
        raise SystemExit(f"템플릿이 손상됐습니다 — 주입 지점 {MARKER!r}이 정확히 1개가 아닙니다: "
                         f"{TEMPLATE_PATH}")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # <script> 안에 </script>나 HTML 주석 시작이 그대로 들어가면 문서가 잘린다.
    blob = blob.replace("</", "<\\/").replace("<!--", "<\\!--")
    return template.replace(MARKER, blob), m


# ══════════════════════════════════════════════════════════════════════════
# 5. 진입점
# ══════════════════════════════════════════════════════════════════════════

def load_json(path, what):
    if not os.path.exists(path):
        raise SystemExit(f"{what} 파일을 찾을 수 없습니다: {path}")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{what} 파일이 올바른 JSON이 아닙니다: {path}\n  {exc}")


def report_errors(errors):
    print(f"통합 현황판 엔진 — 검증 실패 {len(errors)}건. 아무 것도 렌더하지 않았습니다.",
          file=sys.stderr)
    for i, (path, message, hint) in enumerate(errors, 1):
        print(f"  {i}. {path}: {message}", file=sys.stderr)
        if hint:
            print(f"       └ {hint}", file=sys.stderr)
    print("\n스키마 정본: reference/board-schema.md", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="config + data → 고정 통합 현황판 HTML (외부 의존 0)")
    ap.add_argument("--config", default=os.path.join(HERE, "board.config.example.json"),
                    help="프로젝트 config (기본: 번들된 예시)")
    ap.add_argument("--data", default=os.path.join(HERE, "board.example.json"),
                    help="이번 회차 data (기본: 번들된 예시)")
    ap.add_argument("--out", default="integration-board.html", help="산출 HTML 경로")
    args = ap.parse_args(argv)

    raw_cfg = load_json(args.config, "config")
    raw_data = load_json(args.data, "data")

    v = Validator()
    C = validate_config(v, raw_cfg)
    D = validate_data(v, raw_data, C) if C else None
    if v.errors or C is None or D is None:
        report_errors(v.errors or [("config", "읽을 수 없습니다", None)])
        return 2

    html, m = render(C, D)
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"통합 현황판을 만들었습니다 → {out}")
    print(f"  판정 {m['verdict']['word']} · 결정 필요 {m['decides']}건 · "
          f"작업 {len(m['byId'])}건(일정 미정 {len(m['undated'])}) · "
          f"공용 자산 {len(m['assets'])} · 자동 검사 {len(m['checks'])} · "
          f"{len(html.encode('utf-8')):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
