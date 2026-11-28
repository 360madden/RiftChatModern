# RCM — reproducible addon-only packages

The core addon needs no Python, Node, .NET, cloud service or Windows companion at runtime. The developer package builder includes only the RIFT addon folder (seven Lua modules, toc, three font/license files, twelve texture assets). It rejects unexpected files rather than adding development data, character saves, logs, screenshots or private journals.

## Build and verify locally

From a clean checkout in PowerShell, install the normal fixture requirements if needed (Lua 5.1 via Lupa is mandatory for this build):

~~~powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
& .\.venv\Scripts\python.exe -B tools/package_rcm.py
& .\.venv\Scripts\python.exe -B tools/package_rcm.py --check
~~~

The output is dist/RiftChatModern-<version>.zip and a companion .zip.sha256 checksum. The script validates the exact captured manifest and startup order through the existing deployment validator, compiles every Lua module without executing addon code, builds an archive with sorted names and fixed metadata, and reads back every archive member. Identical source bytes yield identical package bytes; text checkout conversions can change source bytes, so use the checksum for the exact artifact. Output is never overwritten if it differs. Existing identical outputs are reusable; if a build was interrupted before the checksum was published, repeat it. Publishing requires a local filesystem with hard-link support (NTFS works); it refuses unsupported filesystems rather than replacing an existing package. Run from a stable checkout without concurrent edits. The check command performs no persistent writes to the output directory.

## CI candidate

The Windows regression workflow builds and checks an addon-only candidate after the full regression gate, then retains the ZIP and checksum as a workflow artifact. This is a development candidate, **not** a GitHub release or physical RIFT certification. No license change or release tag is implied. The repository's existing licensing decision remains unchanged.

After a successful run, open its Artifacts section and download the candidate. Extract the outer GitHub artifact wrapper to obtain the inner addon ZIP and checksum. Verify the actual inner archive with:

~~~powershell
$zip = Get-Item -LiteralPath '.\RiftChatModern-0.2.26.zip'
$expected = ((Get-Content -LiteralPath ($zip.FullName + '.sha256') -Raw).Trim() -split '\s+')[0]
if ((Get-FileHash -LiteralPath $zip.FullName -Algorithm SHA256).Hash -ne $expected) {
    throw 'Package checksum mismatch'
}
~~~

For a new installation only, extract that inner ZIP so the single RiftChatModern directory sits directly under the actual configured RIFT Interface\AddOns directory. Verify the toc path. Do not copy the whole repository or create a nested RiftChatModern/RiftChatModern folder. If the addon already exists, use the guarded updater with the actual host and verified installation path instead of blindly extracting over it. Preserve SavedVariables and the last accepted version until the patch-only acceptance gate is satisfied.

See [deployment policy](LIVE_DEPLOYMENT_RELOADUI_POLICY_20261120.md), [offline qualification](OFFLINE_CI.md) and the [current handoff](HANDOFF_20261128_SATURDAY_LEGION.md). Packaging does not require RIFT to run and never modifies the game or its settings. No new physical chat reception, in-game UI or deployment claim is made.
