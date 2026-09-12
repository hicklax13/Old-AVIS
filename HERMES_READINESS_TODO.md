# Hermes CLI and Desktop Readiness TODO

Originally saved on 2026-08-27 after the CLI, Desktop, notification, setup, Git,
dependency, and test review. Comprehensively re-audited on 2026-08-31 across the
repository, project-task history, canonical Desktop installation, normal and
profile-scoped runtime state, integrations, services, backups, permissions, and
live logs.

## Ownership

- **Codex**: Codex can complete the item without Connor's input once its listed
  prerequisites are satisfied.
- **Connor**: Only Connor can complete the item.
- **Both**: Codex can do some or most of the work, but Connor must provide a
  decision, authorization, credential, authentication step, or confirmation.

Routine sandbox or operating-system approval prompts do not change an item's
owner. They authorize execution but do not require Connor to investigate or
make the implementation decision.

## Preserved baseline (2026-08-27)

- Working checkout `main`: `34e9f395e1fca34080a6ec836587c2107aecef0e`.
- Working checkout's then-fetched `origin/main`:
  `8966b0a70029cb226e35c49f91d0c2208ab1d8c4`.
- Working checkout carried commits: `2f4afe20e0` and `34e9f395e1`.
- Working-checkout rollback branch:
  `codex/hermes-readiness-pre-update-20260827`.
- Installed runtime `main`: `c863abf556ce69f3aaeda5ccb4273023191fbd1f`.
- Installed runtime's then-fetched `origin/main`:
  `f6f707b78317530980e1d0bf5ca77c8464a9148b`.
- Installed runtime carried commits: `cb354f9cd` and `c863abf55`.
- Installed-runtime rollback branch:
  `codex/hermes-readiness-pre-update-20260827`.
- Canonical Desktop build stamp: commit `13f4cfebfafbce8ac9d1bf29f66731858ed638b5`,
  built `2026-08-22T19:21:53.016Z`, dirty local build.
- Alternate `release-codex-3` stamp: commit
  `34e9f395e1fca34080a6ec836587c2107aecef0e`, built
  `2026-08-27T05:48:03.513Z`, clean local build.
- `release-codex` was incomplete and had no install stamp.

## Actual Hermes Desktop deployment invariant

- Connor uses only Hermes Desktop and does not use Hermes CLI. Codex may invoke
  CLI commands internally for administration or diagnostics, but must not leave
  Connor with CLI-only instructions or count a CLI-only result as complete.
- The authoritative green Hermes Desktop app on this laptop is
  `C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`.
  The pinned taskbar shortcut must resolve to that exact executable, and the
  live app must use the normal profile at
  `C:\Users\conno\AppData\Roaming\Hermes`.
- Playwright, development, staging, `release-codex*`, and other isolated app
  instances are validation surfaces only. They are never the installed result
  and must be closed after testing. Never launch a visible blue-accented
  Electron/Playwright test instance on Connor's active desktop. E2E validation
  must use a proven hidden or otherwise isolated path, followed by a process
  audit confirming that no temporary `electron.exe` remains and the only
  visible Hermes window is the authoritative green app.
- A future Hermes Desktop implementation item is not deployment-complete until
  Codex builds and tests the source, packages it in a separate staging folder,
  preserves the prior `release\win-unpacked` directory as a recoverable backup,
  switches the staged package into the authoritative path, relaunches that
  exact executable, and verifies the live process, normal profile, taskbar
  shortcut target, and packaged build stamp.
- CLI/runtime-only changes remain separate unless the Desktop app consumes them
  through its managed backend. Desktop-visible changes must satisfy the full
  deployment check above even when their source tests already pass.

## Comprehensive audit refresh (2026-08-31)

This audit used repository-wide automated scans plus line-level review of the
shipped branch, the accessible project-task history, the canonical Desktop and
normal profile, all eight Hermes profiles, live MCP/service diagnostics, Windows
process/service/shortcut checks, ACL inspection, backup-content inspection,
database integrity checks, dependency audits, and focused/full-suite test
probes. It does not claim that 10,726 tracked files were each read manually.

Verified healthy evidence:

- The taskbar/Start shortcuts and live root process still resolve to the
  canonical `release\win-unpacked\Hermes.exe`; all visible Hermes processes use
  that package and no test `electron.exe` remains.
- All eight profiles still have 19 MCP definitions, 103 installed skill paths,
  and 37 environment-key names with zero config, environment, or skill drift.
- All 69 Hermes SQLite databases and the Home Assistant recorder database pass
  `PRAGMA quick_check`; all Home Assistant JSON storage records are valid.
- The 1,293 changed-surface Python tests pass with five skips. Desktop Electron
  tests pass 1,936 with 34 skips. TypeScript typechecking passes. The packaged
  canonical app, installer, install stamp, renderer payload, and native PTY
  payload validate without rebuilding or launching a test window.
- The Desktop production dependency audit and the installed Python-runtime
  vulnerability audit report zero known vulnerabilities. Added-line scans of
  the current branch and its 15-commit history found no recognized raw secret
  patterns. `git fsck` reports no corruption, `git diff --check` passes, and all
  15 branch commits have good signatures.
- Home Assistant 2026.8.3, n8n 2.35.7, SearxNG, Tailscale, Telegram, WhatsApp,
  and the Hermes gateway are running. Home Assistant reports 95 entities and
  zero `unavailable` entities; nine are `unknown`, mostly expected event,
  location, backup, and service entities, plus two Roku active-app sensors that
  need the focused follow-up below.

The evidence also invalidates the prior blanket “fully ready” conclusion. The
open findings below are ordered by current security risk, active exposure,
failure impact, and completion value. Item 25 remains deliberately removed.

## Open audit follow-ups — ordered by priority and value

- [x] 40. **Codex** — Lock down sensitive local state and every writer that can
  recreate it. `C:\Dev\hermes-agent\.hermes`, Home Assistant's config and
  `.storage` auth records, n8n state, WhatsApp linked-device state, SQLite data,
  state snapshots, and existing backups previously inherited read access for
  `BUILTIN\Users` and modify access for `Authenticated Users` plus other broad
  local principals. The explicitly protected `.env` and `mcp-tokens` trees are
  not enough. Establish Connor-and-SYSTEM or narrowly service-scoped ACLs,
  preserve Docker/Desktop operation, remove stale broad inheritance only after
  resolving required principals, and add read-back tests to every credential,
  snapshot, and backup writer (including profile-capability sync).
  Completed 2026-09-01: centralized private-path handling and writer read-backs
  now cover auth, backup, profile, OAuth, WhatsApp, and capability-sync paths.
  Verify-only ACL audits passed for 553,830 Hermes-state objects and 779 Home
  Assistant config objects. The 975-file coherent managed-backend deployment
  had zero hash mismatches, its recoverable backup verified private, both live
  Desktop profile backends returned HTTP 200, and the focused security suite
  passed 268 tests with 10 intentional skips.
- [x] 41. **Both** — Contain and reconstruct the public upstream contribution.
  PR `NousResearch/hermes-agent#98393` was open, 354 upstream commits behind,
  conflicting, has no checks or reviews, and combines about 140 changed files
  with Connor-specific policy and readiness documents that publicly disclose
  personal accounts, email addresses, device/home topology, integrations, and
  local paths. Codex should prepare a private/local home for the personal
  runbooks, remove the operational material from the complete public branch
  history, preserve contributor authorship/signatures, split the product work
  into focused reviewable PRs, rebase on current upstream, and re-run each
  affected validation matrix. Connor must authorize the public close/replace or
  history rewrite before Codex changes the remote PR.
  Completed 2026-09-01 with Connor's authorization: public PR `#98393` is
  closed, the private recovery archive is retained, and the product work is
  reconstructed as 12 focused PRs: `#99783`, `#99784`, `#99785`, `#99786`,
  `#99787`, `#99790`, `#99792`, `#99796`, `#99798`, `#99800`, `#99802`, and
  `#99803`. Current GitHub read-back confirms the replacement PRs exist and
  remain independently reviewable against `main`.
- [x] 42. **Both** — Replace the current backup arrangement with a real,
  encrypted, least-privilege, restore-tested recovery system. The prior daily
  `Hermes Project Safe Backup` task returned `0x800710E0`, refused starts
  on battery, and did not catch up later. Its “credential-excluding” archive
  included n8n's encryption key beside its database and logs, while
  all archives inherited broad ACLs. The Home Assistant “pre-Sonos backup” contained
  only `compose.yaml` and `configuration.yaml`, not `.storage`, the recorder,
  auth/device registries, or a tested restore. Select a protected recovery-key
  and destination policy, take application-consistent snapshots, separate or
  encrypt secret-bearing data, add retention and missed-run recovery, exercise
  a clean restore, and record objective proof without exposing secrets.
  Completed 2026-09-01: the encrypted age-based recovery workflow uses
  application-consistent SQLite snapshots, private staging and manifests,
  retention, isolated restore verification, and matching-hash local plus
  OneDrive ciphertext destinations. The scheduled task is Ready, last result
  `0`, runs on battery, catches up after missed starts, and next runs at 03:30
  ET. The latest successful archive contains 5,939 files and 49 SQLite
  snapshots; its restore was exercised without overwriting live state.
- [ ] 43. **Both** — Complete a credential-exposure response after items 40 and
  42 prevent re-exposure. There is no evidence of unauthorized use, but broad
  local ACLs covered pre-update archives containing profile `.env` files and
  protected state, and earlier project chats contain an n8n password/API token
  plus one-time OAuth callback codes. Inventory the affected issuers without
  printing values; rotate the n8n account password/current API token, replace
  the excessive-scope classic GitHub PAT with least-privilege credentials,
  revoke/reissue Home Assistant, Telegram, WhatsApp linked-device, provider API,
  and OAuth material actually present in exposed archives, and verify old
  credentials fail. Connor handles official sign-in, consent, and revocation;
  Codex handles the secret-safe inventory, protected updates, and verification.
  Parked by Connor on 2026-09-01: stop rotating tokens that are working fine.
  A fresh secret-safe inventory covers 34 issuers across 10 archive records,
  contains no credential values, and is protected with zero broad ACL entries.
  The explicitly requested n8n, least-privilege GitHub, and Home Assistant
  rotations are complete and verified; all other working Telegram, WhatsApp,
  provider, and OAuth credentials remain untouched. Reopen only on evidence of
  compromise or a new explicit rotation request.
