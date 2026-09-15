# Hermes Desktop Doctor repair — September 13, 2026

The repairs are deployed in the pinned canonical Hermes Desktop app and verified
with its normal Windows profile. The update completed at 17:06:15 ET and relaunched
the app at 17:06:19. The final in-app Doctor run completed successfully and reports
one remaining account issue: the xAI API key has exhausted credits or reached its
monthly spending limit. All five JavaScript dependency audits report no known
vulnerabilities, and the obsolete profile-launcher warning is gone.

Installed Hermes is 0.21.2 at `3f86ed75dad1933036c52018e991dbd839837126`, with the
local repairs. The existing main channel includes the latest published
[v2026.9.11 release](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.9.11),
verified against GitHub's release metadata and the release commit's ancestry.

## What the supplied Doctor report found

The 16:03:53 ET report identified vulnerable JavaScript dependencies, an obsolete
Windows profile launcher, an xAI HTTP 403, and optional integrations without setup.
Doctor also understated its findings: it marked moderate-only vulnerabilities green,
omitted the Desktop workspace audit, and described web advisories as build-only
without checking whether that was true. Saved xAI OAuth credentials were presented
as a successful login even though their connectivity had not been tested.

## Repairs

- Updated affected direct and transitive dependencies using compatible security
  patches. Electron is 41.10.3 and Vitest is 4.1.11. Root/workspace audit findings
  fell from 18 to zero; the separate WhatsApp bridge audit fell from four to zero.
  The original npm release-age policy was preserved; no forced audit fix was used.
- Doctor now audits the Desktop workspace, reports all severities, and explicitly
  flags failed or malformed audits as unverified. It no longer calls an unchecked
  dependency safe or assumes every web advisory is restricted to build tooling.
- Fixed Windows profile deletion to remove its actual `.bat` launcher, including
  compatibility with older extensionless launchers. Doctor now uses the existing
  alias metadata. The exact obsolete `programmer.bat` was backed up and removed.
- Doctor distinguishes a saved OAuth grant from a working static xAI API key.
  A read-only live check classified the 403 as exhausted credits or a monthly
  spending limit. No credentials, billing limits, or subscriptions were changed.

