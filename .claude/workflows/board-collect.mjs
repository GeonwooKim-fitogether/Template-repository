#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────────────
// 통합 현황판 사실 수집기 — GitHub의 사실을 board.json 으로 옮긴다.
//
// 왜 이 스크립트가 있나. 현황판은 "고정 엔진 + 프로젝트 config + 회차 data" 세 겹이고,
// 그중 사람이 채우던 것은 data 하나였다. 그런데 data 가 요구하는 사실의 대부분은
// 이미 GitHub 에 있다 — 열린 PR 이 무엇이고, 무엇이 충돌났고, 며칠째 멈췄고,
// 어떤 검사가 돌아 무엇이 실패했는지. 사람이 그것을 손으로 옮겨 적는 동안 보드는
// 늘 하루쯤 낡아 있었고, 옮겨 적다 틀리기도 했다.
//
// 그래서 옮기는 일을 이 스크립트가 맡는다. 사건이 생길 때마다(PR 검사 완료·main 푸시·
// 30분 심장박동) 워크플로가 이것을 돌려 board.json 을 다시 쓰고, 엔진이 보드를 다시 그린다.
//
// ── 이 스크립트가 지키는 두 가지 규율 ────────────────────────────────────────
//
// 1. **모르는 것을 지어내지 않는다.** GitHub 에 없는 사실(계획 시작·종료일, 진척률,
//    해소 작업)은 비워 둔다. 엔진은 비어 있는 축을 초록이 아니라 회색 "알 수 없다"로
//    그리므로, 자동 수집 보드는 모르는 것을 안다고 말하지 않는다. 채우고 싶으면
//    PR 본문에 한 줄로 선언한다(아래 '본문 선언' 참고).
//
// 2. **말 없이 넘기지 않는다.** 대응표에 없는 작성자·경로를 만나면 기본값으로 넘기되,
//    무엇을 몇 건 그렇게 처리했는지 마지막에 요약으로 남긴다. 조용한 기본값은
//    "다 대응됐다"로 오해되기 때문이다.
//
// ── 무엇을 자동으로 채우나 ───────────────────────────────────────────────────
//   작업 목록·제목·상태 ← 열린 PR + 최근 머지된 PR
//   막힘(충돌/대기)      ← PR 의 머지 가능 상태, 리뷰어 지정 여부
//   며칠째 멈췄나        ← PR 의 마지막 갱신 시각
//   실제 완료일          ← 머지 시각
//   건드린 공용 자산     ← 변경 파일 경로 → 자산 대응표
//   제품 영역·팀         ← 변경 파일 경로 → 영역 대응표, 작성자 → 팀 대응표
//   검사 실행 결과       ← main 최신 커밋의 체크 실행 결과 (체크 이름 = 잡 이름)
//   위반 목록            ← 실패한 체크 (main 은 지목 없는 위반, PR 은 그 PR 을 지목)
//
// ── PR 본문 선언 (선택) ──────────────────────────────────────────────────────
// PR 본문 어디든 아래 한 줄을 적으면 그 값이 보드에 올라간다. 안 적으면 회색으로 남는다.
//   계획: 2026-08-01..2026-08-14      (Plan: 도 받는다)
//   진척: 40%                          (Progress: 도 받는다)
//   해소: 척추가드, 문서매트릭스        (Fixes-check: 도 받는다 — config.checks 의 key)
//
// ── 사람이 선언한 사실을 얹는 층 (board.manual.json) ─────────────────────────
// GitHub 에 아예 없는 사실이 있다. PR 을 아직 열지 않은 **브랜치 작업**, 사람이 감사로
// 판정한 **위반**(척추 규칙 위반·행 수준 보안 같은 것 — 이런 것은 CI 가 실패로 알려 주지
// 않는다), 그리고 기계가 모르는 **검사 결과**다. 이것을 못 담으면 자동 수집으로 바꾼 순간
// 그 사실들이 보드에서 사라지고, 사라진 만큼 판정이 좋아 보인다. **거짓 초록불**이다.
//
// 그래서 `.integration/board.manual.json` 이 있으면 수집한 사실 위에 얹는다.
// 모양은 board.json 과 같고 일부만 적으면 된다.
//
//   { "works": [...], "violations": [...], "checkRuns": {...}, "drift": {...} }
//
//   · works      — id 가 수집된 PR 과 같으면 **적은 항목만 덮어쓴다**(예: 계획일·진척률을
//                  PR 본문 대신 여기서 주기). 없는 id 면 새 작업으로 더한다.
//   · violations — 수집된 것에 **더한다**(같은 것은 한 번만).
//   · checkRuns  — 사람이 적은 쪽이 이긴다. 기계가 보지 못하는 검사를 여기서 채운다.
//   · drift      — 기계가 셀 수 없는 값이라 여기서만 온다.
//
// ── 실행 ─────────────────────────────────────────────────────────────────────
//   node .claude/workflows/board-collect.mjs                     (GitHub 에서 수집)
//   node .claude/workflows/board-collect.mjs --fixture f.json    (녹여 둔 응답으로 수집)
//   옵션: --out <경로>(기본 .integration/board.json) --config <경로> --map <경로>
//         --manual <경로>(기본 .integration/board.manual.json — 없으면 그냥 건너뛴다)
//
// 환경변수: GITHUB_TOKEN, GITHUB_REPOSITORY(=owner/repo). Actions 가 둘 다 준다.
// 준비물 없음 — Node 18+ 의 fetch 만 쓴다.
// ─────────────────────────────────────────────────────────────────────────────

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const argv = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};