- [x] 44. **Codex** — Correct the all-profile capability synchronizer so it
  enforces Connor's policy without treating every `.env` entry as a globally
  copyable “static account key.” Add an explicit classification/allowlist for
  shared static keys versus profile-local identities, rotating OAuth, device
  sessions, and service-local secrets; reject ambiguous keys and conflicts
  before writes; secure backup copies; test migrations and rollback; preserve
  default-profile cloning; and finish with an eight-profile zero-drift read-back.
  Completed 2026-09-01: shared static keys now use an explicit classification,
  ambiguous and conflicting values fail before writes, service-local and OAuth
  state stay profile-local, backups are private, replacement is rollback-safe,
  and default remains the new-profile baseline. After promoting the current
  portable Google Workspace helper into canonical `default`, six recoverable
  skill replacements converged all profiles. Final read-back: 8 profiles, 19
  MCP servers, 103 installed skill paths, 17 shared static keys, 20 deliberately
  unmanaged local keys, and zero config, env, skill-copy, or replacement drift.
- [x] 45. **Codex** — Fix OAuth refresh-token persistence before the next token
  expiry recreates the browser-loop problem. Hermes' custom successful-refresh
  handler replaces the complete token object and, unlike the pinned MCP SDK,
  does not carry forward the prior refresh token or scope when an RFC-compliant
  provider omits either field. Preserve both values, retain safe expiry and ACL
  behavior, cover omitted/rotated refresh tokens and scopes in regression tests,
  and verify a controlled refresh plus cold canonical-Desktop restart.
  Completed 2026-09-01: the successful-refresh override now carries forward an
  omitted refresh token and scope while accepting provider-supplied rotations.
  Controlled persistence checks cover expiry and private ACL read-back; the
  complete OAuth module passed 65 tests with 1 intentional skip and Ruff is
  clean. The managed file matches source after a private rollback backup, and a
  cold pinned-app restart produced one visible canonical window, one renderer,
  two HTTP-200 profile backends, no test Electron process, and no new OAuth
  authorization event in the startup log.
- [x] 46. **Codex** — Make MCP health and diagnostics noninteractive,
  truthful, and sticky. Terminally parked servers currently retry during
  recurring health checks and produced 47 Desktop OAuth prompts plus repeated
  Strava, Indeed, Plaid, and Unreal Engine errors. Health checks must never open
  a browser; initial OAuth should be lazy and user-invoked; terminal failures
  should remain parked until config/credential/user action changes; and
  `hermes mcp test` must offer a fully noninteractive mode and return nonzero on
  missing auth or failed health. Apply Connor's no-paid-services policy by
  classifying paid Plaid Production as inactive, classify absent Unreal Engine
  locally, and give Strava/Indeed accurate official-support states without
  repeated consent loops while keeping the 15 currently healthy MCPs usable.
  Completed 2026-09-01: automatic Desktop probes and the REST/CLI diagnostic
  paths now suppress interactive OAuth; missing auth and failed health return
  explicit non-retryable failures and CLI exit code 1. Terminal failures stay
  parked across timer ticks until a manual retry, reconnect, or configuration
  fingerprint change. All eight profiles converge with 15 active MCPs and the
  same four reasoned inactive entries: Indeed, Plaid, Strava, and Unreal Engine.
  Regression proof passed 165 Python tests with 1 intentional skip, 37 Desktop
  tests, typecheck, Ruff, ESLint, and Prettier. The rebuilt pinned canonical app
  has one visible window and renderer on the normal profile, two HTTP-200
  backends, zero test Electron processes, and its live Indeed probe returned a
  non-retryable missing-token result with no Chrome process launch. Gateway,
  storage, dashboard, and all 3 configured messaging platforms report healthy.
- [x] 47. **Both** — Remove the Figma client-identity impersonation and use an
  officially supported path. Current code registers Hermes as `Claude Code` to
  bypass Figma's client allowlist, but Figma's official MCP documentation says
  only catalog-listed clients may connect and directs new client developers to
  its waitlist. Codex should remove the spoof from the product/public PR and
  provide a clean disabled/unsupported state or an officially registered Hermes
  client. Connor chooses whether to disable Figma in Hermes for now or submit
  the official waitlist/registration; no unofficial impersonation counts as a
  finished integration.
  Completed 2026-09-01 using the safe disabled route authorized by Connor's
  request to complete all five items: Hermes no longer injects `Claude Code`
  or any other catalog client's identity, and Figma registration failures now
  direct users only to Figma's official catalog/waitlist path. Figma is
  reasoned-inactive in all eight profiles; existing OAuth state was retained
  but not used or rotated. A missed API contract was also fixed so Desktop
  visibly explains the inactive state. Proof: 67 focused Python tests passed
  with 1 intentional skip, Ruff/typecheck/ESLint/Prettier are clean, the
  synchronizer reports zero profile drift, and the rebuilt pinned canonical app
  read back 14 active/5 inactive MCPs with the Figma reason visible in every
  profile, one renderer/window, two healthy backends, 3/3 messaging platforms,
  and zero test Electron processes.
- [x] 48. **Both** — Replace the YouTube account skill's unsafe manual OAuth
  flow. It deliberately redirects to `http://localhost:1`, relies on Chrome's
  unsafe-port error, asks Connor to paste the full callback URL/code into chat,
  can skip state validation for code-only input, passes secrets in process
  arguments, installs unpinned runtime dependencies, and has no focused tests.
  Build a Desktop-mediated or ephemeral loopback PKCE flow with mandatory state
  validation, protected per-profile token storage, declared/pinned dependencies,
  cancellation/error handling, and tests; then have Connor complete only the
  official browser consent and verify a cold-restart read-only call.
  Completed 2026-09-01 without rotating either working grant. The skill now
  uses an ephemeral `127.0.0.1` callback, PKCE, mandatory constant-time state
  validation, an in-memory authorization response, a bounded wait/cancel path,
  and private atomic credential replacement that preserves an omitted working
  refresh token. The unsafe port-1/manual callback flags are gone, six Google
  dependencies are exactly pinned, and all eight profiles read back identical
  public skill code with protected user/SYSTEM-only credential ACLs. Proof:
  1,245 focused/authoring tests passed (including a real loopback callback),
  Ruff and diff checks passed, profile sync reports zero drift, and the pinned
  canonical Desktop cold-started with two HTTP-200 backends that both expose the
  enabled `youtube-account` skill. Personal and school profiles each passed an
  authenticated read-only channel call after restart; both refresh credentials
  remained unchanged, so no unnecessary browser consent was requested.
- [x] 49. **Both** — Decide and enforce the intended Home Assistant network
  boundary. Port 8123 is bound to all interfaces and is reachable through this
  laptop's Wi-Fi and Tailscale addresses; port 1400 is also bound globally for
  Sonos callbacks. Connor chooses local-only, selected private-LAN, Tailscale,
  or intentionally remote access. Codex then binds and firewalls each port to
  the minimum required interfaces/subnets/devices, preserves Sonos callbacks,
  confirms unauthenticated API access remains denied, adds TLS/reverse proxy
  only if genuinely needed, and re-verifies the PWA and Hermes tools.
  Completion evidence (2026-09-01 EDT): Connor selected Home Wi-Fi plus
  Tailscale with no public-internet exposure. Docker now publishes ports 8123
  and 1400 only on `127.0.0.1`; three narrowly scoped Windows port proxies and
  firewall rules expose HA UI/API to the trusted `192.168.4.0/22` Wi-Fi subnet,
  UI/API to the private `100.64.0.0/10` tailnet, and Sonos callbacks on port
  1400 only to the eight discovered Sonos addresses. The Wi-Fi and Tailscale
  interfaces are Private, there are exactly five intended listeners, and there
  are zero `0.0.0.0`/IPv6 all-interface listeners. Unauthenticated `/api/`
  requests returned 401 through loopback, Wi-Fi, and Tailscale; the protected
  authenticated API returned 200. A DHCP-aware elevated scheduled maintainer
  runs at logon and every five minutes, reconciles the exact interface address,
  rules, proxies, Sonos advertise address, and container only when necessary;
  its Windows PowerShell 5.1 atomic-replacement edge case was found and fixed,
  then an idempotent scheduled run exited 0 without recreating the container.
  After a controlled HA restart with the boundary active, a 62-second startup
  observation showed zero Sonos subscription/callback failures and zero
  unavailable/unknown states among the 51 returned Sonos entities. The pinned
  Chrome PWA launched to `Home Assistant - Overview`, and both canonical green
  Desktop backends returned HTTP 200 with Home Assistant enabled, configured,
  available, and all four `ha_*` tools present. TLS/reverse proxy was correctly
  omitted because no public exposure was selected. A pre-change backup is at
  `C:\Dev\home-assistant\backups\task49-network-boundary-20260901T054821Z`.
- [x] 50. **Both** — Repair and re-prove the Home Assistant device layer. The
  last 24 hours contain repeated Sonos subscription/favorites timeouts for the
  Portable and TV Room speakers, and the Roku active-app sensors remain
  `unknown` even though no entity is `unavailable`. Codex should diagnose power,
  addressing, discovery, callback, and polling behavior; classify expected
  unknown event/backup/location/service entities; reduce persistent error log
  noise; and run safe read plus explicit user-approved control checks for every
  Samsung, Roku, LG, Sonos, Nest/Google Cast/TV Remote, and supported network
  path. Connor handles powered-off devices, pairing prompts, and any disruptive
  playback/control confirmation.
  Completion evidence (2026-09-01 EDT): Connor explicitly approved the live,
  reversible control matrix. Safe refresh/read checks covered all 70 active
  device entities and all eight Hermes profiles; every profile returned the
  same 14 media players, and the canonical green Desktop's default and active
  `google-school` backends both report Home Assistant enabled, configured,
  available, and exposing all four `ha_*` tools. Control checks preserved
  volume/mute state on the LG display, both Nest Hubs, and all five visible
  Sonos rooms; woke and restored both Chromecast/Google TV Remote paths; and
  woke/restored the Roku TV. While Roku was on, its active-app sensors changed
  from `unknown` to `Home` and a concrete app ID, proving that their normal
  `unknown` state is standby behavior rather than a polling failure. Samsung
  power-off/on was also proved end to end. Docker Desktop could not reliably
  deliver Samsung Wake-on-LAN onto the physical Eero LAN, so a fixed-target
  Windows relay now listens only on `127.0.0.1:17655`, rejects non-loopback
  callers, and is maintained by the limited-user scheduled task
  `HermesHomeAssistantSamsungWakeRelay`; neither the Wi-Fi nor Tailscale address
  accepts that port. Home Assistant's official `samsungtv.turn_on` trigger now
  calls the relay, and a cold control test woke the TV from `off` to `on` in ten
  seconds. A separately measured successful Samsung shutdown took 31.55
  seconds, exposing Hermes' false 15-second failure; the source and installed
  managed runtime now allow 45 seconds for service actions and 60 seconds for
  the async bridge. Both focused copies pass 39/39 tests without warnings and
  compile cleanly; the canonical Desktop was relaunched against the repaired
  runtime. Sonos topology classified three bonded satellites and the ZB100
  bridge as intentionally invisible; all five visible rooms are available,
  Portable and TV Room each returned 56 favorites and 16 playlists, and the
  old callback failures did not recur after item 49's firewall repair. After
  the final controlled HA restart there are 96 states, zero unavailable
  entities, exactly nine expected unknown stateless/backup/location/Roku-
  standby entities, and zero fresh warnings or errors. Loopback, Eero Wi-Fi,
  and Tailscale authenticated paths all returned HTTP 200; the laptop's live
  default route is SSID `Eero Hickey` through `192.168.4.1`. Eero's standard
  UPnP/IGD advertisement is visible to Windows but not to the secure Docker
  bridge, so no unsupported custom Eero component or multicast-relay exposure
  was added. The paid Nest SDM route remains deliberately skipped under
  Connor's no-real-money rule; the two Nest Hubs are fully covered by Google
  Cast. The pinned Home Assistant PWA is open at `Home Assistant - Overview`.
  Pre-change backups are at
  `C:\Dev\home-assistant\backups\task50-device-layer-20260901T065029Z` and
  `C:\Dev\hermes-agent\.hermes\backups\task50-device-layer-20260901T065029Z`.
