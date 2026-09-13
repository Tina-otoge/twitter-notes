const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");

function setup(settings = { server: "https://notes.example.com", token: "secret-test-token" }) {
  let listener;
  const requests = [];
  const extension = {
    storage: { local: { get: async () => settings, setAccessLevel: async () => {} } },
    runtime: {
      getURL: (name) => `chrome-extension://test/${name}`,
      onMessage: { addListener: (callback) => { listener = callback; } },
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../background.js"), "utf8"), {
    chrome: extension, URL, AbortSignal,
    fetch: async (url, options) => {
      requests.push({ url, options });
      return { ok: true, status: 200, json: async () => ({ note: null }) };
    },
  });
  return {
    requests,
    send: (message, sender = { tab: { id: 1 }, url: "https://x.com/alice" }) =>
      new Promise((resolve) => listener(message, sender, resolve)),
  };
}

test("background sends token only to configured origin, omits cookies, rejects redirects", async () => {
  const { send, requests } = setup();
  assert.equal((await send({ action: "read", userId: "123" })).ok, true);
  assert.equal(requests[0].url, "https://notes.example.com/api/notes/123");
  assert.equal(requests[0].options.headers.Authorization, "Bearer secret-test-token");
  assert.equal(requests[0].options.credentials, "omit");
  assert.equal(requests[0].options.redirect, "error");
});

test("background rejects foreign senders and arbitrary paths", async () => {
  const { send, requests } = setup();
  assert.equal((await send({ action: "read", userId: "../me" })).ok, false);
  assert.equal((await send({ action: "read", userId: "123" }, {
    tab: { id: 1 }, url: "https://evil.example/alice",
  })).ok, false);
  assert.equal((await send({ action: "check" })).ok, false);
  assert.equal(requests.length, 0);
});

test("background permits local development but refuses remote plaintext servers", async () => {
  const local = setup({ server: "http://127.0.0.1:5000", token: "test" });
  assert.equal((await local.send({ action: "tags" })).ok, true);
  const remote = setup({ server: "http://example.com", token: "test" });
  assert.equal((await remote.send({ action: "tags" })).ok, false);
  assert.equal(remote.requests.length, 0);
});
