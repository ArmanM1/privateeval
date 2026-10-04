import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the PrivateEval application shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>PrivateEval — Local Model Evaluation Lab<\/title>/i);
  assert.match(html, /Opening the lab/);
  assert.match(html, /Loading the versioned result bundle/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});

test("ships traceable result data and removes starter infrastructure", async () => {
  const [page, layout, packageJson, result] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../public/results/result_bundle.json", import.meta.url), "utf8"),
  ]);
  assert.match(page, /fetch\("\/results\/result_bundle\.json", \{ cache: "no-store" \}\)/);
  assert.match(page, /Example lab/);
  assert.match(page, /Blind review/);
  assert.match(page, /FIXED 12-CARD REVIEW PACKET/);
  assert.match(page, /Export \{completedCardIds\.length\} ratings/);
  assert.match(page, /CONFIGURATION CARDS/);
  assert.match(page, /ONE-COMMAND REPRODUCTION/);
  assert.match(page, /python -m privateeval run --config configs\/demo\.json/);
  assert.match(page, /reports\/MODEL_CARD\.md/);
  assert.match(page, /github\.com\/ArmanM1\/privateeval/);
  assert.match(layout, /PrivateEval — Local Model Evaluation Lab/);
  assert.match(layout, /favicon\.svg/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  assert.match(result, /"schema_version": "1\.0"/);
  await assert.rejects(access(new URL("../app/_sites-preview/SkeletonPreview.tsx", import.meta.url)));
  await access(new URL("../dist/client/results/result_bundle.json", import.meta.url));
  await access(new URL(".openai/hosting.json", root));
});