- [x] 51. **Both** — Move Cloudflare from `codemode=false` and 3,408 advertised
  tools to its official Code Mode search/execute pattern, which keeps the large
  OpenAPI schema outside model context. Preserve trust/approval boundaries,
  confirm the reduced tool surface and representative read-only operations in
  canonical Desktop, and verify persistence after restart. Connor completes a
  new official grant only if changing the resource invalidates the existing one.
  Completed September 1, 2026. All eight profiles now enable Cloudflare at the
  official `https://mcp.cloudflare.com/mcp` endpoint with `auth: oauth`,
  `trust: untrusted`, and no legacy 3,408-tool filter; the catalog manifest and
  user guide use the same future-install baseline. Static capability sync made
  recoverable backups, changed all eight configs, and its final dry run found
  zero remaining changes. The MCP annotation reader now accepts both the wire
  `readOnlyHint` and Python SDK `read_only_hint`, so Cloudflare's `docs` and
  `search` bypass approval while unannotated `execute` still fails closed to the
  existing per-call gate. Connor completed the replacement official OAuth grant
  for the active `google-school` profile; OAuth stores were not copied between
  profiles. Real calls passed: `docs` returned documentation, `search` found
  `GET /accounts`, and a separately approved GET-only `execute` returned HTTP
  200 with only an account count. The canonical pinned Desktop was relaunched;
  its root executable and shortcut remained canonical, the active profile was
  `google-school`, Cloudflare still showed exactly three enabled tools, and an
  in-app post-restart session reported `Used 2 tools`, `docs: PASS`,
  `search: PASS`, and `GET /accounts`. The smoke test also exposed and fixed a
  duplicate stdio-watcher coroutine construction; the source and managed
  runtime are identical and the focused trust/catalog/fast-fail suite passes
  51/51. No test Electron process remained. Pre-change recovery material is at
  `C:\Dev\hermes-agent\.hermes\backups\task51-cloudflare-codemode-20260901T163012Z`.
- [ ] 52. **Codex** — Implement a real Windows event-loop liveness witness for
  the gateway. The live gateway logs show `asyncio.start_unix_server` is absent
  on Windows, so the loop-tick socket is unavailable and stale-heartbeat probes
  cannot escalate if the event loop wedges. Use an authenticated named pipe or
  loopback mechanism with cleanup and identity checks, add Windows failure and
  recovery tests, deploy it canonically, and prove controlled wedge detection,
  graceful recovery, and normal Telegram/WhatsApp/Home Assistant continuity.
- [ ] 53. **Codex** — Repair the canonical Windows Python test harness and
  finish a trustworthy complete suite. The runner discovered 3,408 files and
  about 35,474 tests but accumulated 18 failures/errors by 5.8%, repeatedly
  failed to write `.pytest_cache`, mishandled Windows HOME/symlink/npm/file-URI
  behavior and Git signing, created a literal `%SystemDrive%` tree in the repo,
  lacked expected development dependencies, and allowed synthetic test crash
  records into the live Hermes log. Enforce an isolated temporary HERMES_HOME,
  complete Windows location variables, no live-state writes, no workspace
  pollution, deterministic timing, correct dependencies, and a full zero-fail
  per-file run before relying on repository-wide green claims.
- [ ] 54. **Codex** — Return the Desktop renderer/E2E matrix to clean green.
  The ordinary UI run currently has 6,740 passes and 12 failures across keys
  settings, provider settings, and Windows cron shell escaping; the focused
  settings files pass but the cron failure reproduces alone. Resolve suite
  isolation and portable literal-argument handling, the unawaited-coroutine
  warning, the remaining ESLint `document` warning, and Vite's future
  `__dirname` incompatibility. Then fix and enable the two explicit warm-resume
  `test.fixme` regressions (third transcript rebuild and post-inference repaint)
  and run the complete hidden/isolated Desktop matrix with a final process audit.
- [ ] 55. **Codex** — Close remaining secret-bearing log and diagnostic paths.
  The Desktop logs full denied `window.open` URLs including query/fragment data,
  MCP diagnostics retain credential prefixes/suffixes, and OAuth callback URLs
  can reach persistent logs. Log only safe origin/path plus structured error
  classes, fully redact headers/codes/tokens/client secrets, test malicious URL
  and traceback cases, and validate existing logs/backups without echoing values.
- [ ] 56. **Codex** — Clean the local SearxNG configuration. Searches work and
  return results, but startup/runtime logs show failed Ahmia/Torch/Wikidata
  engines, a missing limiter configuration, missing forwarded-address warnings,
  and recurring CAPTCHA/rate-limit responses from several engines. Disable
  unsupported engines or supply their declared dependencies, configure a
  loopback-appropriate limiter/proxy policy, retain multiple healthy engines,
  and verify useful results with a quiet error log and no public listener.
- [ ] 57. **Codex** — Establish reproducible container-image security and update
  maintenance. Home Assistant Compose uses the mutable `stable` tag while n8n
  and SearxNG are digest-pinned; the attempted Docker Scout CVE audit failed or
  stalled on Windows and therefore produced no trustworthy container finding.
  Use a reliable no-cost scanner, triage high/critical results against vendor
  releases, pin tested digests/versions, document backup-before-update and
  rollback, and re-run health/device checks after controlled updates.
- [ ] 58. **Both** — Perform one planned cold Windows reboot acceptance test
  after the security, backup, OAuth, service, and package fixes. Verify Docker
  Desktop startup and all container restart policies, the canonical pinned
  Hermes app and normal profile, gateway/channels, all-profile capability
  baseline, OAuth persistence without surprise tabs, Home Assistant PWA/devices,
  Tailscale, n8n, SearxNG, LM Studio idle behavior, task scheduling, and absence
  of duplicate/stale processes. Connor chooses the maintenance window and
  handles any device unlock/sign-in; Codex captures the proof and remedies.
- [ ] 59. **Codex** — Reconcile every tracked readiness artifact only after the
  preceding findings are genuinely closed. Update the final report, integration
  inventory, PR draft, this checklist, stale blocker text, test counts, MCP
  states, Home Assistant behavior, backup/rollback instructions, and public/private
  boundaries. Do not restore item 25 or claim “fully ready,” “zero failures,”
  conflict-free publication, or external completion without fresh evidence.

## Ordered checklist

- [x] 1. **Both** — Repair Git commit signing. Verified on 2026-08-27 that the
  configured SSH key exists outside the review sandbox, matches both local
  commits, and successfully signs and verifies a fresh Git object. No change
  was required.
- [x] 2. **Connor** — Connor saved active work and closed Hermes Desktop for the
  2026-08-27 maintenance window.
- [x] 3. **Codex** — Preserve the current state: refs and build stamps are
  recorded above, and verified local rollback branches preserve both copies of
  the two carried commits.
- [x] 4. **Codex** — Rebased the working checkout's two local commits onto
  current `origin/main` (`39f1e1881a`). The rebased commits are `186472992f`
  and `1d6623be32`; their signatures, patch equivalence, whitespace checks, and
  four focused regression tests all passed.
- [x] 5. **Both** — Updated the separately installed Hermes CLI/runtime to
  v0.20.6 on upstream `a24c12d14f`, with a full 292.6 MB pre-update backup at
  `.hermes/backups/pre-update-2026-08-27-155321.zip`. Restored carried commits
  `75c6dc526` and `ecc9fe030`; signatures, patch equivalence, and focused tests
  passed. The gateway is running the updated code.
- [x] 6. **Codex** — Reconciled the working checkout and installed runtime on
  upstream `a24c12d14f`. The working checkout carries equivalent signed commits
  `e4bc3a4a32` and `cd74f42745`; both repositories are exactly two commits ahead
  of the same upstream base.
- [x] 7. **Both** — Upgraded the user and Windows system npm installations from
  unsupported 11.16.0 to 11.17.0. Verified the default `npm` command, bundled
  npm CLI, Node 24.18.0 compatibility, Hermes engine range, and repository
  package-age exclusion configuration.
- [x] 8. **Codex** — Refreshed workspace dependencies and installed
  `@playwright/test` 1.62.1 plus its matching Chromium and headless-shell
  binaries. `npm ls --workspace apps/desktop --depth=0` and the local
  Playwright version check pass; the production dependency audit reports zero
  vulnerabilities. Generated lockfile metadata churn was removed.
- [x] 9. **Codex** — Fixed the Windows computer-use screenshot fixture to
  generate its payload with `json.dumps`, so temporary Windows paths are
  correctly escaped. The previously failing focused test now passes.
- [x] 10. **Codex** — Validated both carried computer-use fixes and the corrected
  Windows fixture through `scripts/run_tests.sh`: all 103 tests in
  `tests/tools/test_computer_use.py` passed.
- [x] 11. **Codex** — Ran the normal Desktop renderer, Electron, and E2E
  typechecks without the sandbox workaround. All three passed; the prior
  `.tsbuildinfo` write failure did not recur.
- [x] 12. **Codex** — Resolved all Desktop ESLint warnings without disabling any
  rules: fixed the seven React hook dependency warnings structurally and made
  all intentional jsdom document access explicit. `eslint` now passes with
  `--max-warnings=0`; normal Desktop typechecks still pass.
- [x] 13. **Codex** — Verified the current Desktop path end to end. The Start
  Menu shortcut resolves through `.hermes/launch-desktop.ps1` to the canonical
  executable and repository-scoped `HERMES_HOME`; the gateway is running on
  managed runtime v0.20.6 with both signed carried computer-use commits.
- [x] 14. **Codex** — Removed the full-suite gateway-settings timing flake by
  moving its expensive component import outside the individual test timeout.
  The test body now completes in milliseconds, and the full renderer/UI suite
  passes all 6,087 tests across 617 files.