The Electron patch covers both the cache-partition and sandboxed-iframe advisories;
40.10.6 alone would not fix the latter. Primary references:
[Electron iframe advisory](https://github.com/advisories/GHSA-9f4c-93c8-jc8g),
[Electron cache advisory](https://github.com/advisories/GHSA-r4w5-6pfg-jxp5),
[Vitest advisory](https://github.com/advisories/GHSA-82fw-gwwq-j7x9),
[Browserslist advisory](https://github.com/advisories/GHSA-c83g-rgw3-j3cx).

## Additional update initiated at 16:45 ET

Connor clicked Update while final Doctor verification was underway. The incoming
14 main-branch commits included a new daily MCP notification feature, which conflicted
with the local prerequisite classification in two files. The CLI correctly refused
to continue after failing to restore the repairs, but the Windows handoff treated
exit 1 as retryable. The fresh retry saw the reset checkout and began building
without the preserved changes.

The verified updater process tree was stopped before package promotion. All 73
modified tracked files were recovered from stash
`305a0e52f61ff829a6146e00f3181236ed63c600`; all 18 untracked source/test files were
verified against its archive. The two conflicts were resolved by retaining both
the upstream notification behavior and the local prerequisite checks.

Required restore failure now exits as a safety refusal. The running Windows
handoff also recognizes that refusal before consulting retry policy, including
when a stale dependency-recovery marker exists or the on-disk policy has been
replaced by an upstream checkout. The recovery stash remains preserved.

The update also reproduced a startup persistence defect: regenerating the gateway
launcher changed it back to detached execution, so the retry wrapper received
success as soon as the child started. The generator now supports a `/wait` option
that returns the real child exit code while retaining its default asynchronous
behavior for other callers. The existing startup supervisor now uses that option.
An actual launch through the Startup wrapper verified the live supervisor,
waiting launcher, and gateway process chain. The canonical Desktop Startup
shortcut and taskbar shortcut both resolve to the installed executable.

## Verification

- Final installed-app Doctor: root package, Desktop, web, TUI, and WhatsApp bridge
  audits all report no known vulnerabilities. The result was read back from the
  canonical app's Maintenance panel; Doctor returned exit 0 with one explicitly
  listed xAI billing action. Optional unconfigured services remain labeled.
- The full repaired Windows updater completed with a successful durable receipt,
  rebuilt and promoted the package, and relaunched the canonical app. The installed
  build stamp is current and the managed release junction resolves correctly.
- After that update, a hidden smoke test against the installed canonical executable
  verified Electron 41.10.3, packaged mode, a rendered application root, and a real
  native terminal command with exit 0. All test windows were hidden and closed.
- Native Desktop showed `v0.21.2 3f86ed7` and Gateway ready using the normal
  `C:\Users\conno\AppData\Roaming\Hermes` profile. The final process audit found
  one canonical root, five app children, and zero test Electron processes.
- All eight profiles read back the same 15 enabled MCP servers and nine shared
  OAuth owners. Connor confirmed removing Plaid, Strava, Indeed, and Unreal Engine;
  these remain removed. The post-update Desktop MCP list also showed healthy
  discovered tools for the visible services, including Hugging Face and Webflow.
- 48 focused Python tests passed after the final integration: Doctor audit and xAI
  classification, Windows alias cleanup, required stash restore, and Windows handoff.
- The retry regression first reproduced the unsafe second invocation in real
  PowerShell, then passed with the guard. Both normal and stale-marker paths are covered.
- Five focused Desktop suites passed: 39 tests passed and one skipped, covering
  merged MCP health behavior, probe caching, OAuth UI, System update, and handoff markers.
- Ten Windows launcher tests passed. The new regression runs the generated VBS
  against a real child process that exits 7; before the fix it returned 0, and
  after the fix it correctly returned 7 to its supervisor.
- Before the additional update, the production Desktop build and type checks passed;
  a hidden packaged Electron 41.10.3 launch rendered the app and ran a real native
  terminal command successfully. Web tests passed 303/303 and root JS tests 69/69.
- The broader Desktop Electron suite was not fully green: 2,174 passed, 38 failed,
  eight skipped. Failures included Windows-incompatible test assumptions and a
  timing-sensitive test. Four broader profile-test failures were reproduced against
  untouched HEAD. These results are not presented as a clean full-suite run.

## Recovery and remaining limits

Evidence directory: `C:\Dev\hermes-agent-recovery\doctor-repair-20260913`.
It contains original manifests and locks, the supplied Doctor report, security
audit JSON, source patches and untracked-source archives, test output, deployment
proof, and two independently verified full package backups of 500 files each.

The xAI API billing restriction requires account-owner action. Optional services
without accounts or credentials are not repaired by installing arbitrary packages.
Plaid, Strava, Indeed, and Unreal Engine are no longer pending setup: Connor
explicitly chose to leave them removed. The shared configuration now contains
15 services across all eight profiles. Earlier 19-server records are historical.

Final evidence is recorded in `final-deployment-proof.json`,
`final-system-proof.json`, `desktop-doctor-ui-proof.json`,
`desktop-doctor-status.json`, `hidden-package-smoke.json`, and
`post-update-profile-readback.json` in the evidence directory. The final source
patch and archive preserve the modified tracked files and 19 untracked source/test
files; the recovery stash is retained. The updater's optional built-in backup step
was reported disabled or failed, so the independent verified package and source
backups are the recovery authority.

Startup runs at Windows sign-in. The live wrapper and real child failure handling
were verified; a cold reboot and sleep/wake recovery were not tested. A sleeping
or powered-off laptop cannot maintain active connections.

These changes prevent the reproduced local failures and make future failures
visible. They cannot guarantee perpetual provider access, prevent future published
vulnerabilities, or automatically resolve every future source conflict. No purchase,
credential rotation, public post, commit, or push was made.
