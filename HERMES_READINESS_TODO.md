# Hermes CLI and Desktop Readiness TODO

Saved on 2026-08-27 after the CLI, Desktop, notification, setup, Git, dependency,
and test review.

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
  - [x] 24g. **Connor/Codex** — Applied Connor's existing option-4C maximum-
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
  confirmed zero config, environment, or skill drift. A final clean-tree and
  signature read-back follows this documentation commit before item 27.
- [ ] 27. **Codex** — Build the updated canonical Desktop package with a current,
  clean, verifiable build stamp. Prerequisite: item 26.
- [ ] 28. **Codex** — Smoke-test the packaged Desktop artifact itself in an
  isolated `HERMES_HOME`: verify Electron startup, renderer loading, backend
  startup/connection, native dependencies, and the packaged Playwright path
  before replacing the installed copy. Prerequisite: item 27.
- [ ] 29. **Codex** — Create and verify a recoverable backup of the currently
  installed Desktop package, launcher, shortcut target, and build stamp; record
  the exact rollback procedure. Prerequisite: item 28.
- [ ] 30. **Both** — Stop/relaunch the Desktop app and gateway on the canonical
  build. Codex performs the recoverable switch; Connor confirms the maintenance
  window and that active work is saved. Prerequisites: items 2 and 29.
- [ ] 31. **Codex** — Perform post-switch installed-Desktop verification:
  confirm the Start Menu shortcut target, new clean build stamp, renderer
  behavior, managed runtime version/commits, gateway connection, and a basic
  no-cost chat/tool smoke path. Prerequisite: item 30.
- [ ] 32. **Both** — Identify the expected four notifications by title, trigger,
  and notification type. Connor supplies the expected events; Codex maps them
  to implementation and reproduction paths.
- [ ] 33. **Codex** — Reproduce and validate the four-notification behavior in the
  live canonical Desktop app, capture evidence, and fix any confirmed defect.
  Prerequisites: items 31-32.
- [ ] 34. **Connor** — Decide whether the six currently unread sessions should be
  marked read or preserved.
- [x] 35. **Connor** — Decided that classic CLI notification-stack parity is not
  needed because Connor uses only Hermes Desktop. Reopen this item only if
  Connor explicitly changes that usage decision.
- [ ] 36. **Codex** — After the canonical build and rollback path are proven,
  permanently remove obsolete `apps/desktop/release-codex/`,
  `apps/desktop/release-codex-3/`, and confirmed leftover managed-test build
  directories. Prerequisites: items 29-33.
- [ ] 37. **Both** — Optionally run CodeRabbit review. Connor authorizes any
  required third-party CLI installation/authentication; Codex runs the review
  and triages results. Prerequisite: item 20.
- [ ] 38. **Both** — Publish the completed work. Codex prepares the PR from the
  signed local commits; Connor authorizes pushing and opening the PR.
  Prerequisites: all selected implementation and validation items.
- [ ] 39. **Codex** — Produce the final readiness report covering versions,
  health, notifications, configured integrations, remaining optional gaps, test
  results, build stamp, installed shortcut/runtime parity, and rollback
  information. Prerequisite: completion of all selected work.

## Current blockers for Codex-only work

Codex-only items do not require Connor to design, diagnose, or implement them.
Some are intentionally sequenced behind shared or Connor-owned gates:

- Item 20a can proceed without Connor and remains independent of optional
  third-party account setup.
- PayPal and Hugging Face MCP are no longer blocked. Option 4C account
  selection, messaging application setup, credentials, and external-service
  authorization remain shared or Connor-owned in items 24g-24k. Local-model
  preparation in items 24b and 24d-24e is complete; Connor's subjective
  quality/noise acceptance remains in item 24f.
- The one-service-at-a-time decision keeps the local AI model first. Hugging
  Face MCP follows that service unless its warning blocks current Desktop work;
  Telegram, WhatsApp, iMessage/BlueBubbles, and other selected messaging
  platforms follow one at a time under item 24j.
- The full account/service/device matrix in item 24m must also be executed one
  integration at a time. Connor handles secure sign-in, consent, device pairing,
  account-policy choices, and any irreversible control; Codex handles the
  inventory, adapters, configuration, safe tests, Desktop verification, and
  non-secret reporting. Raw credentials are never written to tracked files.
- Clean canonical build preparation can proceed from the completed Desktop
  validation matrix and item 20a; the removed paid/external diagnostic item is
  not a release prerequisite.
- The installed-Desktop switch waits for Connor's maintenance window in item
  30.
- Four-notification validation waits for Connor to identify the expected
  notifications in item 32.
- Publishing always remains shared because it changes remote repository state.