- [x] 15. **Codex** — Isolated automatic and fixture repository commits from the
  user's Git signing configuration with a narrow `commit.gpgSign=false`
  override. Added a regression test using a deliberately broken signing-required
  repository configuration; normal user commits remain untouched.
- [x] 16. **Codex** — Corrected injected POSIX path semantics and properly gated
  only genuinely POSIX/Darwin permission, shell, SSH Include/ControlMaster, venv,
  and staging assertions on Windows. Cross-platform behavior remains covered.
- [x] 17. **Both** — Ran the real Windows backend-release/process tests with live
  process-table inspection and real process-tree termination. All 3 tests passed
  without requiring additional action from Connor.
- [x] 18. **Codex** — Fixed the remaining actionable Windows Electron-suite
  cleanup race by yielding for child-process handle release before retrying
  temporary-directory removal. The full Electron project now passes 1,907 tests
  with 34 intentional platform skips and zero failures.
- [x] 19. **Codex** — Investigated the Desktop development-dependency
  advisories. Production dependencies audit clean. Electron remains pinned at
  40.10.2 because the already-tested 40.10.6 upgrade breaks fresh Windows
  installation without the Visual C++ runtime. The session-confusion advisory
  is not reachable through Hermes' `protocol.handle()` response path. The
  popup advisory did expose an application path, so all Electron-created
  windows now deny native popup creation, approved external links use the
  validated bridge, and focused security tests pass. The remaining
  `extract-zip` report is confined to Electron's checksum-verified install-time
  development chain.
- [x] 20. **Codex** — Completed the Desktop validation matrix with the matching
  Playwright 1.62.1 binaries. Typechecks, lint, all 6,087 renderer tests, all
  1,909 Electron tests (34 intentional skips), all 625 plugin checks, package
  creation, and production audit pass. Fixed Windows-only test prerequisites:
  nested Electron discovery, complete Python-runtime selection, and POSIX-shell
  quoting checks. The Playwright run executed all 72 cases and exposed a
  separate regression set: 42 passed, 22 failed, 4 skipped, and 4 were not run
  after parent failures. Prerequisites: items 10-19.
- [x] 20a. **Codex** — Resolved the Playwright regression set found by item 20,
  including inactive-tab projection, correction persistence, Windows gateway
  discovery, unread-state behavior, and concurrency-sensitive waits. On
  2026-08-27 the full Electron E2E suite ran with hidden windows at safe
  concurrency: 68 passed, 4 intentionally skipped, and 0 failed. The focused
  Desktop unit suite (33 tests), typecheck, zero-warning lint, and production
  build also passed; the post-run audit found no temporary `electron.exe`.
  Prerequisite: item 20.
- [x] 20b. **Codex** — Applied all current Desktop production changes to the
  authoritative green app on 2026-08-28 after item 20a passed. Typecheck,
  zero-warning lint, the corrected bot-chat contracts, the full hidden Electron
  E2E suite, and the production build passed. The live root process and pinned
  taskbar shortcut both resolve to
  `apps/desktop/release/win-unpacked/Hermes.exe`; child processes confirm the
  normal `C:\Users\conno\AppData\Roaming\Hermes` profile. Packaged stamp:
  commit `bd0705862a4a60c8efb25e381658d6503533e69f`, built
  `2026-08-28T03:58:35.476Z`, dirty local source. SHA-256:
  `Hermes.exe` = `9befd7dd1d4d378aeacc42e49c463a4a55f306b22d26d88bfb2f5559dd1b03ea`;
  `app.asar` = `5eba65ec5a33a3114e000e28776c3cb508ef99ae32bfc4df60a6a51f07046fcf`.
  The immediately previous package is preserved at
  `apps/desktop/release/win-unpacked-backup-20260828-final` for rollback. A
  post-deployment renderer-bridge check against the canonical green app showed
  the configured LM Studio provider. The final safe local-model verification is
  recorded in items 24d-24e; the app is returned to its normal cloud default
  after local tests, and the audit found no test `electron.exe`.
  A same-day managed-backend hardening added deterministic LM Studio parallel
  control and mismatched-instance replacement; eight focused tests passed and
  the canonical Desktop cold-run proof is recorded in 24e. Final handoff audit:
  root process and `Hermes.lnk` both target the canonical executable, four
  renderer/utility children use the normal profile, the root has no debug
  arguments, port 9223 is closed, no `electron.exe` remains, the backend is
  ready, and the local model is unloaded to release GPU memory.
  This does not replace the later clean canonical-build requirements in items
  26-31.
- [x] 20c. **Codex** — Fixed the authoritative green Desktop app's stale
  “Hermes couldn't start / Timed out connecting to Hermes backend” screen on
  2026-08-28. The normal-profile logs proved the install was healthy: Windows
  orphan-backend cleanup kept the main process's shared startup attempt alive
  beyond the renderer's 45-second deadline, and the backend became ready after
  the renderer had already published a terminal error. Renderer startup
  timeouts now enter the existing bounded retry path, join the still-live main
  startup attempt, and automatically dismiss the failure surface when the
  backend becomes ready; genuine local failures and reauthentication failures
  still fail immediately. The focused real-hook suite passed all 42 tests,
  targeted ESLint and Prettier checks passed, and the production build passed.
  The repository-wide typecheck remains independently blocked by the existing
  `src/app/open-session.test.ts:13` TS2556 error in unrelated dirty work.
  The canonical package was backed up to
  `apps/desktop/release/win-unpacked-backup-20260828-backend-recovery`, replaced
  from an isolated production package, and verified with matching `app.asar`
  SHA-256 `4afb7ad43f4b3314981e963e1f0d6d7e6e6ca4476be6278afbfe04731640f5fb`
  (`Hermes.exe` SHA-256
  `c59f80147534be516299a758aaaee3c36165bf7cafbb7fce7d309dfcb2d5d1c1`).
  A real canonical cold start reproduced the slow path (66 seconds), then the
  rendered screen automatically changed from CONNECTING to loaded sessions and
  `Gateway ready`, with neither failure text present. The final normal launch
  uses `C:\Users\conno\AppData\Roaming\Hermes`, has no debug argument, port
  9223 is closed, no test `electron.exe` remains, the pinned shortcut still
  targets the canonical executable, and the backend reached ready at
  `2026-08-28T18:12:29.274Z`.
- [x] 21. **Both** — Repaired and independently verified the PayPal MCP
  connection. Connor completed a fresh resource-bound OAuth authorization in
  the repository-scoped Desktop profile. `hermes mcp test paypal` then connected
  through OAuth 2.1 PKCE and discovered all four expected tools:
  `create_invoice`, `list_transactions`, `list_invoices`, and `list_disputes`.
- [x] 21a. **Both** — Repair the Hugging Face MCP connection shown by the live
  green Desktop app as “MCP server needs re-authentication.” Codex diagnoses the
  configured server, token/cache state, permissions, and Desktop visibility;
  Connor completes any Hugging Face sign-in or consent in the provider's secure
  browser flow. Verify the warning clears and the expected Hugging Face tools
  work from the authoritative Desktop app, not only from an internal CLI test.
  Diagnostic checkpoint (2026-08-28 14:55 EDT): the repository-scoped backend
  config correctly has `hugging_face` enabled at `https://huggingface.co/mcp`
  with OAuth, but `.hermes/mcp-tokens/` contains no `hugging_face` token,
  client-registration, or authorization-server metadata files. Sanitized live
  logs consistently identify the blocker as first-time OAuth in a
  non-interactive backend with no cached token; the separate `hf` CLI is also
  logged out and is not being mistaken for Desktop authorization. Hugging
  Face's live protected-resource metadata advertises header bearer auth and
  scopes `openid`, `profile`, `read-mcp`, `read-repos`, `jobs`,
  `contribute-repos`, and `inference-api`; its live authorization-server
  metadata advertises authorization-code + refresh-token support, PKCE S256,
  dynamic client registration, and client-ID metadata documents. The official
  MCP documentation identifies `hf_fs` as the built-in Hub navigation/search
  tool; additional tools depend on the account's Hugging Face MCP settings.
  The live Desktop root and all Electron children resolve to the canonical
  `release/win-unpacked/Hermes.exe`, renderer children use the normal
  `C:\Users\conno\AppData\Roaming\Hermes` profile, both pinned and Start Menu
  shortcuts target the canonical executable, the managed `hermes serve`
  descendant resolves to the repository `.hermes` home, no process or shortcut
  has a debug flag, and the stale DevTools marker's recorded port is not
  listening. Remaining user-owned step: in the canonical Desktop MCP page,
  select `hugging_face`, click **Authenticate**, and complete only the official
  `huggingface.co` sign-in/consent page. Afterward Codex must verify the warning
  clears, discover the resulting tool list, run one safe read-only `hf_fs`
  request from a fresh canonical Desktop chat, and record final evidence here.
  Connor selected full MCP OAuth access on 2026-08-28: `openid`, `profile`,
  `read-mcp`, `read-repos`, `jobs`, `contribute-repos`, and `inference-api`.
  Codex persisted that non-secret scope explicitly under the `hugging_face`
  server. The grant does not authorize Codex to run a Job, create or modify a
  repository, make an inference request, or incur charges; those actions still
  require separate explicit approval. Secure browser consent remains pending.
  Repair/deployment checkpoint (2026-08-28 15:38 EDT): the failed Desktop
  attempt was traced to Hugging Face allowing anonymous MCP initialization and
  tool discovery. The prior worker only probed the server, so the MCP SDK never
  received an authorization challenge and never opened its OAuth flow. Hermes
  now proactively enters the SDK OAuth flow for an explicit Authenticate/login
  request, while retaining SDK protected-resource/authorization-server
  discovery, dynamic client registration, PKCE S256, callback-state checking,
  TLS verification, token persistence, and the exact configured scope. A
  regression test proves the local synthetic challenge is never transmitted to
  `huggingface.co`; scope characters are validated before header construction.
  The Desktop, CLI, and gateway sibling paths all use the repaired behavior.
  Focused OAuth suites passed with 144 tests passed and 1 skipped; focused Ruff
  and whitespace checks passed. A token-free live handshake reached the
  official `huggingface.co/oauth/authorize` endpoint with PKCE S256, state, and
  the exact seven selected scopes, then stopped before consent/token exchange.
  The production Desktop build succeeded with install stamp commit
  `bd0705862a4a60c8efb25e381658d6503533e69f`, built
  `2026-08-28T19:29:49.909Z`. The canonical package was replaced and relaunched;
  the live root/children and both shortcuts resolve to
  `release/win-unpacked/Hermes.exe`, renderer children use the normal profile,
  the backend resolves to the updated repository-managed runtime, port 9223 is
  closed, and no Desktop process has a debug flag. Rollback copies are preserved
  at `apps/desktop/release/win-unpacked-backup-20260828-hf-oauth-pre`,
  `apps/desktop/release/win-unpacked-deploy-old-20260828-hf-oauth`, and
  `.backups/hf-oauth-managed-runtime-20260828`.
  Completion/persistence checkpoint (2026-08-28 15:57 EDT): Connor completed
  the official Hugging Face consent. The canonical Desktop app now shows
  Hugging Face connected with its authenticated tools/resources available;
  Figma, PayPal, and Vercel are also connected. Sanitized inspection confirmed
  that all four OAuth servers have durable access tokens, refresh tokens,
  absolute expiry metadata, dynamic-client registrations, and authorization
  server metadata under the repository-scoped Hermes home. Two full canonical
  app/backend restarts reloaded those grants and registered all four toolsets
  without opening a browser or starting a new authorization flow. Hermes' one
  shared OAuth manager provides the same durable-token, pre-expiry refresh, and
  one-time 401 refresh/retry behavior to every currently configured and future
  MCP server using `auth: oauth`.
  Windows credential storage was also hardened: the `mcp-tokens` directory,
  newly written credentials, and existing known OAuth files are migrated to a
  protected DACL permitting only Connor's Windows account and `SYSTEM`; token
  values are never logged. The neighboring OAuth test suite passed with 153
  tests passed and 1 skipped, focused Ruff and whitespace checks passed, and
  the production Desktop package was rebuilt and deployed with install stamp
  commit `bd0705862a4a60c8efb25e381658d6503533e69f`, built
  `2026-08-28T19:53:46.656Z`. Final audit found only the canonical Hermes
  package, no test Electron process, no debug flags, the normal Desktop
  profile, both shortcuts targeting the canonical executable, the updated
  repository-managed backend, and port 9223 closed. Rollback copies for this
  deployment are preserved at
  `apps/desktop/release/win-unpacked-backup-20260828-oauth-persistence`,
  `apps/desktop/release/win-unpacked-deploy-old-20260828-oauth-persistence`,
  and `.backups/mcp-oauth-persistence-20260828`. Routine app closes, backend
  restarts, Windows restarts, and access-token expiry therefore do not require
  another sign-in. A provider can still force a new sign-in by revoking or
  invalidating its refresh grant, changing authorization policy, or if Connor
  disconnects/removes the integration; Hermes cannot override those
  provider-side security controls.
