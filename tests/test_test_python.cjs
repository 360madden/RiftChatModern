"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { resolveTestPython } = require("./rcm-test-python.cjs");

const root = path.resolve(__dirname, "..");
const local = path.join(root, ".venv", "Scripts", "python.exe");
const legacy = path.resolve(root, "..", "riftreader2", ".venv", "Scripts", "python.exe");
const custom = path.join(root, "test-fixture-python.exe");
function options(files, env = {}) {
  return { env, root, platform: "win32", isFile: p => files.includes(p) };
}

test("explicit absolute Python test override wins", () => {
  assert.equal(resolveTestPython(options([custom, local], { RCM_TEST_PYTHON: custom })), custom);
});
test("invalid explicit override fails loudly instead of falling back", () => {
  for (const value of ["", "relative.exe", custom]) {
    assert.throws(() => resolveTestPython(options([local], { RCM_TEST_PYTHON: value })), /existing absolute/);
  }
});
test("project virtual environment is preferred over legacy sibling", () => {
  assert.equal(resolveTestPython(options([local, legacy])), local);
});
test("legacy fallback is explicit and missing runtimes resolve to null", () => {
  assert.equal(resolveTestPython(options([legacy])), legacy);
  assert.equal(resolveTestPython(options([])), null);
});
test("non-Windows project environment uses bin/python", () => {
  const posix = path.join(root, ".venv", "bin", "python");
  assert.equal(resolveTestPython({ ...options([posix]), platform: "linux" }), posix);
});
