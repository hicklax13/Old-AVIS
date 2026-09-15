# Hermes security repair and Desktop verification

Completed September 13, 2026, on ASUS_PRO_LAPTOP. Final checks completed at
20:56 ET. This supersedes the earlier security review that said the upgrade
had not yet been installed.

## Installed result

Both `httpx2` and `httpcore2` are now **2.12.0** in the managed Python runtime
used by the CLI, Desktop backends, and messaging gateway. The separate test
environment also uses the patched versions. Only these two installed Windows
packages changed; all 142 installed packages remain compatible.

The canonical taskbar app was rebuilt, packaged, installed, and relaunched:

- Executable: `C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`
- Normal app data: `C:\Users\conno\AppData\Roaming\Hermes`
- Active source: `C:\Dev\hermes-agent\.hermes\hermes-agent`
- Hermes 0.21.2, Desktop package 0.17.2, Electron 41.10.3.
- Source: `a7254e2d4c170725a4136591e96efc5066251d2c` plus preserved local repairs.
- Final Desktop root PID: 42776. Messaging gateway PID: 68248, started after
  the dependency upgrade and reporting the same source SHA.
- Installed `app.asar` SHA-256:
  `a95975ea946cf5ffbcfbe783ffe3b42e79dc3d0c247a1eaaca5050034e54d031`.

Fresh audits run through the actual Desktop interface returned **0 known
vulnerabilities across 142 components**:

| Selected profile | Audit start time, ET | Result |
| --- | --- | --- |
| default | 20:48:22 | 0 findings / 142 components |
| default, repeated run | 20:48:45 | 0 findings / 142 components |
| reviewer | 20:54:11 | 0 findings / 142 components |

Each displayed timestamp was matched to that profile's actual action log.
Reviewer did not overwrite or display default's audit result. Historical
pre-repair findings remain in the append-only default log; the new runs are clean.

## Fixes that prevent the observed regressions

All three HTTPX2 pins in the active `pyproject.toml` (dev, MCP, and computer-use
extras) now require 2.12.0. The regenerated `uv.lock` selects matching HTTPX2 and
HTTPCORE2 versions, preventing normal dependency synchronization from restoring
the vulnerable 2.7.0 pins. The lock also includes upstream's conditional
`httpx2-jsfetch` dependency for Emscripten/Python 3.12+; it was not installed on
Windows. Other locked package versions did not change. `uv lock --check` passed.

The reported 12 entries represented five underlying vulnerability classes,
including duplicated advisory records and the TLS issue affecting both
distributions. Version 2.12.0 includes the highest required fix in the supplied
audit. See the [official HTTPX2 release notes](https://github.com/pydantic/httpx2/releases/tag/v2.12.0)
and [streamed decompression advisory](https://github.com/advisories/GHSA-8xx6-hgc6-gc2m).

Native verification also exposed a preexisting Desktop reporting bug:

1. Maintenance actions did not consistently carry the selected profile and
   connection to their launch request.
2. Electron sent action-result requests to the primary backend even when the
   selected profile's backend had launched the action. This could display an
   old audit from another profile.
3. Repeating the same maintenance action could leave its polling effect unchanged.

The renderer now captures the launch profile/connection and retains it for
polling, including after a profile switch. Each new launch restarts polling.
Electron routes process-local maintenance results to their owning backend.
Existing primary-backend routing for skills/MCP installs and gateway lifecycle
controls remains covered by tests. The same ownership correction covers the
related Doctor, backup, import, curator, checkpoint, update, and diagnostic actions.

## Validation

- 147 Python compatibility/security tests passed; one platform-specific test
  skipped. This covered MCP transport, TLS/client certificates, OAuth ownership,
  refresh/authentication paths, and security audit behavior using the repository runner.
- A real local HTTP MCP server completed initialization, tool discovery, and an
  actual tool call through Hermes' production transport. The gzip-compressed
  response expanded to 589,824 bytes and matched exactly. This passed in both
  the test and managed runtimes; the fixture was stopped afterward.
- 35 Desktop renderer tests passed. The five new profile/polling regressions
  failed before the first reporting fix and passed afterward.
- 132 Electron connection tests passed. Eleven new action-routing regressions
  failed before the routing fix and passed afterward.
- Renderer and Electron typechecks, focused lint, production build, and Windows
  packaging passed. The final packaged candidate launched hidden and passed a
  real native-terminal echo check. No visible development app was launched.
- All eight profiles were opened in canonical Desktop and showed Gateway ready:
  default, builder, development, google-personal, google-school, operator,
  researcher, and reviewer. Actual owned backends also answered readiness and
  session-list requests with matching profile identities.
- The app was left on default with all eight backends running. Eight warm slots
  and a seven-day idle timeout remain saved.
- Read-back confirms 15 matching enabled MCP definitions and nine explicit
  default OAuth owners across all profiles. Plaid, Strava, Indeed, and Unreal
  Engine remain removed as requested. No OAuth token stores were copied.
- Taskbar target and live executable match the canonical path. The installed
  package matches the validated candidate. No test `electron.exe` remains.
- All 78 preexisting tracked repair patches were preserved byte-for-byte.

These are focused validation results, not a claim that the entire repository
suite or every remote integration was exercised. The audit checks known
vulnerabilities; it does not establish that all software is vulnerability-free.
Cold reboot/sleep recovery and new model generations were not retested here.
External provider outages, revoked grants, and billing restrictions remain
outside a local connection repair. The previously identified xAI credit/spending
restriction still requires an account decision; no billing changes were made.

## Recovery and evidence

Evidence root: `C:\Dev\hermes-agent-recovery\security-upgrade-20260913`.

Recoverable originals include dependency package directories and metadata,
original manifests, source patches, and complete Desktop package backups. The
final deployment verified all 500 files in
`routing-final\win-unpacked-before` before promotion. A previous package is
also retained in the canonical release directory. Deployment was local; no
public release, Git commit, or push was performed.

Key evidence files:

- `native-final-proof.json`: installed Desktop profile checks and fresh audit timestamps.
- `all-eight-final-routing.json`: actual owned backend identities and readiness results.
- `final-process-proof.json`: canonical root, managed runtime versions, gateway, and package hash.
- `routing-final\deployment-proof.json`: candidate/install equality and verified rollback package.
- `audit-after.json`: machine-readable security audit, 0 findings / 142 components.
- `runtime-http-smoke.json`, `test-http-smoke.json`: real MCP transport invocation results.
- `compatibility-tests.log`, `desktop-reporting-green.log`, `routing-green.log`: passing tests.
- `desktop-reporting-red.log`, `routing-red.log`: reproduced pre-fix failures.
- `shared-mcp-after.json`, `preservation-proof.json`, `manifest-proof.json`: read-back and preservation checks.

Future upstream changes can still require merging local repairs. The installed
updater's existing required-restore guard stops when it cannot restore them;
neither future merge conflicts nor perpetual remote availability can be guaranteed.