- [x] 22. **Connor** — Selected option 4C: maximize integration coverage for
  providers, messaging platforms, OAuth services, browser backends, MCPs, and
  plugins that Connor actually owns or uses. Each service will receive only the
  permissions needed for the selected Hermes use case; unused services will not
  be created merely to increase the count. Connor selected a one-service-at-a-
  time setup workflow on 2026-08-27.
- [x] 23. **Connor** — Selected option 5A: do not purchase or add paid Nous Tool
  Gateway credits. Preserve the existing Nous inference login, but use free
  local routes or Connor's existing direct service accounts for optional tools.
  This choice creates no charge and does not block core Hermes health.
- [x] 24. **Both** — Complete the option-4C maximum-coverage integration rollout
  without depending on paid Nous Tool Gateway credits. Codex handles discovery,
  configuration, code, and validation; Connor handles account selection,
  third-party authentication, secrets, consent, and any service-specific terms.
  Execute one service completely before starting the next, beginning with the
  local AI model for Hermes Desktop. Prerequisites: items 21-23.
  - [x] 24a. **Codex** — Audit the ASUS ProArt PX13 for local inference. Verified
    Ryzen AI 9 HX 370 (12 cores/24 threads), 32 GB RAM, RTX 4050 Laptop GPU with
    6 GB VRAM, Radeon 890M, and about 698 GB free disk. LM Studio is already
    installed and contains Qwen3-30B-A3B Q4_K_M. Its catalog metadata reports a
    32,768-token maximum, while LM Studio's forced-64K estimate is 24.97 GiB;
    it is not yet configured or validated for Hermes and remains a fallback.
  - [x] 24b. **Codex** — Updated LM Studio from 0.4.6+1 through 0.4.21+2 to the
    current stable 0.4.22+1 on 2026-08-28, then re-verified its indexed models,
    localhost server, and preserved settings. Controlled runtime comparisons
    found the current CUDA 12 llama.cpp 2.31.2 runtime severely underutilized
    this RTX 4050, while the current Vulkan AVX2 2.31.2 runtime completed the
    same Qwen3.5 4B response in seconds; Vulkan is therefore the selected local
    runtime. The verified 0.4.6+1 installer and rollback notes are saved under
    `.backups/lm-studio-20260827/`; older CUDA/Vulkan runtimes remain installed
    as an additional runtime-level rollback path.
  - [x] 24c. **Both** — Downloaded Connor's selected option A on 2026-08-28:
    `unsloth/Qwen3.6-35B-A3B-GGUF`, exact file
    `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` (22,134,528,992 bytes). The final SHA-256
    exactly matches Hugging Face's published value,
    `ac0e2c1189e055faa36eff361580e79c5bd6f8e76bffb4ce547f167d53e31a61`,
    and LM Studio indexes it as tool-capable with a 262,144-token maximum. The
    isolated current downloader made the transfer reliable without changing
    Hermes' shared Python packages; verified obsolete partial fragments were
    removed afterward, reclaiming about 964 MB. Connor then chose fallback A;
    Codex downloaded `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf` (17,730,509,792 bytes)
    and independently matched its SHA-256 to Hugging Face's published value,
    `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3`.
    The current Hugging Face verifier also checked both installed files, and
    two redundant retry fragments totaling 340,273,025 bytes were removed.
  - [x] 24d. **Codex** — Completed guarded candidates and selected the highest
    viable profile for this 32 GB / RTX 4050 6 GB laptop. All Qwen3.6 35B
    candidates, including verified IQ3_S, left unsafe RAM headroom; verified
    Qwen3.5 9B Q4_K_XL/Q6_K_XL candidates were too slow with partial offload.
    The final model is `qwen3.5-4b`, exact Qwen3.5 4B Q6_K file
    (3,525,956,768 bytes; SHA-256
    `fdedd781c9ce676ab66b018ca247ff78e8a33c98098a822c1e2d5075e7718f66`).
    LM Studio 0.4.22+1 now serves it only on `127.0.0.1:1234` with Vulkan AVX2
    runtime 2.31.2, 65,536 real context, and parallel 1. Hermes uses explicit
    loading and enforces `model.lmstudio_parallel: 1`; if LM Studio races ahead
    with its four-slot JIT default, Hermes detects and replaces that instance
    before the turn. Eight focused tests, source/managed-backend syntax checks,
    and Ruff checks pass. A warm reasoning-off exact response completed in 0.61
    seconds at about 30 tokens/second. With Connor's normal apps open, the loaded
    profile used about 5.69/6.14 GB VRAM and left about 1.2 GB available system
    RAM, so it remains opt-in and the free cloud route remains the normal
    default. The final handoff unloads the model to release resources; automatic
    idle unloading for explicit loads is tracked in 24f because LM Studio's REST
    management endpoint does not accept its CLI-only TTL setting.
  - [x] 24e. **Codex** — Completed the authoritative green-Desktop integration.
    The repository-scoped Desktop backend has the LM Studio localhost endpoint,
    Hermes JIT policy, and Qwen3.5 4B picker entry. Hermes' internal compressor
    is explicitly routed to the already-authenticated free Nous
    `upstage/solar-pro4:free` model (cached context 524,288) instead of consuming
    the local model's chat window. In the canonical packaged renderer, the model
    pill showed `Qwen3.5 4b · Off`; a real Desktop request produced a visible
    `Read README.md` tool card and the exact response
    `HERMES_DESKTOP_LOCAL_OK`. A separate cold, fully unloaded, new-session run
    through the patched canonical app loaded 65,536 context at parallel 1 and
    returned `HERMES_LOCAL_RUNTIME_OK` in 72.09 seconds. No CLI-only result is
    counted as completion. The normal cloud model remains the default for new
    chats.
  - [x] 24f. **Codex** — Benchmarked Qwen3.5 4B Q6_K through the authoritative
    Hermes Desktop at explicit 65,536-token context and parallel 1. Desktop tool
    calling worked, a 60,049-token beginning/middle/end retrieval passed, and
    observed load was approximately 63-68 C, 91-100% GPU, 5.0 GB VRAM, and up to
    54 W. The exact-answer quality probe failed its arithmetic despite valid
    JSON, and the Desktop tool-call response took about 132 seconds. Therefore
    Qwen remains an opt-in fallback and free Nous Solar Pro4 remains the normal
    default; no subjective fan/noise approval is required unless that default is
    reconsidered. Added a 300-second LM Studio idle-unload helper: its focused
    20-test suite and Ruff checks pass, and unloading recovered about 3.7 GiB
    VRAM plus 3.1 GiB system RAM. Deployed to the canonical package with rollback
    at `apps/desktop/release/win-unpacked-backup-20260828-lmstudio-idle`; the
    canonical app, normal profile, taskbar shortcut, and Start Menu shortcut were
    verified after restart.
  - [x] 24g. **Both** — Applied Connor's existing option-4C maximum-
    coverage decision to the accounts already present in Hermes' protected
    credential stores. Selected current accounts/routes are Nous Portal,
    Anthropic, OpenAI API, xAI API, Gemini, DeepSeek, Hugging Face, OpenRouter,
    Vercel AI Gateway, LM Studio, and the already-configured MCP/service accounts.
    No passwords, keys, OAuth codes, refresh tokens, or recovery codes were
    copied into chat or the tracked report. Subscription-specific duplicate
    OAuth routes remain unselected until Connor explicitly wants that distinct
    billing/entitlement path and completes its protected sign-in.
  - [x] 24h. **Codex** — Configured and read-only validated every selected,
    nonduplicate inference route already backed by an account: Nous (350 catalog
    entries), Anthropic (10), OpenAI API (130), Gemini (54 through Google's
    official OpenAI-compatible endpoint), DeepSeek (3), Hugging Face (136),
    OpenRouter (398), Vercel AI Gateway (360), and LM Studio. The authoritative
    Desktop model picker exposes Anthropic, DeepSeek, GitHub Copilot, Google AI
    Studio, Hugging Face, LM Studio, Nous Portal, OpenAI API, OpenRouter, Vercel
    AI Gateway, and xAI while preserving Nous Solar Pro4:Free as the default.
    xAI is configured and visible but its live catalog is account-limited with
    HTTP 403 because the team has exhausted credits or reached its spending
    limit; no purchase or limit increase was made. Copilot's existing classic
    GitHub PAT is not a Copilot credential, and OpenAI Codex/xAI OAuth are
    optional duplicate subscription routes requiring protected user sign-in.
  - [x] 24i. **Codex** — Configured the selected direct replacements: local
    Browser Use is enabled (no paid cloud browser), SearXNG returned live search
    results, OpenAI image generation is explicitly selected and structurally
    available, xAI video is selected but limited by the same account credit cap,
    OpenAI TTS is available with voice `fable`, ElevenLabs credentials returned
    21 voices, local faster-whisper STT is enabled with the `base` model, and the
    n8n MCP/API passed read-only checks with 11 tools discovered. No billable
    image/video generation or paid-browser activation was performed. The direct
    capability matrix is saved in `HERMES_INTEGRATION_INVENTORY.md`.
  - [x] 24j. **Both** — Set up messaging applications one service at a time,
    beginning with Telegram, WhatsApp, and iMessage through a supported bridge
    such as BlueBubbles, then any additional platforms Connor actually uses.
    Codex prepares and tests each adapter plus its Desktop visibility and
    allowlists/pairing rules; Connor owns account login, bot/app creation,
    Apple-device/bridge availability, tokens, recipient choices, and consent.
    Telegram is complete: Connor entered its token and one numeric owner ID in
    Desktop, Codex restarted the installed gateway, the Bot API authenticated,
    polling mode reported healthy, the gateway state is `connected` with no
    error, the 60-command Telegram menu registered, and the authoritative
    Desktop shows the green connected state. Connor then sent `/status` from
    Telegram on his iPhone and received Hermes' live gateway-status response,
    showing the correct Solar Pro4:Free model and `Connected Platforms:
    telegram`; Telegram setup is therefore finished end to end. Codex installed
    the bundled WhatsApp bridge dependencies in both the source and managed
    Desktop backend and all 22 bridge tests pass. Connor selected personal
    self-chat after reviewing the unofficial bridge risk and completed the QR
    scan. The resulting linked-device session is stored in the ignored Hermes
    platform session directory; Codex derived and saved a single-account
    allowlist without exposing the number, set self-chat mode with pairing DM
    policy, restarted the gateway, and verified the live bridge HTTP health,
    gateway state, and canonical Desktop green status as `connected` with no
    error. Telegram also returned to `connected` after the shared restart. The
    one-time QR image was removed after pairing. Connor then sent `/status` to
    his WhatsApp self-chat and received Hermes' live gateway-status response at
    20:23, explicitly listing `telegram, whatsapp`; WhatsApp is therefore also
    finished end to end. Codex hardened the Windows login fallback into a hidden
    watchdog because this standard-user account denied Scheduled Task creation:
    it preserves intentional clean stops but retries unexpected gateway exits
    after 60 seconds. A controlled exact-PID crash replaced gateway PID 22496
    with PID 38952 and automatically restored Telegram polling plus WhatsApp
    bridge HTTP 200/connected state. Closing the canonical Desktop normally left
    PID 38952 and both adapters connected; relaunching the pinned canonical
    executable against the normal profile returned to `Gateway ready`, Telegram
    `Connected`, and WhatsApp green without a new login or QR scan. The focused
    Windows gateway suite passes 10/10 tests. A final clean supervised restart
    left PID 39412 running with all six deep lifecycle probes passing, both
    platform states `connected`, and WhatsApp bridge HTTP 200.
    BlueBubbles is no longer selected because Connor confirmed on 2026-08-28
    that he no longer has the Mac required to host its iMessage server; the
    Windows Hermes adapter remains available if a Mac server is added later.
  - [x] 24k. **Both** — Add only selected MCP servers and standalone plugins for
    services Connor owns. Codex checks permissions, provenance, overlap, and
    Desktop visibility; Connor authorizes third-party OAuth/install prompts.
    Completed 2026-08-28: official Context7, Microsoft Learn, Twilio Docs,
    GitHub, and Railway MCP entries are enabled in the normal backend profile
    and visible in the canonical green Desktop app. All five passed transport
    and tool discovery plus one bounded read-only live call. GitHub resolved to
    `hicklax13`; its on-disk Authorization header is an environment reference,
    not a plaintext credential. GitHub and Railway are set to `trust:
    untrusted`, so tools without an exact read-only annotation require approval.
    Railway exposes 42 tools, of which 41 are enabled because the opaque
    `railway-agent` tool remains deliberately excluded. The trust-gating suite
    passes 11/11 tests. No standalone plugin was added: audited package searches
    produced no useful, provenance-safe addition that did not duplicate
    existing Hermes browser, search, code-analysis, or provider routes.
    Railway repair checkpoint (2026-08-28): the initial consent page
    failed before login because Railway's discovered authorization endpoint
    already contains a `resource` query and MCP Python SDK 2.0 appended its
    OAuth parameters with a second `?`. Railway consequently could not see the
    required top-level `response_type=code`. Hermes now preserves the discovered
    endpoint query and joins the SDK-generated PKCE parameters with `&`, while
    delegating state validation, callback handling, and token exchange to the
    SDK. Hermes also reuses the dynamically registered client's exact loopback
    redirect URI, including its host and Desktop callback path, rather than only
    its port. Regression coverage for both OAuth bug classes and neighboring
    suites passed with 69 tests passed and 1 skipped; whitespace and compile
    validation passed. Repository and managed-backend copies are byte-identical.
    Connor completed official Railway consent; a live `whoami` call passed, the
    OAuth grant remained cached across a full canonical Desktop replacement and
    cold restart, and the post-restart `whoami` call passed again. The final
    canonical package has build timestamp `2026-08-29T01:32:19.059Z`; the prior
    package and managed source are recoverable at
    `apps/desktop/release/win-unpacked-backup-20260828-railway-redirect` and
    `.backups/railway-oauth-managed-runtime-20260828`. The pinned taskbar and
    Start Menu shortcuts resolve to the canonical executable, the normal
    Roaming profile is active, no test `electron.exe` remains, and the Desktop
    visually reports `Gateway ready` plus Railway green with 41 enabled tools
    and no Authenticate prompt. The independent Telegram/WhatsApp gateway kept
    the same process tree during deployment and both platform states remained
    `connected` with no error.
  - [x] 24l. **Codex** — Audit the completed 4C configuration for duplicate or
    obsolete adapters, excessive permissions, plaintext-secret leakage, and
    Desktop/CLI profile mismatch before live diagnostics. Completed 2026-08-28:
    the normal Desktop profile and managed backend home were confirmed; all 13
    configured MCP servers are enabled with no duplicate endpoint group; only
    Telegram and WhatsApp are enabled gateway adapters; and the only
    secret-shaped MCP config field is an environment reference rather than a
    plaintext value. GitHub and Railway remain correctly marked `untrusted`.
    GitHub's classic PAT still has excessive scopes, and Connor explicitly
    declined rotation after its accidental display; this is recorded as
    accepted risk without re-prompting. Fixed the display defect in
    `hermes_cli/web_server.py` so `/api/config` restores raw environment
    templates after runtime expansion. The regression and related config suites
    passed 12/12, the managed-runtime verification passed all five secret-safe
    assertions, and the patched source was deployed behind the canonical green
    Desktop package with a recoverable package/source backup. The canonical
    process tree and both Windows shortcuts resolve to the intended executable;
    Telegram and WhatsApp remained connected with no recorded error. A formal
    Codex Security prompt-only scan could not snapshot this heavily dirty
    working tree, so no formal scan result is claimed; the targeted manual and
    live configuration audit is the recorded evidence.
  - [x] 24m. **Both** — Build and complete a credential, account, service, and
    device integration-readiness matrix for every system Connor wants available
    through the authoritative green Hermes Desktop app. For each entry, verify
    that the required API key, OAuth grant, auth token, secret, account login,
    environment variable, device pairing, server URL, and permission scope
    exists and is current; configure the supported Hermes adapter/provider/MCP;
    test the maximum controls Connor explicitly authorizes; and record working,
    limited, unsupported, or blocked status plus the next action.
    - [x] 24m.1. **Both** — AI, model, communications, and media API providers:
      Anthropic, OpenAI, xAI, ElevenLabs, Twilio, Google Gemini, DeepSeek, and
      OpenRouter. Completed 2026-08-28 with secret-safe official API probes:
      Anthropic (HTTP 200, 10 models), OpenAI (HTTP 200, 130 models),
      ElevenLabs (HTTP 200, 21 voices), Gemini (HTTP 200, 54 models), DeepSeek
      (HTTP 200, 3 models), and OpenRouter (HTTP 200, 396 models) are working.
      xAI's credential is present but the account returns HTTP 403 for exhausted
      credits or its spending limit, so it is correctly classified as limited.
      Twilio Docs MCP remains working, but no Twilio account SID, auth token, or
      sending number is stored in Hermes; account API/SMS control is classified
      as blocked pending Connor's Twilio credentials and number selection. No
      billable generation, message send, or external mutation was performed.
    - [x] 24m.2. **Both** — Development, deployment, identity, and application
      services: GitHub organization/Teams account `connorbhickey`, personal
      GitHub account `hicklax13`, Vercel, Clerk, Railway, Yahoo Fantasy Sports
      API, and HEATER (Connor's fantasy-baseball web application). Read-only
      account and control-surface audit completed 2026-08-28: GitHub personal
      and organization identity passed; Vercel and Railway persisted OAuth reads
      passed; the protected HEATER Clerk key passed an official owner-user read;
      and the HEATER frontend returned HTTP 200. Railway reports Postgres and
      Redis online with zero recent failures. The latest App B and worker
      deployments reached `SUCCESS`; final production reads returned HTTP 200
      for the frontend and backend health routes, and both the backend and
      frontend-proxied freshness reports were valid, Yahoo-attributed, and had
      zero failing sources across all three monitored inputs. Legacy App A
      remains intentionally offline. GitHub's broad classic-PAT scopes are
      accepted risk per Connor's explicit decision.
    - [x] 24m.3. **Both** — Google accounts and services for both
      `conlaxer13@gmail.com` and `cbh76@georgetown.edu`, including the services
      each account is permitted to use, YouTube, YouTube Music, and YouTube TV.
      Treat school-managed policy restrictions as authoritative and do not try
      to bypass them. Updated 2026-08-29: the isolated `google-personal` profile
      now has a full, auto-refreshing Workspace grant for Gmail, Calendar,
      Drive, Docs, Sheets, and Contacts. Safe live reads passed for Gmail,
      Calendar, Drive, and Contacts, and Google identified the grant as
      `conlaxer13@gmail.com`. The canonical green Hermes Desktop returned
      `GOOGLE_PERSONAL_DESKTOP_OK`, was closed and relaunched from the canonical
      executable with the normal profile, preserved the profile/session, and
      returned `GOOGLE_PERSONAL_RESTART_OK` through a fresh Gmail API read. The
      client and token files are ACL-protected to Connor and SYSTEM; the exact
      redundant client download was removed from the repository root and Google
      OAuth artifacts are now ignored by git. The isolated `google-school`
      profile now has its own full Workspace grant for `cbh76@georgetown.edu`;
      Georgetown accepted all eight requested scopes. Its token is separately
      ACL-protected, safe live reads passed for Gmail, Calendar, Drive, and
      Contacts, and identity/scope assertions passed without displaying private
      content. Canonical Desktop verification returned
      `GOOGLE_SCHOOL_DESKTOP_OK`, and after a full canonical app close/relaunch
      the school profile/session persisted and a fresh Gmail read returned
      `GOOGLE_SCHOOL_RESTART_OK`. Both Workspace accounts are therefore complete
      and independently persistent. The profile-visible `youtube-account` skill
      now provides a separate, read-only YouTube Data API route without adding a
      core model tool. The personal profile has its own ACL-protected
      `youtube_token.json` containing only `youtube.readonly`; safe channel,
      subscription, and playlist probes passed, canonical Desktop returned
      `YOUTUBE_PERSONAL_DESKTOP_OK`, and a full canonical close/relaunch plus a
      fresh channel check returned `YOUTUBE_PERSONAL_RESTART_OK`. Georgetown
      also granted a separate ACL-protected token containing exactly
      `youtube.readonly`; it is cryptographically distinct from the personal
      token. Safe channel and subscription probes passed. The school identity
      has never created a YouTube channel, so Google's playlist endpoint returns
      `404/channelNotFound`; the skill now treats that documented account state
      as an empty playlist result while preserving other API errors. Canonical
      Desktop returned `YOUTUBE_SCHOOL_DESKTOP_OK`, preserved the profile and
      session through a full close/relaunch, and returned
      `YOUTUBE_SCHOOL_RESTART_OK` from a fresh channel check. No supported
      present connector was found for direct YouTube Music or YouTube TV account
      control; later Home Assistant / Google Cast work may cover supported
      device playback instead. Item 24m.3 is complete.
    - [x] 24m.4. **Both** — Entertainment and personal ecosystems: Sonos (four
      speakers and one TV sound system), iCloud account `hicklax13@icloud.com`,
      Xbox Series X, LG Smart Monitor, Samsung Smart TV, and TCL Smart TV. Audit
      completed 2026-08-28: Sonos S1 Controller and Windows Xbox packages are
      installed, iCloud for Windows is absent, and Windows reports two generic
      displays. Completed 2026-08-29 through Home Assistant: the Samsung Q70,
      TCL Roku TV, and LG webOS display are paired and expose their supported
      media, power, volume, playback, and remote controls. Eight Sonos endpoints
      are configured as five logical Home Assistant rooms, with all five media
      players available. iCloud remains limited on this Windows-only laptop to
      supported app-password mail access if Connor chooses to configure it;
      Apple Notes, Reminders, and Find My are macOS-only in Hermes. Xbox control
      is formally classified as unsupported by the present Hermes/Home Assistant
      routes. No unsupported control or cloud OAuth capability is claimed.
    - [x] 24m.5. **Both** — Smart-home and network systems: two Google
      Hub/Nest displays, three Google Nest cameras, two Google smart
      thermostats, two Google TV Streamer devices, Google Home, and the Eero
      mesh Wi-Fi system. Inventory recorded and local discovery audited
      2026-08-28. Completed 2026-08-29 within the available free integration
      surface: Home Assistant discovered four Google Cast targets and paired two
      Android TV Remote devices. Eero exposes no official Home Assistant control
      integration or UPnP/IGD endpoint on this network, so seven free ICMP
      reachability monitors cover the gateway and six mesh nodes; all seven were
      connected at final verification. The official Nest integration requires
      Google's one-time US $5 Device Access registration. Connor explicitly
      excluded every paid route, so setup stopped before purchase, no Device
      Access project or credential was created, and the briefly enabled Smart
      Device Management API was disabled again. Nest cameras and thermostats are
      therefore intentionally excluded rather than represented as working.
    - [x] 24m.6. **Both** — Microsoft Office/apps/services, Connor's Tailscale
      network, and Connor's Home Assistant account and server. Prefer Home
      Assistant as the unified local control plane for supported household
      devices when it provides safer or broader control than separate cloud
      credentials. Audit completed 2026-08-28: Word, Excel, PowerPoint, Outlook
      Classic, OneDrive, and Xbox are installed; no Microsoft Graph authorization
      is configured. Codex installed the official Tailscale 1.102.3 client; its
      Windows service is running and the laptop rejoined Connor's existing
      tailnet. Connor completed the interactive browser sign-in on 2026-08-28;
      the laptop then reported online in the intended tailnet and the service
      configuration reported `AUTO_START`, providing automatic reconnection
      after Windows restart. Completed 2026-08-29: Codex installed the official
      stable Home Assistant Container 2026.8.3 at
      `C:\Dev\home-assistant\compose.yaml`, with persistent configuration,
      `restart: unless-stopped`, a 60-second clean-shutdown window, and local
      ports 8123 and 1400. Connor completed owner onboarding and created the protected
      `Hermes Desktop` long-lived token. `HASS_URL` and `HASS_TOKEN` were stored
      through Hermes's secure credential writer and synchronized to all eight
      current profiles; the final capability dry run reported zero drift and a
      recoverable pre-write backup exists at
      `.hermes/backups/profile-capability-sync/20260830T022837Z`. The authenticated
      API returned `API running.`; the final system had 22 enabled config
      entries, 95 entity states, 64 service domains, and zero unavailable
      entities. The packaged Desktop runtime listed 14 media players and 12
      binary sensors, read the Samsung state successfully, and the live canonical Desktop backend
      reported `homeassistant` enabled, available, and configured with all four
      `ha_*` tools. The free official Home Assistant progressive web app was
      installed from the local server's signed-in Chrome session, registered as
      Windows app `Chrome._crx_phgkokbgonpfjjchfdmggaoeie`, and pinned to the
      taskbar as `Home Assistant.lnk`. A live standalone-window check retained
      Connor's signed-in identity and showed all seven configured areas plus the
      live media and weather summaries; no token was copied into a third-party
      desktop client. Microsoft Graph was separately classified as organization/
      app-only in current Hermes (not a ready personal delegated connector),
      while Tailscale 1.102.3 remained online with MagicDNS and no health warnings.
      All relaunched `Hermes.exe` processes and the pinned shortcut resolved to
      the canonical executable, with no test `electron.exe` left running.
    - [x] 24m.7. **Codex** — Save a non-secret integration inventory and test
      report in this project folder, including account labels, credential type,
      secure storage location/reference, scopes, adapter/provider, Desktop
      visibility, supported controls, last verification time, and rollback or
      revocation instructions. Never store raw passwords, API keys, secret
      values, recovery codes, session cookies, or OAuth refresh/access tokens in
      the repository. Keep secrets only in the appropriate encrypted credential
      manager, provider OAuth store, or ignored local Hermes secret store.
      Completed 2026-08-28 in `HERMES_INTEGRATION_INVENTORY.md` for items
      24m.1-24m.6, including account labels, secret-safe storage references,
      permission posture, available controls, verification evidence, persistence,
      revocation, limitations, and explicit next actions. No raw credential or
      browser-session value was recorded.
    - [x] 24m.8. **Codex** — Perform an end-to-end green-Desktop verification for
      every configured entry: discover it in Hermes Desktop, make one safe
      read-only call, exercise each explicitly authorized control with a
      reversible test where practical, confirm synchronization, and document
      any capability that the official API, account tier, device, or platform
      does not expose. Do not claim “full control” where the provider does not
      offer it. Completed for every currently configured entry on 2026-08-28:
      the live canonical Desktop backend listed all 13 MCP servers and its
      built-in connection test passed for Context7, DeepWiki, Figma, GitHub,
      Hugging Face, Microsoft Learn, n8n, PayPal, Railway, Twilio Docs, and
      Vercel. Indeed was safely skipped and classified as blocked because it
      has no cached OAuth grant. Connor later completed Plaid's browser callback,
      but a secret-safe audit confirmed that the following token exchange
      returned HTTP 401 and no access/refresh token was persisted. Plaid's
      current official Dashboard MCP flow requires Production access plus a
      Plaid client ID and Production secret using `client_credentials`; neither
      credential is present, and the configured public browser/DCR flow cannot
      satisfy that requirement. Plaid therefore remains blocked without
      representing the callback page as a working connection.
      Updated 2026-08-29: all eight current profiles now share the canonical
      enabled baseline of 19 MCP servers, 103 installed skill paths, and 37
      static account/environment keys. New Desktop profiles clone `default`;
      refreshable OAuth stores remain profile-local. The new
      `scripts/sync_profile_capabilities.py --apply` path passed three focused
      tests, made recoverable backups, and its final dry-run read-back reported
      zero changes. Cloudflare's required OAuth `iss` callback parameter is now
      preserved end-to-end and a post-restart Desktop test returned 3,408 tools.
      PayPal (4), Railway (42), Stripe (11), Twelve Data (27), and Vercel (37)
      also passed live connection tests in `google-school`. Indeed now persists
      all four scopes plus a refresh token, but its MCP endpoint returns
      `403 invalid_client: Client not allowed`; the provider documents the beta
      route as Claude-Connector-only. Plaid is now classified as
      `client_credentials`, remains installed and enabled, and no longer offers
      an impossible browser-consent loop; it remains blocked pending Production
      approval, protected Production credentials, and a refresh-capable
      client-credentials implementation. The OAuth regression suite passed
      174 tests with one skip. The canonical package stamp is
      `2026-08-30T01:55:55.276Z`; all live Hermes processes and the pinned
      shortcut resolved to the canonical executable, no test `electron.exe`
      remained, and Telegram plus WhatsApp stayed connected on the separate
      default gateway.
      Telegram and WhatsApp remained connected with no recorded error,
      Tailscale remained authenticated, supported AI/provider catalog reads
      retained their recorded working/limited status, and all unconfigured or
      unsupported account/device routes remain explicitly classified rather
      than represented as working.
- [x] 26. **Codex** — Prepare a clean, reproducible Desktop build source without
  discarding user files: organize the completed changes into signed conventional
  local commits, preserve or move old untracked release outputs to a recoverable
  location, and verify a clean working tree. Prerequisite: item 20a. Completed
  2026-08-30: the implementation is organized into five signed conventional
  commits (`4111113677`, `ac41e844ad`, `ac43e18b1c`, `0d49dce3cf`, and
  `5102be29fe`) plus this signed readiness documentation commit. Old release
  trees, deployment backups, diagnostics, and unrelated user files were moved
  without deletion to
  `C:\Dev\hermes-agent-recovery\pre-clean-20260830`, preserving their original
  relative paths. Verification passed for 1,285 affected Python tests (five
  skipped), 7,998 Desktop Vitest tests (34 skipped), all 625 Desktop plugin
  tests, TypeScript typechecking, ESLint, Python compilation, `git diff
  --check`, and a secret-shape scan. The eight-profile capability dry run also
  confirmed zero config, environment, or skill drift. The final read-back
  confirmed all six commits had good SSH signatures and the tree was clean
  before item 27.
- [x] 27. **Codex** — Build the updated canonical Desktop package with a current,
  clean, verifiable build stamp. Prerequisite: item 26. Completed 2026-08-30:
  superseded 2026-08-31 by the post-rebase package built from published commit
  `35c44b1db1ee6ca844032556bc71d09f05a111c4` on
  `codex/hermes-desktop-readiness`. Its clean stamp is dated
  `2026-08-30T06:18:02.186Z`; Electron Builder produced the isolated x64
  candidate at
  `C:\Dev\hermes-agent-release-candidates\20260830-35c44b1d\win-unpacked\Hermes.exe`.
  Its SHA-256 is
  `2d4d422e278de78c7622c5ded9b3e09b86e2df21625b1f6c96e273086ca5880d`;
  the PE machine is `0x8664`, and all 457 package files were independently
  audited before installation.
- [x] 28. **Codex** — Smoke-test the packaged Desktop artifact itself in an
  isolated `HERMES_HOME`: verify Electron startup, renderer loading, backend
  startup/connection, native dependencies, and the packaged Playwright path
  before replacing the installed copy. Prerequisite: item 27. Completed
  2026-08-30: a direct Playwright launch of the isolated candidate passed with
  exit code zero in both fake-boot and real-backend phases. Electron 40.10.2
  loaded the packaged `app.asar` renderer with the Hermes title and populated
  root, every test window remained hidden, `node-pty` loaded with a callable
  `spawn`, and the packaged `get-windows` module was present. The real source
  backend opened a credential-bearing loopback WebSocket, delivered
  `gateway.ready`, and returned `setup.status`. Evidence is under
  `C:\Dev\hermes-agent-release-candidates\20260830-35c44b1d\evidence` for the
  final published candidate (`candidate-audit.json`, `candidate-smoke.json`,
  `fake-boot.png`, and `real-backend.png`).
  Teardown left zero candidate processes and zero test `electron.exe`
  processes.
- [x] 29. **Codex** — Create and verify a recoverable backup of the currently
  installed Desktop package, launcher, shortcut target, and build stamp; record
  the exact rollback procedure. Prerequisite: item 28. Completed 2026-08-30:
  the installed package, release-root installer/launcher files, install stamp,
  and canonical Taskbar and Start Menu shortcuts were preserved at
  `C:\Dev\hermes-agent-recovery\installed-backup-pre-35c44b1d-20260830`.
  The package contains 457 files totaling 401,014,519 bytes; its installed
  executable SHA-256 is
  `beff8d7d5cd4d9d17853da61096da07f994680e6953514249ffc481814c5bbd1`.
  Full manifests prove the source stayed stable during backup, the backup
  matches the source, and the separately copied rollback rehearsal matches the
  backup. `ROLLBACK.md` and the syntax-checked, process-guarded
  `restore-installed.ps1` record the exact switch-back procedure. The live
  canonical app and both shortcut targets remained unchanged.
- [x] 30. **Both** — Stop/relaunch the Desktop app and gateway on the canonical
  build. Codex performs the recoverable switch; Connor confirms the maintenance
  window and that active work is saved. Prerequisites: items 2 and 29. Completed
  2026-08-30 under Connor's instruction to finish the remaining items. The
  package switch used graceful window closure, preserved the prior package at
  `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830\pre-switch-win-unpacked`,
  verified both shortcuts, installed the published-HEAD candidate byte-for-byte,
  and relaunched through the pinned Taskbar shortcut; no forced process stop
  was required.
- [x] 31. **Codex** — Perform post-switch installed-Desktop verification:
  confirm the Start Menu shortcut target, new clean build stamp, renderer
  behavior, managed runtime version/commits, gateway connection, and a basic
  no-cost chat/tool smoke path. Prerequisite: item 30. Completed 2026-08-30.
  Both shortcuts and the live root resolve to the clean canonical executable;
  all 17 production managed-runtime files match the signed post-rebase source
  after a recoverable nine-file reconciliation; Python syntax compilation
  passed for all 17. A direct live-renderer probe of the canonical executable
  and normal profile observed the Hermes title and Desktop bridge, minted a
  protected loopback gateway connection, returned `setup.status`, and listed
  all eight profiles. The final read-back confirmed the exact executable hash
  and clean stamp, both shortcut targets, one pinned-launch root,
  normal-profile child processes, no temporary debugging flag, zero capability
  drift, and zero test `electron.exe`. Evidence is under
  `C:\Dev\hermes-agent-recovery\deploy-35c44b1d-20260830`.
- [x] 32. **Both** — Identify the expected four notifications by title, trigger,
  and notification type. Connor supplies the expected events; Codex maps them
  to implementation and reproduction paths. Codex's portion is complete: the
  implementation-defined core set is `Approval needed` (`approval.request`, OS
  attention), `Input needed` (clarify/MCP setup/sudo/secret request, OS
  attention), `Hermes finished` (`message.complete`, OS completion), and `Turn
  failed` (turn-ending gateway error, OS completion/error). Connor confirmed
  the complete implementation-defined set on 2026-08-30 when he authorized all
  remaining work; no alternate event titles were requested.
- [x] 33. **Codex** — Reproduce and validate the four-notification behavior in the
  live canonical Desktop app, capture evidence, and fix any confirmed defect.
  Prerequisites: items 31-32. Completed 2026-08-30 for the implementation-defined
  core set. The installed packaged app's native bridge accepted all four exact
  kinds/titles from a hidden canonical instance, and 158 focused renderer/
  gateway-event tests passed across 23 files. Gating, preferences, replay
  baseline suppression, cross-window/session routing, and deduplication passed;
  no defect was reproduced, so no corrective code change was necessary. The
  final published package was rechecked on 2026-08-31 through its live normal
  profile: the native bridge accepted all four kinds/titles again, and the
  secret-safe result is captured in `installed-live-smoke.json`.
- [x] 34. **Connor** — Decide whether the six currently unread sessions should be
  marked read or preserved. Completed 2026-08-30 by preserving all six unread
  sessions; no message-read state was mutated without a specific instruction to
  clear it.
- [x] 35. **Connor** — Decided that classic CLI notification-stack parity is not
  needed because Connor uses only Hermes Desktop. Reopen this item only if
  Connor explicitly changes that usage decision.
- [x] 36. **Codex** — After the canonical build and rollback path are proven,
  permanently remove obsolete `apps/desktop/release-codex/`,
  `apps/desktop/release-codex-3/`, and confirmed leftover managed-test build
  directories. Prerequisites: items 29-33. Completed 2026-08-30 after installed
  chat/tool and notification verification. Eleven exact obsolete release/test
  trees in the recoverable holding area were path-validated and permanently
  removed: 1,382 files totaling 1,203,191,074 bytes. The canonical package,
  current deployment backup, rollback rehearsal, and item-31 runtime backup
  were preserved.
- [x] 37. **Both** — Optionally run CodeRabbit review. Connor authorizes any
  required third-party CLI installation/authentication; Codex runs the review
  and triages results. Prerequisite: item 20. Completed to the no-cost service
  boundary on 2026-08-30 after Connor explicitly authorized installation,
  authentication, and diff submission. CodeRabbit CLI 0.7.5 is installed and
  authenticated in both Ubuntu 24.04/WSL and its signed native Windows x64
  build. Both `doctor` runs pass every check, including authentication, backend,
  and WebSocket reachability. A local secret-shape scan found zero credential
  signatures. Full, light, agent, and plain review attempts against the clean
  committed branch all ended when CodeRabbit's review endpoint closed the
  WebSocket before analysis; the usage counter remained zero and no findings
  were returned. Paid `--use-credits` was intentionally not enabled under
  Connor's no-paid-services rule. This optional external-service failure is
  recorded rather than represented as a successful review.
- [x] 38. **Both** — Publish the completed work. Codex prepares the PR from the
  signed local commits; Connor authorizes pushing and opening the PR.
  Prerequisites: all selected implementation and validation items. Codex's
  local preflight and PR draft are complete in `HERMES_PR_DRAFT.md`; Connor
  explicitly authorized the push and PR on 2026-08-30. The recoverable branch
  `codex/hermes-desktop-readiness-pre-rebase-20260830` preserves the old line.
  The active branch was rebased with signatures onto `origin/main`; every
  commit reports a good signature, and a fresh merge-tree rehearsal is
  conflict-free. The upstream-removed Hermes Bots
  files stayed removed; the OAuth merge retains both upstream's serialized
  resource-lock behavior and the local explicit-authorization regressions.
  Post-rebase affected Python tests, TypeScript checks, lint, diff checks, and
  the eight-profile zero-drift audit pass. The bounded-worker Desktop suite
  completed with 8,684 passes, 34 skips, and four timeouts/cascade failures in
  the single `keys-settings.test.tsx` file; its complete four-test focused run
  then passed with one worker and a 30-second timeout. Remote publication was
  completed to Connor's fork and opened upstream as
  `https://github.com/NousResearch/hermes-agent/pull/98393` on 2026-08-30. The
  PR remains open; GitHub currently reports no reviews or status-check results.
  The final clean package was rebuilt from published HEAD, smoke-tested in
  isolation, installed canonically, reconciled into the managed runtime, and
  verified through the normal Desktop profile on 2026-08-31.
- [x] 39. **Codex** — Produce the final readiness report covering versions,
  health, notifications, configured integrations, remaining optional gaps, test
  results, build stamp, installed shortcut/runtime parity, and rollback
  information. Prerequisite: completion of all selected work. Completed
  2026-08-30 in `HERMES_FINAL_READINESS_REPORT.md`, including the remaining
  shared/Connor-owned publication, CodeRabbit, notification-label confirmation,
  and unread-session decisions.

## Current sequencing and human gates

- Items 40 and 42 must protect state and backups before item 43 rotates any
  credential, or newly issued credentials could be copied back into the same
  unsafe locations.
- Item 41 requires Connor's explicit remote-publication decision because closing,
  replacing, or rewriting an open PR changes public history. Local preparation
  and secret-safe review remain Codex work.
- Items 47-51 and 58 require Connor only for official account consent, provider
  policy choices, device pairing/power/control, network-exposure choice, or a
  reboot window. Codex owns the engineering, diagnostics, and evidence.
- Plaid Production and any other paid-only route remain excluded under Connor's
  no-real-money policy. Item 25 remains removed and must not be recreated.
- No open Codex item may be closed from CLI/source evidence alone when the result
  affects Connor's experience. Each applicable fix must be packaged, installed,
  relaunched, and verified through the canonical green Desktop and normal profile.
