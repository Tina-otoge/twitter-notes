const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");

function setup(stored = {}) {
  const elements = new Map();
  const permissions = [];
  let saved;
  const document = { getElementById: (id) => {
    if (!elements.has(id)) elements.set(id, {
      value: "", listeners: {},
      addEventListener(name, callback) { this.listeners[name] = callback; },
    });
    return elements.get(id);
  } };
  const chrome = {
    storage: { local: {
      get: async () => stored,
      set: async (data) => { saved = data; },
      remove: async () => {},
    } },
    permissions: { request: async (data) => { permissions.push(data); return true; } },
    runtime: { sendMessage: async () => ({ ok: true, data: { username: "alice" } }) },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../popup.js"), "utf8"), {
    document, chrome, URL,
  });
  return { elements, permissions, saved: () => saved };
}

test("popup defaults to the hosted Twitter-Notes server", async () => {
  const fixture = setup();
  await new Promise(setImmediate);
  assert.equal(fixture.elements.get("server").value, "https://twitter-notes.tina.moe");
});

test("popup preserves a saved custom server", async () => {
  const fixture = setup({ server: "https://notes.example.com" });
  await new Promise(setImmediate);
  assert.equal(fixture.elements.get("server").value, "https://notes.example.com");
});

test("popup requests a portable host permission but preserves the exact server port", async () => {
  const fixture = setup();
  await new Promise(setImmediate);
  fixture.elements.get("server").value = "http://127.0.0.1:5000";
  fixture.elements.get("token").value = "tn_" + "a".repeat(43);
  await fixture.elements.get("settings").listeners.submit({ preventDefault() {} });
  assert.equal(fixture.permissions[0].origins[0], "http://127.0.0.1/*");
  assert.equal(fixture.saved().server, "http://127.0.0.1:5000");
  assert.equal(fixture.elements.get("status").textContent, "Connected as @alice.");
});

test("popup rejects remote HTTP before requesting permissions or storing the token", async () => {
  const fixture = setup();
  await new Promise(setImmediate);
  fixture.elements.get("server").value = "http://example.com";
  fixture.elements.get("token").value = "tn_" + "a".repeat(43);
  await fixture.elements.get("settings").listeners.submit({ preventDefault() {} });
  assert.equal(fixture.permissions.length, 0);
  assert.equal(fixture.saved(), undefined);
  assert.match(fixture.elements.get("status").textContent, /HTTPS/);
});