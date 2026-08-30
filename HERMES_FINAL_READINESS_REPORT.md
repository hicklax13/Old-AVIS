# Hermes Desktop final readiness report

Verified 2026-08-30 on Connor's ASUS Windows 11 laptop. This report covers the
local delivered system. It does not claim that unpublished commits are on the
upstream repository.

## Delivery verdict

The canonical green Hermes Desktop installation is healthy and locally ready.
The clean package is installed at
`C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`, both
Windows shortcuts still target it, the normal-profile gateway reconnects after
a pinned-shortcut launch, and no test `electron.exe` remains. No Codex-owned
runtime or notification defect is open.

Connor authorized remote publication. The signed local line has been rebased
onto current `origin/main`, is zero commits behind and eleven commits ahead,
and has passed the post-rebase verification matrix. Branch publication and PR
creation are the active final handoff steps; the installed package described
below remains the last verified pre-rebase rollback point until the final HEAD
is rebuilt and switched canonically.

## Installed Desktop and runtime

- Desktop package version: `0.17.0`; Electron: `40.10.2`.
- Clean build stamp: commit
  `0bae5382b0653ba2a6f69830dcc025fddcbf45d3`, branch `main`, built
  `2026-08-30T04:27:27.837Z`, `dirty: false`.
- Installed executable SHA-256:
  `beff8d7d5cd4d9d17853da61096da07f994680e6953514249ffc481814c5bbd1`.
- Taskbar and Start Menu shortcuts resolve to the canonical executable and use
  its `win-unpacked` directory as the working directory.
- The live root process was relaunched through the pinned shortcut after final
  testing. The `google-school` backend accepted two renderer WebSocket peers at
  01:13:59 local time and started the eight-profile cron scheduler normally.
- The managed backend base reports Hermes `v0.20.6`, commit `ecc9fe03046`, with
  Connor's local managed overlay. A post-switch parity audit compared all 17
  production overlay files with the signed source: 17 matched, zero differed.
  Five stale managed files found during the first audit were backed up, replaced
  atomically, compiled, and reverified before the final restart.

## Fresh installed-package proof

A hidden, isolated test launched the installed canonical executable against the
real managed Python gateway and a local mock inference endpoint. It submitted a
real session, rendered three interim assistant messages, executed four safe
`todo` tool calls, and rendered the final answer. The bridge, renderer, gateway,
mock request, and tool loop all passed in 23.6 seconds without using an external
model, account credential, or paid service.

Evidence:

- `C:\Dev\hermes-agent-recovery\deploy-0bae5382-20260830\item31-installed-smoke.json`
- `C:\Dev\hermes-agent-recovery\deploy-0bae5382-20260830\item31-installed-smoke.png`
- `C:\Dev\hermes-agent-recovery\deploy-0bae5382-20260830\deployment-report.json`

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
renderer and Electron main process. The installed canonical notification bridge
accepted one silent test of each exact title from a hidden packaged instance.
The focused renderer and gateway-event suite passed 158 tests across 23 files.
No defect was reproduced, so no notification fix was necessary.

Evidence:

- `C:\Dev\hermes-agent-recovery\deploy-0bae5382-20260830\item33-installed-notifications.json`

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
- Pushing and opening the PR are authorized and in progress.

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
- Final process audit: canonical `Hermes.exe` relaunched; zero `electron.exe`.

## Cleanup and rollback

Eleven obsolete Desktop release/test staging trees were permanently removed
after the clean package, installed smoke, native notifications, and rollback
path passed. The cleanup removed 1,382 files totaling 1,203,191,074 bytes. It
did not touch the canonical package or any current rollback material.

Recovery material:

- Pre-switch installed package and shortcuts:
  `C:\Dev\hermes-agent-recovery\installed-backup-pre-0bae5382-20260830`
- Exact guarded rollback script:
  `C:\Dev\hermes-agent-recovery\installed-backup-pre-0bae5382-20260830\restore-installed.ps1`
- Deployment's intact pre-switch package:
  `C:\Dev\hermes-agent-recovery\deploy-0bae5382-20260830\pre-switch-win-unpacked`
- Pre-repair managed runtime files:
  `C:\Dev\hermes-agent\.hermes\backups\managed-runtime-item31-20260830T0058`

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
A fresh merge-tree rehearsal is conflict-free. Publication is authorized; a
new clean Desktop package and canonical installed smoke must be produced from
the final published HEAD before the older locally verified package is replaced.
