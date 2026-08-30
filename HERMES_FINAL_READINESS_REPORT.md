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

Remote publication is intentionally not complete. Connor must explicitly
authorize pushing/opening a PR, and the local line must first be reconciled
with the 479 newer commits on `origin/main`. Optional CodeRabbit review also
remains outside the delivered result because its CLI is not installed or
authenticated and running it sends code diffs to CodeRabbit.

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
- Connor still owns the decision to preserve or mark read the six unread
  sessions.
- CodeRabbit is optional and pending CLI installation, authentication, and
  explicit consent to upload the diff for review.
- Pushing and opening a PR remain pending Connor's explicit authorization.

## Verification summary

- Pre-build affected Python suite: 1,285 passed, five skipped.
- Pre-build Desktop Vitest suite: 7,998 passed, 34 skipped.
- Desktop plugin suite: 625 passed.
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

After a fresh fetch, local `main` is eleven signed commits ahead and 479 commits
behind `origin/main`. Every local commit reports a good SSH signature. A
read-only merge-tree rehearsal identified six conflicts before publication:

- Four modify/delete conflicts under the upstream-removed
  `apps/desktop/src/plugins/hermes-bots/` tree.
- Content conflicts in `tools/mcp_oauth_manager.py` and
  `tests/tools/test_mcp_oauth_bidirectional.py`.

No push, PR, rebase, or remote mutation has been performed. Reconciliation
must be followed by the relevant tests and a new clean Desktop build before the
rebased result can replace this locally verified package.
