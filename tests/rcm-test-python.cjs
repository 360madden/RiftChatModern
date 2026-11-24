"use strict";

// Resolve the Python interpreter for fixture-only disk-auditor tests.
// Keep production verify-disk's explicit absolute-path requirement intact.
const fs = require("node:fs");
const path = require("node:path");

function resolveTestPython({ env = process.env, platform = process.platform,
  root = path.resolve(__dirname, ".."), isFile = (p) => {
    try { return fs.statSync(p).isFile(); } catch (_) { return false; }
  } } = {}) {
  // An explicit override is a contract, not a hint. A typo must fail rather
  // than silently skip tests or select a different interpreter.
  if (Object.hasOwn(env, "RCM_TEST_PYTHON")) {
    const value = env.RCM_TEST_PYTHON;
    if (!value || !path.isAbsolute(value) || !isFile(value))
      throw new Error("RCM_TEST_PYTHON must name an existing absolute interpreter file");
    return value;
  }
  // Prefer RCM's own isolated development environment on any host.
  const local = platform === "win32" ?
    path.join(root, ".venv", "Scripts", "python.exe") :
    path.join(root, ".venv", "bin", "python");
  if (isFile(local)) return local;

  // Preserve the historical AMD-DESKTOP test setup during migration.
  // A missing legacy environment is reported as a genuine skipped test.
  const legacy = platform === "win32" ?
    path.resolve(root, "..", "riftreader2", ".venv", "Scripts", "python.exe") : null;
  return legacy && isFile(legacy) ? legacy : null;
}

module.exports = { resolveTestPython };
