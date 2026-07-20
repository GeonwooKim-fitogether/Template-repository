#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────────
// 인증된 QA 세션 발급기 — 테스트 유저로 로그인해 Playwright storageState 를 만든다.
//
// 무엇을/왜: QA 스웜의 L2(정상 흐름을 깊게 공격)와 권한·쓰기 검증은 "로그인된 상태"
//   에서만 돈다. 이 스크립트는 사람이 매번 로그인 화면을 통과하지 않아도 되도록,
//   테스트 유저의 세션을 한 번 받아 **Playwright 가 그대로 물고 시작하는 storageState
//   파일**(로그인 쿠키를 담아 재사용하는 저장 상태)로 떨궈 둔다. qa-contract.md 가
//   "사람이 공급하는 유일한 것 = 인증 셋업 스크립트"라 부르는 그 스크립트의 구현이다.
//
// 어떻게: 쿠키 이름·인코딩·청킹을 손으로 흉내 내지 않는다. **검증 대상 앱이 실제로
//   쓰는 그 @supabase/ssr 라이브러리**(APP_DIR 의 node_modules)를 그대로 불러
//   signInWithPassword → 세션을 쿠키로 직렬화시키고, 그 쿠키를 storageState 로 옮긴다.
//   같은 라이브러리로 쓰고 앱이 같은 라이브러리로 읽으므로 형식이 어긋날 수 없다.
//
// 필요 환경변수 (비밀은 env 로만 — 저장소·로그에 남기지 않는다):
//   QA_SUPABASE_URL       (없으면 NEXT_PUBLIC_SUPABASE_URL)     테스트 프로젝트 URL
//   QA_SUPABASE_ANON_KEY  (없으면 NEXT_PUBLIC_SUPABASE_ANON_KEY) 공개(anon) 키
//   QA_TEST_EMAIL / QA_TEST_PASSWORD                            테스트 유저 자격증명
//   QA_APP_ORIGIN   (기본 http://localhost:3100)  쿠키를 심을 앱 주소(도메인·secure 판정)
//   QA_APP_DIR      (기본 cwd)                     @supabase/ssr 를 해석해 올 앱 디렉터리
//   QA_STATE_OUT    (기본 <QA_APP_DIR>/e2e/.auth/qa-state.json)  storageState 출력 경로
//
// 출력: storageState 파일을 쓰고, 인증된 이메일·쿠키 이름·만료만 출력한다(토큰 미출력).
// 실패: 자격증명 미설정·로그인 거부·이메일로그인 비활성 등은 사유를 찍고 exit 1.
//
// ⚠ 산출된 storageState 는 실제 세션 토큰을 담은 **비밀**이다. 커밋 금지(.auth/ gitignore).
// ─────────────────────────────────────────────────────────────────────────
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

function fail(msg) { console.error(`[mint-auth-state] ✗ ${msg}`); process.exit(1); }

const URL_ = process.env.QA_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const ANON = process.env.QA_SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const EMAIL = process.env.QA_TEST_EMAIL;
const PASSWORD = process.env.QA_TEST_PASSWORD;
const APP_ORIGIN = process.env.QA_APP_ORIGIN || "http://localhost:3100";
const APP_DIR = process.env.QA_APP_DIR || process.cwd();
const OUT = process.env.QA_STATE_OUT || path.join(APP_DIR, "e2e", ".auth", "qa-state.json");

if (!URL_ || !ANON) fail("QA_SUPABASE_URL/QA_SUPABASE_ANON_KEY (또는 NEXT_PUBLIC_*) 가 없습니다.");
if (!EMAIL || !PASSWORD) fail("QA_TEST_EMAIL/QA_TEST_PASSWORD 가 없습니다.");

// 검증 대상 앱의 @supabase/ssr 를 그 앱 node_modules 에서 해석해 온다.
let createServerClient;
try {
  const req = createRequire(path.join(APP_DIR, "package.json"));
  ({ createServerClient } = await import(pathToFileURL(req.resolve("@supabase/ssr")).href));
} catch (e) {
  fail(`@supabase/ssr 를 APP_DIR(${APP_DIR}) 에서 찾지 못했습니다. QA_APP_DIR 를 앱 폴더로 지정하세요. (${e.message})`);
}

// 인메모리 쿠키 항아리 — ssr 이 세션을 여기에 직렬화한다.
const jar = new Map();
const supabase = createServerClient(URL_, ANON, {
  cookies: {
    getAll() { return [...jar.entries()].map(([name, value]) => ({ name, value })); },
    setAll(list) { for (const c of list) jar.set(c.name, c.value); },
  },
});

const { data, error } = await supabase.auth.signInWithPassword({ email: EMAIL, password: PASSWORD });
if (error) {
  // 흔한 원인을 사람 말로 풀어 준다.
  const m = error.message || String(error);
  let hint = "";
  if (/invalid login credentials/i.test(m)) hint = " — 유저가 없거나 비번이 틀렸습니다. authenticated-session.md 의 1회 프로비저닝을 먼저 하세요.";
  else if (/email logins are disabled|email provider/i.test(m)) hint = " — 테스트 프로젝트에서 Email(비밀번호) 인증이 꺼져 있습니다. Authentication > Providers 에서 켜세요.";
  else if (/email not confirmed/i.test(m)) hint = " — 유저 이메일이 미확인 상태입니다. email_confirm=true 로 프로비저닝하세요.";
  fail(`로그인 실패: ${m}${hint}`);
}
if (!data?.session) fail("로그인은 됐으나 세션이 없습니다(이메일 확인 대기일 수 있음).");
if (jar.size === 0) fail("세션 쿠키가 만들어지지 않았습니다(@supabase/ssr 버전 확인).");

// storageState 쿠키로 변환. 도메인·secure 는 앱 주소에서 판정.
const origin = new global.URL(APP_ORIGIN);
const secure = origin.protocol === "https:";
const expires = (data.session.expires_at ?? Math.floor(Date.now() / 1000) + 3600) + 7 * 24 * 3600;
const cookies = [...jar.entries()].map(([name, value]) => ({
  name, value,
  domain: origin.hostname,
  path: "/",
  expires,
  httpOnly: true,
  secure,
  sameSite: "Lax",
}));

mkdirSync(path.dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({ cookies, origins: [] }, null, 2));

console.log(`[mint-auth-state] ✓ 인증 세션 발급 완료`);
console.log(`  user     : ${data.session.user?.email}`);
console.log(`  cookies  : ${cookies.map((c) => c.name).join(", ")}  (domain=${origin.hostname}, secure=${secure})`);
console.log(`  state    : ${OUT}   ← Playwright storageState (비밀: 커밋 금지)`);
