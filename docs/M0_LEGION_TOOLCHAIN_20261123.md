# RCM — Monday M0 development environment and host portability verification

**Date:** November 23, 2026 (EST) · **Host:** LEGION · **Starting HEAD:** `b4b8b77bf911117cc42370239ef7ffd3edf919ef` (clean, matched remote before edits).

## Results

| Verification | Result |
|---|---|
| Python 3.14.10 + Lupa 2.8 (Lua 5.1) + Pillow 13.0.0 | Successfully installed in RCM's isolated .venv; imports and Lua version verified |
| Full Python/Lua suite | 321 passed, zero failures or skips; confirmed again after all code and roadmap edits (48.039s) |
| Full Node suite after fixes | 129 passed, zero failures or skips |
| .NET 10.0.403 Release editor sender | Build passed, zero warnings and errors |
| Physical RIFT acceptance | NOT RUN — AMD-DESKTOP connection unavailable |

The prior LEGION environment errors and skipped tests are now superseded for this test configuration. No Windows security policy was changed; the prior DLL restriction was not reproduced in this run. The current addon version remains v0.2.23; no game deployment or game input was performed.

## Root causes and fixes

1. The Say and public disk-receipt integration tests relied on a hardcoded sibling Python virtual environment. The shared test-only interpreter resolver now prefers RCM's own .venv, supports an explicit absolute RCM_TEST_PYTHON, and retains a legacy Windows fallback. Invalid explicit overrides fail rather than skip.
2. The delivery coordinator expected .NET at a fixed Windows installation path. LEGION uses an alternate installed SDK. Four Node tests reproduced the failure after prerequisites were supplied. The shared .NET host resolver honors an explicit absolute RCM_DOTNET, then the standard Windows installation, then absolute PATH entries. No shell or current-directory search is used. Missing sender and missing host have distinct diagnostics; existing dispatch validation and game pins remain unchanged.
3. Four sender tests previously returned early if the DLL was absent, falsely appearing to pass. They now produce explicit skip reasons; on this configured run all four actually executed and passed.
4. Added ten resolver tests and pinned Python development dependencies in requirements-dev.txt.

## Reproduction

Use the repository-root instructions in README.md and CONTRIBUTING.md. Node 24.20.0 and .NET SDK 10.0.403 were observed. The host observer reuses the existing LuaPadModern sibling decoder; the LEGION sibling checkout was clean at `559a721ba95f23b419af2ca02597f7d2079c8e18`, ahead of its own remote by 16 commits. Decoder SHA-256: `1ed80e2b43073a4d4d70a670a6fafa603616bbb68be842102fdf4ee5d1d7d399`. That repository was not modified. This dependency still needs to be accounted for in a fresh-clone release workflow.

## Next

M0/RCM-002 is qualified on LEGION. M1 remains blocked pending a fresh AMD-DESKTOP game session. Preserve public and Say journal isolation; use real new game-generated evidence for M1. If AMD remains unavailable, move to independent UX1/API1 offline work or improve the dependency provenance/preflight. Do not infer physical acceptance from the green offline test suite.
