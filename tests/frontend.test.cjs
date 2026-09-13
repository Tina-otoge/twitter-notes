const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function setup(context) {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const field = () => ({
    value: "", listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; },
  });
  const search = field();
  const tag = field();
  const submissions = [];
  const requests = [];
  const documentListeners = {};
  const results = {
    ...field(), children: [],
    setAttribute() {}, removeAttribute() {},
    replaceChildren(...children) { this.children = children; },
  };
  const error = { hidden: true };
  const location = { href: "https://notes.example.com/?q=&tag=" };
  const form = {
    ...field(),
    action: "https://notes.example.com/",
    elements: { q: search, tag },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../app/static/app.js"), "utf8"), {
    document: {
      querySelector: (selector) => ({
        "[data-note-filters]": form,
        "[data-note-results]": results,
        "[data-filter-error]": error,
      })[selector],
      querySelectorAll: () => [],
      addEventListener: (name, callback) => { documentListeners[name] = callback; },
    },
    window: {
      location, confirm: () => false,
      history: { replaceState: (_, title, url) => { location.href = url.href; } },
    },
    FormData: class { constructor() { return [["q", search.value], ["tag", tag.value]]; } },
    DOMParser: class {
      parseFromString(html) {
        return { querySelector: () => html === "missing" ? null : { childNodes: [html] } };
      }
    },
    fetch: (url, options) => {
      submissions.push({ q: url.searchParams.get("q"), tag: url.searchParams.get("tag") });
      return new Promise((resolve, reject) => {
        requests.push({ url, options, resolve, reject });
      });
    },
    URL, URLSearchParams, AbortController, setTimeout, clearTimeout,
  });
  return { search, tag, submissions, requests, form, results, error, location, documentListeners };
}

test("search waits for 200 ms after the last text change", (context) => {
  const { search, submissions } = setup(context);
  search.value = "al";
  search.listeners.input({});
  context.mock.timers.tick(199);
  assert.equal(submissions.length, 0);
  search.value = "alice";
  search.listeners.input({});
  context.mock.timers.tick(199);
  assert.equal(submissions.length, 0);
  context.mock.timers.tick(1);
  assert.deepEqual(submissions, [{ q: "alice", tag: "" }]);
});

test("blur searches immediately and cancels the pending search", (context) => {
  const { search, submissions } = setup(context);
  search.value = "alice";
  search.listeners.input({});
  search.listeners.blur();
  assert.equal(submissions.length, 1);
  context.mock.timers.tick(200);
  search.listeners.blur();
  assert.equal(submissions.length, 1);
});

test("tag changes immediately submit the current search and tag", (context) => {
  const { search, tag, submissions } = setup(context);
  search.value = "alice";
  search.listeners.input({});
  tag.value = "2";
  tag.listeners.change();
  assert.deepEqual(submissions, [{ q: "alice", tag: "2" }]);
  context.mock.timers.tick(200);
  assert.equal(submissions.length, 1);
  tag.value = "";
  tag.listeners.change();
  assert.deepEqual(submissions[1], { q: "alice", tag: "" });
});

test("unchanged text does not search, and clearing cancels a pending search", (context) => {
  const { search, submissions } = setup(context);
  search.listeners.blur();
  search.listeners.input({});
  context.mock.timers.tick(200);
  assert.equal(submissions.length, 0);
  search.value = "alice";
  search.listeners.blur();
  search.value = "";
  search.listeners.input({});
  context.mock.timers.tick(200);
  assert.equal(submissions.length, 1);
});

test("submit uses fetch and replaces only results while updating the URL", async (context) => {
  const { form, search, requests, results, location } = setup(context);
  search.value = "alice";
  let prevented = false;
  const completion = form.listeners.submit({ preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  requests[0].resolve({ ok: true, text: async () => "Alice's notes" });
  await completion;
  assert.deepEqual(results.children, ["Alice's notes"]);
  assert.equal(search.value, "alice");
  assert.equal(new URL(location.href).searchParams.get("q"), "alice");
  search.value = "";
  const cleared = search.listeners.blur();
  requests[1].resolve({ ok: true, text: async () => "All notes" });
  await cleared;
  assert.deepEqual(results.children, ["All notes"]);
});

test("stale responses cannot replace newer results", async (context) => {
  const { search, requests, results } = setup(context);
  search.value = "alice";
  const first = search.listeners.blur();
  search.value = "bob";
  search.listeners.input({});
  assert.equal(requests[0].options.signal.aborted, true);
  const second = search.listeners.blur();
  requests[1].resolve({ ok: true, text: async () => "Bob" });
  await second;
  requests[0].resolve({ ok: true, text: async () => "Alice" });
  await first;
  assert.deepEqual(results.children, ["Bob"]);
});

test("failed requests preserve results and can be retried", async (context) => {
  const { search, requests, results, error } = setup(context);
  results.children = ["Existing notes"];
  search.value = "alice";
  const first = search.listeners.blur();
  requests[0].reject(new Error("Offline"));
  await first;
  assert.equal(error.hidden, false);
  assert.deepEqual(results.children, ["Existing notes"]);
  const retry = search.listeners.blur();
  requests[1].resolve({ ok: true, text: async () => "Alice" });
  await retry;
  assert.equal(error.hidden, true);
  assert.deepEqual(results.children, ["Alice"]);
});

test("pagination uses fetch and new note forms retain delete confirmation", async (context) => {
  const { results, requests, documentListeners } = setup(context);
  let prevented = false;
  const completion = results.listeners.click({
    button: 0,
    target: { closest: () => ({ href: "https://notes.example.com/?page=2" }) },
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
  requests[0].resolve({ ok: true, text: async () => "Page two" });
  await completion;
  assert.deepEqual(results.children, ["Page two"]);
  let deletionPrevented = false;
  documentListeners.submit({
    target: { closest: () => ({ dataset: { confirm: "Delete?" } }) },
    preventDefault() { deletionPrevented = true; },
  });
  assert.equal(deletionPrevented, true);
});
