#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────────
// 인증 쓰기 검증 — mint-auth-state 로 만든 세션이 "정말 쓰기까지 되는" 세션인지 증명한다.
//
// 왜: 세션을 주입해 로그인 화면을 건너뛰는 것만으로는 부족하다. 그 세션의 유저가
//   실제로 DB 에 쓸 권한(RLS)이 있어야 QA 가 작성 흐름(생성→편집→제출…)을 태울 수
//   있다. 이 스크립트는 storageState 를 물고 앱을 인증 상태로 연 뒤, **브라우저로
//   실제 쓰기 1건(여기선 Change/ECO 생성)** 을 수행해 저장되는 것을 눈으로 확인한다.
//   이것이 통과하면 "표시는 되나 작성이 안 된다"류 회귀를 스웜 전에 차단할 수 있다.
//
// 전제: 앱이 **테스트 프로젝트로 향한 채** 이미 떠 있어야 한다(QA_APP_ORIGIN). 즉
//   NEXT_PUBLIC_SUPABASE_URL/ANON_KEY 를 테스트 프로젝트로 두고 dev 서버를 띄운 뒤,
//   같은 자격증명으로 mint-auth-state 를 돌려 QA_STATE_OUT 을 만들어 두고 실행한다.
//
// 필요 환경변수:
//   QA_APP_ORIGIN (기본 http://localhost:3100)  떠 있는 앱 주소
//   QA_STATE_OUT  (기본 <QA_APP_DIR>/e2e/.auth/qa-state.json)  storageState 경로
//   QA_APP_DIR    (기본 cwd)  @playwright/test 를 해석해 올 앱 디렉터리
//   PLAYWRIGHT_BROWSERS_PATH (선택)  미리 설치된 chromium 재사용
//
// 결과: 인증 확인 + 쓰기 성공이면 exit 0. /login 으로 튕기거나 쓰기가 저장 안 되면 exit 1.
// ─────────────────────────────────────────────────────────────────────────
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";

function fail(msg) { console.error(`[auth-write-check] ✗ ${msg}`); process.exit(1); }

const APP_ORIGIN = process.env.QA_APP_ORIGIN || "http://localhost:3100";
const APP_DIR = process.env.QA_APP_DIR || process.cwd();
const STATE = process.env.QA_STATE_OUT || path.join(APP_DIR, "e2e", ".auth", "qa-state.json");
if (!existsSync(STATE)) fail(`storageState 가 없습니다: ${STATE} — 먼저 mint-auth-state.mjs 를 실행하세요.`);

let chromium;
try {
  const req = createRequire(path.join(APP_DIR, "package.json"));
  ({ chromium } = await import(pathToFileURL(req.resolve("@playwright/test")).href));
} catch (e) {
  fail(`@playwright/test 를 APP_DIR(${APP_DIR}) 에서 못 찾음. QA_APP_DIR 지정 필요. (${e.message})`);
}

// playwright.config 와 같은 규약으로 미리 설치된 chromium 을 재사용(있으면).
function prebuiltChrome() {
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH;
  if (!base) return undefined;
  try {
    const dir = readdirSync(base).find((d) => d.startsWith("chromium-"));
    const p = dir && `${base}/${dir}/chrome-linux/chrome`;
    return p && existsSync(p) ? p : undefined;
  } catch { return undefined; }
}
const executablePath = prebuiltChrome();

const browser = await chromium.launch(executablePath ? { executablePath } : {});
const ctx = await browser.newContext({ storageState: STATE });
const page = await ctx.newPage();
let ok = false;
try {
  // 1) 인증 확인 — /changes 로 갔을 때 /login 으로 튕기지 않아야 한다.
  await page.goto(`${APP_ORIGIN}/changes`, { waitUntil: "networkidle" });
  if (/\/login/.test(new URL(page.url()).pathname)) fail("인증 실패 — /login 으로 리다이렉트됨(세션 미주입/만료).");
  console.log(`[auth-write-check] · 인증 상태 확인 OK (${page.url()})`);

  // 2) 실제 쓰기 — 생성 마법사로 Change(ECO) 1건 생성.
  const title = `QA-WRITE-CHECK ${new Date().toISOString()}`;
  await page.goto(`${APP_ORIGIN}/changes/new`, { waitUntil: "networkidle" });
  await page.getByLabel("제목").fill(title);
  // 3단계 마법사: 다음 → 다음 → 제출. 버튼이 보이는 대로 눌러 마지막까지 진행.
  for (let i = 0; i < 3; i++) {
    const next = page.getByRole("button", { name: /다음/ });
    if (await next.isVisible().catch(() => false)) { await next.click(); await page.waitForTimeout(300); }
    else break;
  }
  const submit = page.getByRole("button", { name: /제출/ });
  if (!(await submit.isVisible().catch(() => false))) fail("제출 버튼에 도달하지 못함(마법사 단계 변경 가능 — 셀렉터 확인).");
  await submit.click();

  // 3) 저장 확인 — 상세로 이동(URL 에 ECO-)하고 제목이 보이면 성공.
  await page.waitForURL(/\/changes\/ECO-/, { timeout: 15000 }).catch(() => {});
  const onDetail = /\/changes\/ECO-/.test(page.url());
  const titleShown = await page.getByText(title, { exact: false }).first().isVisible().catch(() => false);
  if (!onDetail && !titleShown) fail(`쓰기 저장 확인 실패 — 현재 URL=${page.url()}`);
  console.log(`[auth-write-check] ✓ PASS — 인증 상태에서 Change 생성 저장 확인 (${page.url()})`);
  ok = true;
} finally {
  await browser.close();
}
process.exit(ok ? 0 : 1);