const CONFIG_PATH = opt("--config", ".integration/board.config.json");
const MAP_PATH = opt("--map", ".integration/board.map.json");
const OUT_PATH = opt("--out", ".integration/board.json");
const MANUAL_PATH = opt("--manual", ".integration/board.manual.json");
const FIXTURE = opt("--fixture", null);

const DAY = 86400000;

// ── 대응표 기본값 ────────────────────────────────────────────────────────────
// 모두 프로젝트가 board.map.json 으로 덮어쓴다. 여기 값은 "적지 않았을 때의 뜻"이다.
const MAP_DEFAULTS = {
  timezone: "Asia/Seoul",   // '오늘'을 어느 시간대로 볼지. 팀이 있는 곳 기준이 맞다.
  recentMergedDays: 14,     // 며칠 안에 머지된 것까지 보드에 남길지
  statusOf: {},             // {draft|open|merged: config.statuses 의 key}
  workIdPrefix: "PR-",      // 작업 id 접두어. 저장소의 기존 표기(예: 'pr-')를 따를 수 있다.
  teamByAuthor: {},
  teamByArea: {},           // {영역 key: 팀}. 팀이 사람이 아니라 '파트'인 저장소를 위한 것.
  teamDefault: null,
  areaByPath: [],           // [[glob, area], ...] 위에서부터 처음 맞는 것
  areaDefault: null,
  assetByPath: [],          // [[glob, asset], ...] 맞는 것 전부
  checkByRun: {},           // {체크 이름 = 워크플로의 잡(job) 이름: config.checks 의 key}
  severityByCheck: {},      // {check key: "block"|"warn"} 기본은 아래 두 상수
  mainSeverity: "block",    // main 에서 실패한 검사의 무게 — 저장소가 그 상태다
  prSeverity: "warn",       // PR 에서 실패한 검사의 무게 — 아직 본선에 들어오지 않았다
};

function die(msg) {
  console.error("수집 실패: " + msg);
  process.exit(2);
}

function loadJson(path, what) {
  if (!existsSync(path)) die(`${what}를 찾을 수 없습니다: ${path}`);
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    die(`${what}가 올바른 JSON 이 아닙니다: ${path} — ${e.message}`);
  }
}

// ── 경로 glob — `**` 와 `*` 만 받는다. 그 이상은 필요한 적이 없었다 ──────────
function globToRe(glob) {
  let out = "^";
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === "*") {
      if (glob[i + 1] === "*") { out += ".*"; i++; if (glob[i + 1] === "/") i++; }
      else out += "[^/]*";
    } else if (".+?^${}()|[]\\".includes(c)) out += "\\" + c;
    else out += c;
  }
  return new RegExp(out + "$");
}

