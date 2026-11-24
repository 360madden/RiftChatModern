"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { resolveDotnet } = require("../tools/rcm-dotnet-host.cjs");

const root = path.resolve(__dirname, "..");
const standardDir = path.join(root, "program-files");
const standard = path.join(standardDir, "dotnet", "dotnet.exe");
const sdkDir = path.join(root, "sdk");
const sdk = path.join(sdkDir, "dotnet.exe");
function options(files, env = {}) {
  return { platform: "win32", env: { ProgramFiles: standardDir, ...env },
    isFile: file => files.includes(file) };
}

test("existing explicit .NET executable overrides all defaults", () => {
  assert.equal(resolveDotnet(options([standard, sdk], { RCM_DOTNET: sdk })), sdk);
});
test("malformed or missing explicit .NET override fails closed", () => {
  for (const value of ["", "dotnet.exe", sdk]) {
    assert.throws(() => resolveDotnet(options([standard], { RCM_DOTNET: value })),
      /configured_dotnet_host_not_found/);
  }
});
test("standard Windows installation remains first choice", () => {
  assert.equal(resolveDotnet(options([standard, sdk], { PATH: sdkDir })), standard);
});
test("alternate SDK installation resolves through absolute PATH entries", () => {
  assert.equal(resolveDotnet(options([sdk], { Path: ["", "relative", sdkDir].join(path.delimiter) })), sdk);
});
test("missing host never implicitly searches the current directory", () => {
  assert.equal(resolveDotnet(options([], { PATH: ["", ".", "relative"].join(path.delimiter) })), null);
});
