const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

test("panel contains keyboard events without cancelling native editing", async () => {
  const listeners = new Map();
  const shadow = {
    addEventListener(type, handler) { listeners.set(type, handler); },
    append() {},
  };
  const header = { closest: () => null, after() {} };
  let scheduled;
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../content.js"), "utf8"), {
    location: { pathname: "/someone" },
    document: {
      querySelector: () => header,
      createElement: () => ({
        attachShadow: () => shadow,
        append() {}, setAttribute() {},
      }),
    },
    window: { addEventListener() {}, dispatchEvent() {} },
    Event,
    MutationObserver: class { observe() {} },
    setTimeout(callback) { scheduled = callback; },
    clearTimeout() {},
  });
  await scheduled();
  for (const type of ["keydown", "keypress", "keyup"]) {
    let stopped = false;
    listeners.get(type)({
      stopPropagation() { stopped = true; },
      preventDefault() { assert.fail("Native editing must remain enabled"); },
    });
    assert.equal(stopped, true, `${type} must stay inside the panel`);
  }
});