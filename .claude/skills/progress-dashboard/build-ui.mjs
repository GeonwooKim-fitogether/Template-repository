// build-ui.mjs — ONE-TIME build: bundle ui-src/ into assets/dashboard.html.
//
// Produces a single self-contained HTML file: React + react-dom + react-markdown
// + remark-gfm + the whole Director Dashboard UI, inlined. No external requests
// (CSP-safe / works offline / works as a Claude Artifact). The runtime data is
// NOT baked in — the file carries a __DASHBOARD_DATA_JSON__ sentinel that
// render.mjs replaces per project.
//
// Run this only when the UI source changes:
//   node build-ui.mjs --deps "<path-to-a-node_modules-with-react+react-markdown>"
//
// esbuild itself and the react/* + react-markdown + remark-gfm packages are
// resolved from the --deps node_modules (defaults to the sibling SaaS project
// that originated this UI). They are BUILD-TIME ONLY — the emitted HTML has no
// dependency on them.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// --- resolve the build-time node_modules (react etc.) ---------------------
function argVal(flag) {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? process.argv[i + 1] : undefined;
}
const DEFAULT_DEPS = resolve(
  __dirname,
  "../../../../12.subscription-payment-saas-platform/node_modules",
);
const depsDir = resolve(argVal("--deps") ?? DEFAULT_DEPS);
if (!existsSync(join(depsDir, "react"))) {
  console.error(`[build-ui] react not found under ${depsDir}\n` +
    `Pass --deps <node_modules> pointing at an install that has react, ` +
    `react-dom, react-markdown, remark-gfm, and esbuild.`);
  process.exit(2);
}

// esbuild may live in a different node_modules than react (e.g. an isolated
// build install). Defaults to the deps dir.
const esbuildDir = resolve(argVal("--esbuild") ?? depsDir);
const esbuildMain = join(esbuildDir, "esbuild", "lib", "main.js");
if (!existsSync(esbuildMain)) {
  console.error(`[build-ui] esbuild not found at ${esbuildMain}\n` +
    `Pass --esbuild <node_modules> pointing at an install that has esbuild.`);
  process.exit(2);
}
const esbuild = await import(pathToFileURL(esbuildMain).href);

const entry = join(__dirname, "ui-src", "entry.tsx");
const outHtml = join(__dirname, "assets", "dashboard.html");
const outBody = join(__dirname, "assets", "dashboard.body.html");

console.log(`[build-ui] bundling ${entry}`);
const result = await esbuild.build({
  entryPoints: [entry],
  bundle: true,
  format: "iife",
  platform: "browser",
  jsx: "automatic",
  loader: { ".ts": "ts", ".tsx": "tsx" },
  nodePaths: [depsDir],          // resolve bare imports (react, ...) from here
  define: { "process.env.NODE_ENV": '"production"' },
  minify: true,
  write: false,
  legalComments: "none",
  logLevel: "info",
});

const js = result.outputFiles[0].text;

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Progress Dashboard</title>
<style>html,body{margin:0;padding:0;background:#1d2125;color:#c7d1db}#root{min-height:100vh}</style>
</head>
<body>
<div id="root"></div>
<script>window.__STATIC__=true;window.__DASHBOARD_DATA__=__DASHBOARD_DATA_JSON__;</script>
<script>${js}</script>
</body>
</html>
`;

writeFileSync(outHtml, html, "utf8");
const kb = (Buffer.byteLength(html, "utf8") / 1024).toFixed(0);
console.log(`[build-ui] wrote ${outHtml} (${kb} KB)`);

// Body-only fragment for the Claude Artifact path (the publisher wraps it in
// its own <!doctype>/<head>/<body>, so we must NOT include those tags here).
const body = `<style>html,body{margin:0;padding:0;background:#1d2125;color:#c7d1db}#root{min-height:100vh}</style>
<div id="root"></div>
<script>window.__STATIC__=true;window.__DASHBOARD_DATA__=__DASHBOARD_DATA_JSON__;</script>
<script>${js}</script>
`;
writeFileSync(outBody, body, "utf8");
console.log(`[build-ui] wrote ${outBody} (${(Buffer.byteLength(body, "utf8") / 1024).toFixed(0)} KB)`);
console.log(`[build-ui] data injection sentinel: __DASHBOARD_DATA_JSON__`);
