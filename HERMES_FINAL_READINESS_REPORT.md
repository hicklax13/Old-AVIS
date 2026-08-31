# Hermes Desktop final readiness report

Verified through 2026-08-31 on Connor's ASUS Windows 11 laptop. This report covers the
local delivered system. It does not claim that unpublished commits are on the
upstream repository.

## Delivery verdict

The canonical green Hermes Desktop installation is healthy and locally ready.
The clean package is installed at
`C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`, both
Windows shortcuts still target it, the normal-profile gateway reconnects after
a pinned-shortcut launch, and no test `electron.exe` remains. No Codex-owned
runtime or notification defect is open.

Connor authorized remote publication. The signed local line was rebased onto
`origin/main`, published to Connor's fork, and opened upstream as PR
`https://github.com/NousResearch/hermes-agent/pull/98393`. The final published
implementation commit was rebuilt, smoke-tested, installed, reconciled into the
managed runtime, and verified through the canonical green app's normal profile.
The PR remains open and currently has no review or status-check result; that
external state is not represented as merged.

## Installed Desktop and runtime

- Desktop package version: `0.17.0`; Electron: `40.10.2`.
- Clean build stamp: commit
  `35c44b1db1ee6ca844032556bc71d09f05a111c4`, branch
  `codex/hermes-desktop-readiness`, built `2026-08-30T06:18:02.186Z`,
  `dirty: false`.
- Installed executable SHA-256:
  `2d4d422e278de78c7622c5ded9b3e09b86e2df21625b1f6c96e273086ca5880d`.
- Taskbar and Start Menu shortcuts resolve to the canonical executable and use
  its `win-unpacked` directory as the working directory.
- The live root process was relaunched through the pinned shortcut after final
  testing. Its root command line has no temporary inspection flag, its child
  processes use `C:\Users\conno\AppData\Roaming\Hermes`, and zero test
  `electron.exe` processes remain.
- The managed backend base reports Hermes `v0.20.6`, commit `ecc9fe03046`, with
  Connor's local managed overlay. A post-switch parity audit compared all 17
  production overlay files with the signed post-rebase source: 17 matched, zero
  differed. Nine pre-rebase managed files were backed up, replaced
  transactionally, syntax-compiled, and reverified before the final restart.

## Fresh installed-package proof

The final package first passed hidden isolated fake-boot and real-backend smoke
tests. After installation, a direct live-renderer probe attached to the exact
canonical executable and normal profile. It observed the populated Hermes
renderer and Desktop bridge, obtained a protected loopback gateway URL without
recording its token, returned `setup.status`, listed all eight profiles, and
accepted all four native-notification classes. The temporary local inspection
launch was then closed gracefully and replaced by a clean pinned-shortcut
launch; the final process audit found no debugging flag and no test Electron.

Evidence:

- `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\deployment-report.json`
- `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\managed-runtime-sync.json`
- `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\installed-live-smoke.json`
- `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\installed-live-smoke.png`
- `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\final-readback.json`

## Native notification matrix

The implementation-defined four core chat notifications are:

| Title | Kind/type | Production trigger | Delivery rule |
| --- | --- | --- | --- |
| Approval needed | `approval`, native OS attention | `approval.request` | Fires while Hermes is away or for an off-screen session; includes approve/reject actions where the OS supports them. |
| Input needed | `input`, native OS attention | Clarify, MCP setup, sudo, or secret request | Fires while Hermes is away or for an off-screen session. |
| Hermes finished | `turnDone`, native OS completion | Successful `message.complete` | Fires only for the active session while Hermes is backgrounded. |
| Turn failed | `turnError`, native OS completion/error | Turn-ending gateway error | Fires only for the active session while Hermes is backgrounded. |

All four kinds are enabled by default, respect the master/per-kind preferences,
ignore the post-connect replay baseline, and deduplicate repeated events in the
renderer and Electron main process. The final installed canonical notification
bridge accepted one live test of each exact title through the normal profile.
The focused renderer and gateway-event suite passed 158 tests across 23 files.
No defect was reproduced, so no notification fix was necessary.

Evidence:

- `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\installed-live-smoke.json`

If Connor intended a different set of four events, item 32 should be reopened
with those exact titles; the four above are the core set defined by the current
Desktop implementation.

## Profiles, tools, accounts, and integrations

The final capability dry run reports eight current profiles, with 19 MCP
servers, 103 installed skill paths, and 37 static account/environment keys
enabled everywhere. It reports zero config changes, zero environment changes,
and zero skill copies needed. New profiles clone `default`; rotating OAuth
stores remain profile-local and must be authorized independently.

Home Assistant was freshly checked through its authenticated local API:

- Home Assistant Container `2026.8.3` is up with restart persistence.
- The API reports `API running.`, 95 entity states, 14 media players, 64 service
  domains, and zero unavailable entities.
- Supported Samsung, TCL Roku, LG webOS, Sonos, Google Cast, Android TV Remote,
  and network-reachability entities remain represented through Home Assistant.
