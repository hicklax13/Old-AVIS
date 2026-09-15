# Hermes Desktop profile loading repair — 2026-09-13

Verified in the canonical Desktop app and normal Roaming profile at 18:19 ET.

## Result

All eight local profiles opened successfully in the running Desktop app:
default, builder, development, google-personal, google-school, operator,
researcher, and reviewer. Each displayed Gateway ready. Operator and Reviewer
also passed repeat switches with the full pool running; returning to default
passed. No slot wait or profile-start failure was logged after deployment.

Separate read-only diagnostics connected to all eight actual Desktop-owned
backends. Each returned a gateway-ready event, successful runtime configuration
check, and session-list response. Process ownership and each backend's own
HERMES_HOME established the correct profile identity. All eight retained the
same backend PIDs during the repeated-switch checks.

## Confirmed causes and changes

1. The device had no saved `pool-limits.json`, so Hermes used its default cap of
   three non-primary backends and a ten-minute idle timeout. The real Desktop
   log repeatedly showed Operator waiting at `3/3 busy` and failing after the
   thirty-second slot-wait deadline. Eight profiles exceeded this capacity.
   The cap is intentional resource management; the profiles were not corrupt.
2. Saved `maxBackends: 8` and `idleMs: 604800000` (seven days) in
   `C:\Users\conno\AppData\Roaming\Hermes\pool-limits.json`. This accommodates
   all seven named profiles alongside the primary default backend, with room
   for the coordinator's foreground reservation. The running app read these
   exact values at startup, and its native Advanced settings displayed them.
3. A separate renderer bug left the `runtime-not-ready` notification visible
   after readiness recovered. Updated `refreshOnboarding` to dismiss that
   specific notification only after the runtime check succeeds. The regression
   test preserves unrelated notifications and deduplicates repeated warnings.

The existing backend coordinator and resource controls remain in use. No
profile was recreated, no OAuth store was copied, and no account or model
configuration was changed by this repair. Read-back confirms the same 15 enabled
MCP definitions and nine shared OAuth owners across all eight profiles. Plaid,
Strava, Indeed, and Unreal Engine remain removed as Connor requested.

## Validation and deployment

- Regression reproduced before the fix: the warning remained after a successful
  runtime check. After the fix, the onboarding and profile suites passed all
  39 tests. Renderer TypeScript checking and the production build passed.
- The packaged candidate passed a hidden, isolated Electron render test and a
  native terminal test. The test window was never visible and was closed.
- Verified all 500 files of a recoverable canonical package backup before
  replacement. Promoted the staged package using the existing verified swap
  helper, then relaunched through the pinned taskbar shortcut at 18:05 ET.
- Canonical executable remains
  `C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`.
  Normal user data remains `C:\Users\conno\AppData\Roaming\Hermes`.
  Both the taskbar pin and Desktop Startup shortcut resolve to that executable.
- Hermes remains 0.21.2 at `3f86ed75dad1933036c52018e991dbd839837126` plus local
  repairs; Desktop package 0.17.2, Electron 41.10.3. The installed package stamp
  matches the managed source, and the staged and installed archive hashes match.
- Installed `app.asar` SHA-256:
  `3718f959026cb7943bdbc1e8b6235bd80debebdd68586db64850c77b6819e02a`.
- Final process audit: canonical root PID 87928 with four canonical children,
  all eight owned profile backends, and zero test `electron.exe` processes.
  The eight backend runtime processes used approximately 2.52 GiB of private
  memory during the audit. Other applications and available memory fluctuate.
- The managed working tree and earlier updater, MCP, and Doctor repairs were
  preserved. No commits or pushes were made. This was targeted verification,
  not a claim that the entire repository test suite passed.

## Evidence and recovery

Evidence directory: `C:\Dev\hermes-agent-recovery\profile-loading-20260913`.

- `slot-failures-before.txt`: original repeated slot failures.
- `readiness-red.log`, `profile-green.log`, `typecheck.log`, `build.log`, and
  `package.log`: regression and build evidence.
- `native-profile-checks.json`: observations from the canonical native window.
- `native-settings-check.json`: direct Advanced settings read-back.
- `all-eight-first.json` and `all-eight-after-switches.json`: live authenticated
  backend diagnostics, with credentials and session contents excluded.
- `shared-mcp-readback.json`, `startup-and-pool-after.txt`, `pin-before.json`,
  `pin-after.json`, `deployment-proof.json`, and `final-audit.json`: persistence,
  configuration, process, and package proof.
- `win-unpacked-before` plus `package-before-manifest.json`: verified original
  package backup. The swap also retained `release\win-unpacked.previous`.
- `onboarding-before.ts`, `onboarding-before.test.ts`,
  `source-before-deployment.patch`, and `HERMES_READINESS_TODO.before.md` preserve
  the previous files and the complete managed source diff at deployment.
- `pool-limits-before-state.json` records that the preference file did not
  previously exist. Reverting this preference would restore the three-slot
  default and could reproduce the reported failure.

## Practical limits

These changes resolve the reproduced slot-exhaustion failure and stale warning
for the current eight-profile roster. The saved preference survives application
restarts; this was verified by the deployment restart and native settings
read-back. Unused backends may still be reclaimed after seven days. Closing or
restarting the app requires backends to start again when needed.

Cold laptop reboot and sleep/wake recovery were not exercised. This verification
covers profile loading, session access, and runtime configuration readiness; it
does not assert a newly generated model response or a fresh tool invocation for
every MCP. Network outages, revoked provider grants, billing limits, OS resource
pressure, and future upstream regressions cannot be permanently excluded. A
larger future profile roster may require revisiting the saved capacity.