const matchers = new Map();
const matches = (glob, path) => {
  if (!matchers.has(glob)) matchers.set(glob, globToRe(glob));
  return matchers.get(glob).test(path);
};

// ── GitHub 에서 읽기 ─────────────────────────────────────────────────────────
class GitHub {
  constructor(repo, token) {
    this.repo = repo;
    this.token = token;
  }
  async get(path) {
    const res = await fetch(`https://api.github.com${path}`, {
      headers: {
        authorization: `Bearer ${this.token}`,
        accept: "application/vnd.github+json",
        "user-agent": "integration-board-collect",
      },
    });
    if (!res.ok) die(`GitHub 응답 ${res.status} — ${path}\n${(await res.text()).slice(0, 400)}`);
    return res.json();
  }
  openPulls() { return this.get(`/repos/${this.repo}/pulls?state=open&per_page=100`); }
  closedPulls() {
    return this.get(`/repos/${this.repo}/pulls?state=closed&sort=updated&direction=desc&per_page=50`);
  }
  // 목록 응답에는 mergeable_state 와 본문이 없거나 부실하다. 충돌 여부와 본문 선언을
  // 보려면 PR 하나하나를 따로 읽어야 한다(열린 PR 은 보통 몇 개뿐이라 부담이 없다).
  pull(n) { return this.get(`/repos/${this.repo}/pulls/${n}`); }
  files(n) { return this.get(`/repos/${this.repo}/pulls/${n}/files?per_page=100`); }
  checkRuns(ref) {
    return this.get(`/repos/${this.repo}/commits/${ref}/check-runs?per_page=100`)
      .then(r => r.check_runs || []);
  }
  defaultBranchHead() {
    return this.get(`/repos/${this.repo}`).then(r => r.default_branch);
  }
}

// ── 녹여 둔 응답으로 읽기 — 네트워크 없이 같은 결과를 확인하기 위한 것 ───────
class Fixture {
  constructor(data) { this.d = data; }
  async openPulls() { return this.d.openPulls || []; }
  async closedPulls() { return this.d.closedPulls || []; }
  async pull(n) { return (this.d.pull || {})[n] || die(`녹여 둔 응답에 PR ${n} 이 없습니다`); }
  async files(n) { return (this.d.files || {})[n] || []; }
  async checkRuns(ref) { return (this.d.checkRuns || {})[ref] || []; }
  async defaultBranchHead() { return this.d.defaultBranch || "main"; }
}

// ── PR 본문 선언 ─────────────────────────────────────────────────────────────
// 사람이 적어야만 알 수 있는 세 가지를 본문에서 읽는다. 없으면 없는 대로 둔다.
function parseDeclarations(body) {
  const out = {};
  const text = body || "";
  const plan = text.match(/(?:계획|Plan)\s*[:：]\s*(\d{4}-\d{2}-\d{2})\s*\.\.\s*(\d{4}-\d{2}-\d{2})/i);
  if (plan) { out.planStart = plan[1]; out.planEnd = plan[2]; }
  const prog = text.match(/(?:진척|Progress)\s*[:：]\s*(\d{1,3})\s*%/i);
  if (prog) out.progress = Math.min(100, parseInt(prog[1], 10));
  const fix = text.match(/(?:해소|Fixes-check)\s*[:：]\s*([^\n\r]+)/i);
  if (fix) {
    out.fixes = fix[1].split(/[,·]/).map(s => s.trim()).filter(Boolean);
  }
  return out;
}

function ymd(iso, tz) {
  // 시간대를 옮겨 '그 곳의 날짜'를 얻는다. Intl 은 Node 표준에 들어 있다.
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz }).format(new Date(iso));
}

