#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────────
// mint-auth-state 의 오프라인 자기검증 — "세션 주입" 배관이 맞는지 network 없이 증명한다.
//
// 왜: mint-auth-state 의 핵심이자 가장 깨지기 쉬운 부분은 "세션을 앱이 읽을 수 있는
//   쿠키로 옮기는 것"이다. 이 쿠키의 이름·base64 인코딩·청킹은 @supabase/ssr 버전에
//   묶여 있어, 손으로 흉내 내면 언제든 어긋난다. 이 테스트는 실제 앱의 @supabase/ssr
//   로 (1) 합성 세션을 쿠키로 쓰고 → (2) 그 쿠키를 새 클라이언트로 읽어 → getSession
//   이 같은 사용자·토큰을 돌려주는지 확인한다. GoTrue 로의 유일한 네트워크 호출
//   (사용자 검증)만 스텁하고, 쿠키 인코딩/재읽기는 전부 라이브러리 실코드다.
//
//   실사용(mint-auth-state)은 signInWithPassword 로 실토큰을 받으므로 JWT·네트워크
//   문제가 없다. 이 자기검증만 합성 JWT 를 쓰기 때문에 사용자 검증 호출을 스텁한다.
//
// 사용: QA_APP_DIR=<앱 폴더> node mint-auth-state.selftest.mjs   (exit 0 = PASS)
// ─────────────────────────────────────────────────────────────────────────
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";

const APP_DIR = process.env.QA_APP_DIR || process.cwd();
let createServerClient;
try {
  const req = createRequire(path.join(APP_DIR, "package.json"));
  ({ createServerClient } = await import(pathToFileURL(req.resolve("@supabase/ssr")).href));
} catch (e) {
  console.error(`[selftest] ✗ @supabase/ssr 를 APP_DIR(${APP_DIR}) 에서 못 찾음. QA_APP_DIR 지정 필요. (${e.message})`);
  process.exit(1);
}

const b64url = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const future = Math.floor(Date.now() / 1000) + 3600;
const email = "qa-selftest@example.com";
const sub = "00000000-0000-0000-0000-0000000000aa";
const user = { id: sub, email, aud: "authenticated", role: "authenticated", app_metadata: {}, user_metadata: {} };
// 구조적으로 유효한(서명 미검증) JWT — 오프라인 setSession/getSession 에 충분.
const jwt = [
  b64url({ alg: "HS256", typ: "JWT" }),
  b64url({ sub, email, aud: "authenticated", role: "authenticated", exp: future, iat: future - 3600 }),
  "c2lnbmF0dXJl",
].join(".");
const session = {
  access_token: jwt, refresh_token: "selftest-refresh", expires_at: future,
  expires_in: 3600, token_type: "bearer", user,
};

// GoTrue 사용자 검증 호출 하나만 스텁. 나머지(쿠키 인코딩/청킹/재읽기)는 실코드.
const realFetch = globalThis.fetch;
globalThis.fetch = async (input, init) => {
  const u = typeof input === "string" ? input : input?.url ?? "";
  if (u.includes("/auth/v1/user")) {
    return new Response(JSON.stringify(user), { status: 200, headers: { "content-type": "application/json" } });
  }
  return realFetch(input, init);
};

const client = (jar) => createServerClient("https://selftestref.supabase.co", "anon-placeholder", {
  cookies: {
    getAll() { return [...jar.entries()].map(([name, value]) => ({ name, value })); },
    setAll(list) { for (const c of list) jar.set(c.name, c.value); },
  },
});

// 1) MINT: 세션을 쿠키로 직렬화.
const writeJar = new Map();
const { error: setErr } = await client(writeJar).auth.setSession(session);
if (setErr) { console.error(`[selftest] ✗ setSession: ${setErr.message}`); process.exit(1); }
const names = [...writeJar.keys()];
if (names.length === 0) { console.error("[selftest] ✗ 쿠키가 쓰이지 않음"); process.exit(1); }

// 2) INJECT + READ-BACK: 그 쿠키만 가진 새 클라이언트로 다시 읽기.
const readJar = new Map(writeJar);
const { data, error: getErr } = await client(readJar).auth.getSession();
if (getErr) { console.error(`[selftest] ✗ getSession: ${getErr.message}`); process.exit(1); }
const got = data.session;
if (!got) { console.error("[selftest] ✗ 세션이 재읽기되지 않음"); process.exit(1); }
if (got.user?.email !== email) { console.error(`[selftest] ✗ 이메일 불일치: ${got.user?.email}`); process.exit(1); }
if (got.access_token !== jwt) { console.error("[selftest] ✗ 토큰 불일치"); process.exit(1); }

console.log(`[selftest] ✓ PASS — 쿠키 ${JSON.stringify(names)} 로 왕복, 사용자 ${email} 복원, 토큰 일치`);
