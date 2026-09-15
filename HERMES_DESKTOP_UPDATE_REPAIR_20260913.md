# Hermes Desktop update repair — 2026-09-13

## Confirmed failures

The pinned app and the updating runtime used different checkouts. The pinned
executable was `C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`,
but the active updater ran in `C:\Dev\hermes-agent\.hermes\hermes-agent`.
That managed checkout had no Desktop release directory. Runtime updates therefore
completed without rebuilding the installed app, and the final Desktop verifier
failed with `The updated Desktop executable is missing`. The handoff log records
this on September 13 at 10:36:28 ET, followed by relaunch of the old package.

A second route, Command Center → System → Update Hermes, directly called the
backend update endpoint while Desktop and its profile backends were still running.
The September 13 12:12:47 ET update refused to proceed because those processes
held native Python extension files open. Other Desktop update entry points already
used the coordinated shutdown and detached updater.

## Repair

- Connected the managed checkout's `apps/desktop/release` to the existing canonical
  release directory with a Windows directory junction. Both paths now identify the
  same installed package. The idempotent repair/read-back helper is
  `scripts/desktop-update/link-windows-release.ps1`; it refuses conflicting paths.
- Routed the System update button through `requestActiveUpdate()`, the shared
  Desktop update flow. Desktop closes its backends before replacement and restarts
  after verification.
- Preserved release junctions during ZIP fallback staging so a future fallback
  cannot silently create a second installed app.
- Retained one `.previous` Windows package after successful staged promotion.
- Removed the Windows handoff's automatic `--keep-stash`. Normal automatic
  stash/restore now retains the local repairs. Required automatic restoration
  failures stop the update instead of reporting success with repairs missing.
- Carried forward the existing explicit hidden-window test guard for isolated
  packaged smoke tests. Ordinary Desktop launches use their normal visibility path.

Implementation lives in the active managed checkout. The outer checkout retains
its existing development history and unrelated work. Future packaging for this
installation must use the managed Desktop source and the canonical release link.

## Verification

Before the real in-app update:

- System/update-store UI checks: 69 passed. The new System-button regression failed
  before the fix and passed afterward.
- Electron update, handoff, visibility, and teardown checks: 110 passed, 1 skipped.
- Focused native Windows updater checks: 18 passed, including actual junction
  staging/promotion/rollback and required-stash restoration. Regressions failed
  before their fixes. Earlier ZIP/package checks: 30 passed.
- Desktop renderer, Electron, and E2E TypeScript checks passed; focused ESLint passed.
- A packaged candidate booted with a rendered UI in a separate temporary profile,
  with every window hidden. It closed afterward; no test Electron process remained.

Broader diagnostic suites returned 80 passed, 20 failed, and 16 skipped: three
GUI fixtures use invalid dummy executables, and the autostash suite has additional
failures including temporary commits blocked by global Git signing. Not all 20
failures were individually established as pre-existing. The original captured
output is preserved in the evidence directory; this is not a full-suite green claim.

The real installed-app update started at 12:45:15 ET. It released the Desktop
process and venv shim, pulled 16 commits, and restored the local source repairs.
The tracked repair patch and all five untracked source/test files read back
identically after that update (`repair-retention.json`). The updater exited 0 at
12:54:50, passed its final verifier, cleared its marker, relaunched the canonical
app, and acknowledged success at 12:54:55. The normal-profile backend was ready
at 12:55:10.

Final read-back:

| Check | Verified result |
| --- | --- |
| Latest published release | [Hermes Agent 0.21.2, v2026.9.11](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.9.11) |
| Runtime | 0.21.2, commit `5dea46d13deec9549bdc2ea703ae9201d733c28d` |
| Release inclusion | Release commit `939e45c91d751fadd94dcd1b873ac3cb44846213` is an ancestor of the installed runtime |
| Installed Desktop package | 0.17.2, read directly from the packaged ASAR manifest |
| Electron executable | 40.10.2; this is the executable resource version, separate from the Desktop package version |
| Packaged source | Commit `5dea46d13dee`, built `2026-09-13T16:51:35.745Z`, with the local repairs |
| Final verifier | PE/ASAR/renderer validation passed; `buildNeeded: false` |
| Canonical process | PID 68156, exact pinned executable; four children identify the normal Roaming/Hermes profile |
| Pinned shortcut | Invoked again at 13:00:27 ET and resolved to the updated normal-profile app |
| Installed UI | `Gateway ready`, `v0.21.2 5dea46d`, all seven named profiles present; System displayed `Hermes 0.21.2 · Active sessions 0` |
| Recovery | `win-unpacked.previous` exists; original pre-repair package also retained separately |
| Process cleanup | Original updater exited; no `electron.exe` test processes or debug instances remained |

The existing `main` update channel was retained, so this installation includes the
latest published release plus subsequent upstream fixes and these local repairs.
The normal profile also displayed MCP reauthentication notices. Account consent
work is separate from this updater repair.

The two reproduced update failures are fixed and the installed update completed.
No updater repair work remains. Other readiness items and account-consent tasks
retain their existing status.

## Recovery and evidence

`C:\Dev\hermes-agent-recovery\desktop-update-20260913` contains the original
installed package, pinned shortcut, package manifest, source repair patch, copies
of untracked regression files, and validation logs. The original package backup
was read back and verified file by file: 457 files, 401,100,946 bytes.

The original four unrelated working-tree edits were preserved byte for byte as a
Git binary diff (SHA-256
`A592AD3109FC6387B127B8A6CEA2F153571D78FD9A169AD17F95F313930F282B`).
No commits or pushes were made by this repair.

The canonical release also retains `win-unpacked.previous` after promotion. Any
package rollback must first close the app and confirm that no updater is active;
preserve the current package before restoring a verified previous package. This
is a Desktop package recovery path, not a rollback of runtime or profile data.
