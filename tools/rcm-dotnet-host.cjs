"use strict";

// Locate a genuine installed .NET host without using a shell or depending
// on the current working directory. The sender DLL and all live-game pins
// are still checked by the existing coordinator and .NET receiver.
const fs = require("node:fs");
const path = require("node:path");

function resolveDotnet({ env = process.env, platform = process.platform,
  isFile = p => {
    try { return fs.statSync(p).isFile(); } catch (_) { return false; }
  } } = {}) {
  // Explicit configuration must be absolute and exist. Never quietly fall
  // back after a misspelled override: operators need a useful failure.
  if (Object.hasOwn(env, "RCM_DOTNET")) {
    const override = env.RCM_DOTNET;
    if (!override || !path.isAbsolute(override) || !isFile(override))
      throw new Error("configured_dotnet_host_not_found");
    return override;
  }
  const binary = platform === "win32" ? "dotnet.exe" : "dotnet";
  // Keep the previous standard Windows install preference for AMD-DESKTOP.
  const standard = platform === "win32" ?
    path.join(env.ProgramFiles || "C:\\Program Files", "dotnet", binary) : null;
  if (standard && path.isAbsolute(standard) && isFile(standard)) return standard;
  // Absolute PATH entries only. No implicit cwd or shell expansion.
  const key = Object.keys(env).find(k => k.toUpperCase() === "PATH");
  for (const entry of String(key ? env[key] : "").split(path.delimiter)) {
    if (!path.isAbsolute(entry)) continue;
    const candidate = path.join(entry, binary);
    if (isFile(candidate)) return candidate;
  }
  return null;
}

module.exports = { resolveDotnet };