async function main() {
  const cfg = loadJson(CONFIG_PATH, "보드 config");
  const map = { ...MAP_DEFAULTS, ...loadJson(MAP_PATH, "수집 대응표") };

  const areaKeys = new Set((cfg.areas || []).map(a => a.key));
  const statusKeys = new Set((cfg.statuses || []).map(s => s.key));
  const assetKeys = new Set((cfg.assets || []).map(a => a.key));
  const checkKeys = new Set((cfg.checks || []).map(c => c.key));
  const teamRoster = cfg.teams || null;

  // 대응표가 config 에 없는 것을 가리키면 여기서 멈춘다. 보드가 만들어진 뒤
  // 엔진이 거부하는 것보다, 무엇이 어긋났는지 이름을 대며 먼저 멈추는 편이 낫다.
  const bad = [];
  for (const [k, v] of Object.entries(map.statusOf))
    if (!statusKeys.has(v)) bad.push(`statusOf.${k} → 없는 상태 '${v}'`);
  for (const [, v] of map.areaByPath) if (!areaKeys.has(v)) bad.push(`areaByPath → 없는 영역 '${v}'`);
  for (const k of Object.keys(map.teamByArea)) if (!areaKeys.has(k)) bad.push(`teamByArea 의 열쇠 '${k}' 는 없는 영역입니다`);
  if (map.areaDefault && !areaKeys.has(map.areaDefault)) bad.push(`areaDefault → 없는 영역 '${map.areaDefault}'`);
  for (const [, v] of map.assetByPath) if (!assetKeys.has(v)) bad.push(`assetByPath → 없는 자산 '${v}'`);
  for (const [k, v] of Object.entries(map.checkByRun))
    if (!checkKeys.has(v)) bad.push(`checkByRun['${k}'] → 없는 검사 '${v}'`);
  if (teamRoster) {
    for (const [k, v] of Object.entries(map.teamByAuthor))
      if (!teamRoster.includes(v)) bad.push(`teamByAuthor['${k}'] → 명부에 없는 팀 '${v}'`);
    for (const [k, v] of Object.entries(map.teamByArea)) {
      if (!teamRoster.includes(v)) bad.push(`teamByArea['${k}'] → 명부에 없는 팀 '${v}'`);
    }
    if (map.teamDefault && !teamRoster.includes(map.teamDefault))
      bad.push(`teamDefault → 명부에 없는 팀 '${map.teamDefault}'`);
  }
  for (const need of ["draft", "open", "merged"])
    if (!map.statusOf[need]) bad.push(`statusOf.${need} 가 없습니다 — PR 의 이 상태를 어느 열에 놓을지 정해야 합니다`);
  if (!map.areaDefault) bad.push("areaDefault 가 없습니다 — 경로 대응에 걸리지 않는 PR 을 어느 영역에 둘지 정해야 합니다");
  if (!map.teamDefault) bad.push("teamDefault 가 없습니다 — 대응표에 없는 작성자를 어느 팀으로 볼지 정해야 합니다");
  if (bad.length) die("대응표가 config 와 어긋납니다\n  - " + bad.join("\n  - "));

  const src = FIXTURE
    ? new Fixture(loadJson(FIXTURE, "녹여 둔 응답"))
    : new GitHub(process.env.GITHUB_REPOSITORY || die("GITHUB_REPOSITORY 가 없습니다"),
                 process.env.GITHUB_TOKEN || die("GITHUB_TOKEN 이 없습니다"));

  const tz = map.timezone;
  const now = Date.now();
  const notes = { unmappedAuthors: new Set(), unmappedPaths: 0, noPlan: 0, unmappedChecks: new Set() };

  // ── 작업 목록 ──────────────────────────────────────────────────────────────
  const open = await src.openPulls();
  const closed = await src.closedPulls();
  const merged = closed.filter(p => p.merged_at && now - Date.parse(p.merged_at) <= map.recentMergedDays * DAY);

  const works = [];
  const byNumber = new Map();

  for (const brief of [...open, ...merged]) {
    const n = brief.number;
    // 열린 PR 은 충돌 여부와 본문이 필요해 하나씩 다시 읽는다. 머지된 것은 목록만으로 족하다.
    const pr = brief.merged_at ? brief : await src.pull(n);
    const files = (await src.files(n)).map(f => f.filename);

    const area = (map.areaByPath.find(([g]) => files.some(f => matches(g, f))) || [])[1];
    if (!area) notes.unmappedPaths++;
    const author = (pr.user && pr.user.login) || "";
    const areaKey = area || map.areaDefault;
    // 팀은 세 단계로 정한다. 작성자 대응이 먼저이고, 없으면 영역 대응(팀이 사람이 아니라
    // '파트'인 저장소에서는 이쪽이 맞다), 그것도 없으면 기본값이다.
    const team = map.teamByAuthor[author] || map.teamByArea[areaKey];
    if (!map.teamByAuthor[author] && !map.teamByArea[areaKey] && author) notes.unmappedAuthors.add(author);

    const touches = [...new Set(
      map.assetByPath.filter(([g]) => files.some(f => matches(g, f))).map(([, a]) => a))];

    const decl = parseDeclarations(pr.body);
    const isMerged = Boolean(pr.merged_at);
    const status = isMerged ? map.statusOf.merged
      : pr.draft ? map.statusOf.draft : map.statusOf.open;

    const w = {
      id: `${map.workIdPrefix}${n}`,
      title: pr.title,
      area: areaKey,
      team: team || map.teamDefault,
      status,
    };
    if (touches.length) w.touches = touches;

    if (isMerged) {
      w.progress = 100;
      w.completedAt = ymd(pr.merged_at, tz);
      // 끝난 일은 시간 축에 실제 구간(요청 생성 → 머지)으로 올린다.
      // 계획이 아니라 실제이지만, 이미 끝난 일을 '일정 미정'으로 몰아 두면 두 가지가
      // 함께 망가진다 — 간트가 최근에 무엇이 나갔는지 보여 주지 못하고,
      // '언제 끝날지 모르는 일' 카드가 이미 끝난 일까지 세어 거짓 경보를 낸다.
      w.planStart = ymd(pr.created_at, tz);
      w.planEnd = w.completedAt;
    } else {
      // 충돌은 '깨끗하지 않다'가 아니라 '실제로 충돌났다'일 때만 붙인다.
      // GitHub 이 아직 계산 중이면(unknown) 아무 말도 하지 않는다.
      if (pr.mergeable_state === "dirty" || pr.mergeable === false) w.block = "conflict";
      else if ((pr.requested_reviewers || []).length) w.block = "waiting";
      const idle = Math.floor((now - Date.parse(pr.updated_at)) / DAY);
      if (Number.isFinite(idle)) w.stalledDays = Math.max(0, idle);
    }

    if (decl.planStart) { w.planStart = decl.planStart; w.planEnd = decl.planEnd; }
    else if (!isMerged) notes.noPlan++;
    if (decl.progress !== undefined) w.progress = decl.progress;
    if (decl.fixes) {
      const ok = decl.fixes.filter(k => checkKeys.has(k));
      const wrong = decl.fixes.filter(k => !checkKeys.has(k));
      if (wrong.length) die(`PR #${n} 의 '해소:' 선언이 없는 검사를 가리킵니다: ${wrong.join(", ")}\n`
        + `  쓸 수 있는 검사 key: ${[...checkKeys].join(", ")}`);
      if (ok.length) w.fixes = ok;
    }

    works.push(w);
    byNumber.set(n, { pr, work: w });
  }

  if (!works.length) die("열린 PR 도 최근 머지된 PR 도 없어 작업 목록이 빕니다 — 보드는 작업이 "
    + "최소 하나 있어야 만들어집니다. recentMergedDays 를 늘려 보십시오.");

  // ── 검사 실행 결과와 위반 ──────────────────────────────────────────────────
  // 검사의 '이번 회차 결과'는 main 최신 커밋의 체크에서 읽는다. 그것이 저장소의 현재 상태다.
  const mainRef = await src.defaultBranchHead();
  const mainRuns = await src.checkRuns(mainRef);

  // GitHub이 체크의 이름으로 주는 것은 워크플로 이름이 아니라 **잡(job) 이름**이다.
  // 실제 응답을 확인해 알아낸 사실이다 — 예: 'PR 크로스컷 게이트'가 아니라 'gate'.
  // 그래서 대응표의 열쇠는 워크플로 파일의 `jobs:` 아래 키다. 워크플로 파일명이나
  // 표시 이름을 적어 둔 항목도 함께 받아 준다(해가 없고, 사람이 그렇게 적기 쉽다).
  const keyOfRun = (run) => {
    const cands = [run.name];
    const wf = (run.check_suite && run.check_suite.workflow && run.check_suite.workflow.path) || "";
    if (wf) cands.push(wf, wf.split("/").pop());
    for (const c of cands) {
      if (c && map.checkByRun[c]) return map.checkByRun[c];
    }
    if (run.name) notes.unmappedChecks.add(run.name);
    return null;
  };

  let manualDrift = null;
  const FAIL = new Set(["failure", "timed_out", "action_required", "startup_failure"]);
  const checkRuns = {};
  const violations = [];
  const seen = new Set();
  const addViolation = (check, ref, severity) => {
    const k = `${check}|${ref || ""}|${severity}`;
    if (seen.has(k)) return;
    seen.add(k);
    const v = { check, severity };
    if (ref) v.ref = ref;
    violations.push(v);
  };

  for (const run of mainRuns) {
    const key = keyOfRun(run);
    if (!key) continue;
    if (run.status !== "completed") continue;         // 아직 도는 중인 것은 결과가 아니다
    if (run.conclusion === "success") checkRuns[key] = checkRuns[key] || "pass";
    else if (run.conclusion === "skipped") checkRuns[key] = checkRuns[key] || "skipped";
    else if (FAIL.has(run.conclusion)) {
      checkRuns[key] = "fail";
      addViolation(key, null, map.severityByCheck[key] || map.mainSeverity);
    }
  }
  // main 에서 한 번도 결과가 안 잡힌 검사는 적지 않는다 — 엔진이 회색 '정보 없음'으로 둔다.

  for (const [n, { pr }] of byNumber) {
    if (pr.merged_at) continue;
    const runs = await src.checkRuns(pr.head && pr.head.sha ? pr.head.sha : `refs/pull/${n}/head`);
    for (const run of runs) {
      if (run.status !== "completed" || !FAIL.has(run.conclusion)) continue;
      const key = keyOfRun(run);
      if (!key) continue;
      addViolation(key, `${map.workIdPrefix}${n}`, map.severityByCheck[key] || map.prSeverity);
    }
  }

  // ── 사람이 선언한 사실을 얹는다 ────────────────────────────────────────────
  // 기계가 볼 수 없는 것(PR 없는 브랜치 작업, 감사로 판정한 위반, 기계가 모르는 검사)을
  // 여기서 받는다. 이 층이 없으면 자동 수집으로 바꾼 순간 그 사실들이 조용히 사라지고,
  // 사라진 만큼 판정이 좋아 보인다.
  let manualNote = null;
  if (existsSync(MANUAL_PATH)) {
    const man = loadJson(MANUAL_PATH, "사람이 선언한 사실");
    // `_`로 시작하는 열쇠는 주석으로 본다 — 이 저장소의 설정 파일들이 쓰는 관례이고,
    // 사람이 손으로 채우는 파일일수록 "이 칸이 무엇인지"를 파일 안에 적어 둘 자리가 필요하다.
    const allowed = new Set(["works", "violations", "checkRuns", "drift"]);
    const extra = Object.keys(man).filter(k => !allowed.has(k) && !k.startsWith("_"));
    if (extra.length) die(`${MANUAL_PATH} 에 얹을 수 없는 항목이 있습니다: ${extra.join(", ")}\n`
      + `  얹을 수 있는 것: works · violations · checkRuns · drift`);

    const byId = new Map(works.map(w => [w.id, w]));
    let over = 0, added = 0;
    for (const mw of man.works || []) {
      if (!mw || typeof mw.id !== "string") die(`${MANUAL_PATH} 의 works 항목에 id 가 없습니다`);
      const cur = byId.get(mw.id);
      if (cur) { Object.assign(cur, mw); over++; }   // 적은 항목만 덮어쓴다
      else { works.push(mw); byId.set(mw.id, mw); added++; }
    }
    // 사람이 적은 위반은 **중복 제거 없이 그대로** 싣는다.
    //
    // 기계가 모은 위반에는 중복 제거가 맞다(같은 검사가 여러 실행에서 같은 실패를 보고한다).
    // 그런데 사람이 감사로 찾은 발견은 검사·지목·무게가 똑같아도 **서로 다른 건**이다.
    // 실제로 이 저장소에는 척추 가드 위반이 셋(막힘 둘·주의 하나), 행 수준 보안이 둘 있었는데,
    // 중복 제거를 걸었더니 셋이 둘로, 둘이 하나로 줄었다. 보드가 문제를 실제보다 작게
    // 말하게 되므로 — 이 도구가 없애려는 바로 그 방향이므로 — 얹는 층에서는 걸지 않는다.
    for (const mv of man.violations || []) {
      const v = { check: mv.check, severity: mv.severity };
      if (mv.ref) v.ref = mv.ref;
      violations.push(v);
    }
    for (const [k, v] of Object.entries(man.checkRuns || {})) checkRuns[k] = v;  // 사람이 이긴다
    if (man.drift) manualDrift = man.drift;
    manualNote = `사람이 선언한 사실을 얹었습니다 — 작업 추가 ${added}건 · 기존 작업 보강 ${over}건`
      + ` · 위반 ${(man.violations || []).length}건 · 검사 결과 ${Object.keys(man.checkRuns || {}).length}개`;
  }

  // 걸린 것이 있는 검사는 '통과'로 보고할 수 없다.
  //
  // 처음에는 main 의 결과를 그대로 두고 PR 의 실패만 위반으로 올렸는데, main 에서 통과한
  // 검사가 어떤 PR 에서 실패하면 "통과인데 위반 1건"이라는 앞뒤가 안 맞는 회차가 나왔다.
  // 엔진이 그것을 거부하며 알려 준 문제다. 스키마의 뜻을 따르면 답은 분명하다 —
  // 위반은 "이 회차에 이 선이 걸렸다"는 사실이고, 그러면 그 검사의 이번 회차 결과는
  // 통과가 아니다. main 의 통과는 사라지지 않는다. 검사 칸에 걸린 PR 이 이름으로 남아,
  // 본선이 아니라 들어오려는 것이 걸렸다는 사실이 그 자리에서 읽힌다.
  for (const v of violations) checkRuns[v.check] = "fail";

  // ── board.json ─────────────────────────────────────────────────────────────
  const data = {
    today: ymd(new Date(now).toISOString(), tz),
    updated: new Intl.DateTimeFormat("sv-SE", {
      timeZone: tz, dateStyle: "short", timeStyle: "short",
    }).format(new Date(now)).replace("T", " "),
    works,
  };
  if (violations.length) data.violations = violations;
  if (Object.keys(checkRuns).length) data.checkRuns = checkRuns;
  if (manualDrift) data.drift = manualDrift;

  mkdirSync(dirname(OUT_PATH), { recursive: true });
  writeFileSync(OUT_PATH, JSON.stringify(data, null, 2) + "\n", "utf8");

  // ── 요약 — 못 채운 것을 말한다 ─────────────────────────────────────────────
  console.log(`board.json 을 썼습니다 → ${OUT_PATH}`);
  console.log(`  작업 ${works.length}건(열림 ${open.length} · 최근 머지 ${merged.length})`
    + ` · 위반 ${violations.length}건 · 검사 결과 ${Object.keys(checkRuns).length}개`);
  if (manualNote) console.log("  " + manualNote);
  const say = [];
  if (notes.noPlan) say.push(`계획일 미선언 ${notes.noPlan}건 → 간트의 '일정 미정' 그룹으로 갑니다`);
  if (notes.unmappedPaths) say.push(`경로 대응 없음 ${notes.unmappedPaths}건 → areaDefault('${map.areaDefault}')로 두었습니다`);
  if (notes.unmappedAuthors.size) say.push(`작성자 대응 없음: ${[...notes.unmappedAuthors].join(", ")} → teamDefault('${map.teamDefault}')로 두었습니다`);
  if (notes.unmappedChecks.size) say.push(`대응표에 없는 체크: ${[...notes.unmappedChecks].join(", ")} → 보드에 싣지 않았습니다`);
  if (!works.some(w => w.fixes)) say.push("해소 작업 선언 없음 → 걸린 검사는 '해소 작업 미보고'(회색)로 나옵니다");
  if (say.length) {
    console.log("  채우지 못한 것:");
    for (const s of say) console.log(`    · ${s}`);
  }
}

main().catch(e => die(e && e.stack ? e.stack : String(e)));
