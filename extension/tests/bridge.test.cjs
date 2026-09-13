const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");

function setup(data) {
  const events = [];
  const listeners = new Map();
  const response = { clone: () => ({ json: async () => data }) };
  const window = {
    fetch: async () => response,
    dispatchEvent: (event) => events.push(event),
    addEventListener: (name, callback) => listeners.set(name, callback),
  };
  class XHR {
    open() {}
    addEventListener(name, callback) { this[name] = callback; }
  }
  class CustomEvent {
    constructor(type, options) { this.type = type; this.detail = options.detail; }
  }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../bridge.js"), "utf8"), {
    window, XMLHttpRequest: XHR, CustomEvent, URL, Request, location: { origin: "https://x.com" },
  });
  return { window, events, listeners, XHR, response };
}

test("captures stable IDs from legacy fetch responses without consuming the response", async () => {
  const { window, events, response } = setup({ data: { user: { result: {
    __typename: "User", rest_id: "9007199254740993123", legacy: { screen_name: "Alice" },
  } } } });
  assert.equal(await window.fetch("/i/api/graphql/hash/UserByScreenName"), response);
  await new Promise(setImmediate);
  assert.deepEqual(JSON.parse(events[0].detail), { username: "Alice", userId: "9007199254740993123" });
});

test("captures current core responses via XHR and replays identities", () => {
  const { XHR, events, listeners } = setup({});
  const xhr = new XHR();
  xhr.open("GET", "/i/api/graphql/hash/UserByScreenName");
  xhr.responseText = JSON.stringify({ data: { user: { result: {
    rest_id: "123", core: { screen_name: "someone" },
  } } } });
  xhr.load();
  assert.equal(JSON.parse(events[0].detail).userId, "123");
  listeners.get("twitter-notes:request-identities")();
  assert.equal(events.length, 2);
});

test("ignores unrelated endpoints, foreign origins and invalid identities", async () => {
  const { window, events } = setup({ rest_id: 123, legacy: { screen_name: "bad/handle" } });
  await window.fetch("/i/api/graphql/hash/UserByScreenName");
  await window.fetch("https://example.com/i/api/graphql/hash/UserByScreenName");
  await window.fetch("/i/api/graphql/hash/HomeTimeline");
  await new Promise(setImmediate);
  assert.equal(events.length, 0);
});