- The free Home Assistant Chrome app remains the supported pinned Windows
  control surface; no paid third-party desktop client was introduced.

Tailscale remains online on the laptop. Telegram and WhatsApp use the separate
default gateway. Google personal/school services, read-only YouTube access, and
the previously verified Cloudflare, PayPal, Railway, Stripe, Twelve Data, and
Vercel MCP routes retain their recorded status. The complete secret-safe account,
scope, device, rollback, and revocation inventory is in
`HERMES_INTEGRATION_INVENTORY.md`.

The local LM Studio route remains optional: LM Studio `0.4.22+1` with
`qwen3.5-4b` Q6_K, Vulkan AVX2, 65,536 context, and parallelism 1. Hermes unloads
the model when idle to release scarce GPU/RAM; the no-cost cloud route remains
the normal default.

## Known optional or external gaps

- Indeed persists its OAuth grant but the provider endpoint returns
  `403 invalid_client: Client not allowed` outside its supported connector.
- Plaid requires Production approval plus protected Production credentials and
  a refresh-capable client-credentials route. No false browser-auth success is
  claimed.
- Official Nest camera/thermostat control requires Google's one-time US $5
  Device Access registration and is intentionally excluded under Connor's
  no-paid-services rule. Eero remains reachability monitoring rather than an
  unsupported control integration.
- Microsoft Graph personal delegated access is not a ready Hermes connector;
  iCloud on Windows is limited, and Xbox control is classified unsupported.
- The six unread sessions were preserved; no read state was changed.
- CodeRabbit CLI 0.7.5 is installed and authenticated in both supported WSL and
  signed native Windows modes. Every doctor check passes, but its no-cost review
  endpoint closed the WebSocket before analysis in full, light, agent, and
  plain modes. Usage remained zero, no findings were returned, and paid credits
  were not enabled.
- The signed branch is published to Connor's fork and upstream PR
  `https://github.com/NousResearch/hermes-agent/pull/98393` is open.

## Verification summary

- Post-rebase affected Python suite: 1,293 passed, five skipped.
- Post-rebase Desktop Vitest suite: 8,675 passed, 34 skipped in the initial
  saturated run; all 13 timed-out/environment-dependent cases passed in focused
  reruns. The bounded-worker full rerun then recorded 8,684 passed and 34
  skipped, with its only four failures confined to the same timing-sensitive
  `keys-settings.test.tsx` file. That complete file passed 4/4 immediately in a
  one-worker focused rerun with a 30-second timeout (its slow test took 13.1s,
  inside that limit but near the full suite's 15-second default).
- TypeScript typecheck, ESLint, Python compilation, `git diff --check`, secret
  shape scan, and all-profile capability read-back passed before packaging.
- Packaged candidate fake-boot and real-backend hidden smoke tests passed.
- Fresh post-install notification/session suite: 158 passed.
- Fresh hidden installed chat/tool smoke: one passed.
- Fresh hidden installed native-notification smoke: one passed.
- Final published-package live smoke: renderer, bridge, `setup.status`, eight
  profiles, and four notification kinds passed.
- Final process audit: canonical `Hermes.exe` relaunched from the pinned
  shortcut with the normal profile, no inspection flag, and zero
  `electron.exe`.

## Cleanup and rollback

Eleven obsolete Desktop release/test staging trees were permanently removed
after the clean package, installed smoke, native notifications, and rollback
path passed. The cleanup removed 1,382 files totaling 1,203,191,074 bytes. It
did not touch the canonical package or any current rollback material.

Recovery material:

- Pre-switch installed package and shortcuts:
  `C:\Dev\hermes-agent-recovery\installed-backup-pre-35c44b1d-20260830`
- Exact guarded rollback script:
  `C:\Dev\hermes-agent-recovery\installed-backup-pre-35c44b1d-20260830\restore-installed.ps1`
- Deployment's intact pre-switch package:
  `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\pre-switch-win-unpacked`
- Pre-repair managed runtime files:
  `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\managed-runtime-pre-rebase-sync`

The package switch and managed-runtime repair both completed through graceful
window closure; neither required a forced process stop.

## Publication readiness

The prior line is recoverable from
`codex/hermes-desktop-readiness-pre-rebase-20260830`. The active
`codex/hermes-desktop-readiness` branch was rebased with commit signing onto
`origin/main` at `26350357d76e4508c8df9304a3374bdc5a6f6220` and is now zero
commits behind and eleven commits ahead. Every local commit reports a good SSH
signature. The four upstream-deleted Hermes Bots files remained deleted, while
the OAuth conflict resolution preserves upstream's serialized resource lock,
the explicit interactive-authorization path, and both regression test classes.
A fresh merge-tree rehearsal is conflict-free. Publication, the published-HEAD
package, the canonical switch, the managed-runtime reconciliation, and the
normal-profile live smoke are complete. PR review and merge are the only
remaining external publication states; neither is required to use the verified
local Desktop installation.
