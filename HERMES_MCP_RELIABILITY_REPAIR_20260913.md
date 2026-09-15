# Hermes Desktop MCP repair — September 13, 2026

## Current outcome after the later update

Connor confirmed that Plaid, Strava, Indeed, and Unreal Engine were intentionally
removed and should remain removed. Final read-back on September 13 confirms the
remaining 15 enabled definitions and nine shared OAuth owners across all eight
profiles. The subsequent update and Doctor repairs are deployed and verified in
the canonical app; see `HERMES_DOCTOR_REPAIR_20260913.md` for the current build and
evidence. The earlier 19-server counts below describe the state before this choice.

## Earlier verified MCP repair outcome

The repair is installed in the canonical Desktop app and its normal Windows profile.
All eight local Hermes profiles have the same 19 MCP definitions enabled and resolve
the 11 OAuth definitions to a single default-owned credential store. Existing OAuth
files were not copied between profiles. Unrelated settings read back unchanged.

Fifteen services now connect in the repaired canonical Desktop app. Fourteen passed
harmless real tool calls; PayPal passed connection and discovery only. Cloudflare and
Stripe now work in default and google-personal with the same default-owned grants.
Four other configured servers have unmet prerequisites. Their enabled switches remain
on, with explicit reasons. This is not an all-servers-working claim.

## Confirmed causes and changes

1. **Lost OAuth issuer.** Desktop's callback relay forwarded the code and state but
   dropped the authorization server's `iss` parameter. Cloudflare advertises issuer
   validation, so the SDK correctly rejected the relayed response. The native callback,
   Desktop bridge, JSON-RPC path, local gateway callback, and dashboard callback now
   preserve the issuer. State, replay, and SDK issuer validation remain enabled.
2. **Destructive reauthentication.** A new sign-in could remove a usable grant before
   replacement succeeded. Desktop, dashboard, and CLI browser reauthentication now
   write to a temporary store and commit only after successful authentication. Failed,
   cancelled, or incomplete sign-ins preserve the existing grant. Device-flow commits
   use the same protected ownership boundary.
3. **Independent profile grants and refresh races.** The explicit `mcp_shared_from:
   default` configuration uses default as the MCP editing authority. OAuth references
   use `oauth.token_owner: default`; they do not duplicate rotating refresh tokens.
   Cross-process Windows locks serialize refresh, reread the latest grant after locking,
   and release on cancellation. Provider and connection caches include owner/client
   identity. Profiles without this explicit opt-in retain isolation.
4. **Configuration drift.** Named profiles now read current default MCP definitions.
   Active gateway reconciliation watches the owner's config and credential file.
   Static credential references resolve in default's scope, never silently fall back
   to another profile's account, and fail with an actionable prerequisite if absent.
   Unrelated settings saves preserve the raw local configuration; MCP edits in a
   borrowing profile return an instruction to edit default. Desktop's existing
   create-profile default remains cloning default, which carries the sharing policy.
5. **Misleading retry/authentication notifications.** Explicit unmet prerequisites are
   now represented separately from transient failures or missing authentication across
   runtime discovery, probes, RPC/REST, and Desktop. Such servers are not repeatedly
   probed or offered futile sign-in attempts. Ordinary network recovery and resume
   handling remain active for eligible servers.
6. **Automatic startup.** `Hermes Desktop.lnk` was installed in the current user's
   Windows Startup folder by copying the verified pinned shortcut. It launches the
   canonical app at Windows sign-in. The existing hidden Hermes gateway startup and
   retry behavior is preserved under the current profile-scoped Startup filename,
   `Hermes_Gateway_9836f4d8.vbs`. The obsolete duplicate Startup entry was moved to
   recovery. The current gateway helper recognizes the single entry, and launching
   that exact entry produced one gateway process. Closing Desktop intentionally quits that app;
   minimizing leaves it running. Startup does not bypass Windows sign-in or sleep.
7. **Stripe delayed-consent state replacement.** A staged live Stripe witness reproduced
   one accepted authorization state at 1.265 seconds and a different accepted state at
   62.281 seconds, before cancellation. `_probe_single_server` allowed a long outer
   OAuth wait but failed to pass that timeout to the underlying transport, which still
   used its 60-second handshake timeout. A retry replaced the state belonging to the
   original browser page. No browser was opened, callback submitted, or grant committed
   by this diagnostic, and the existing grant metadata remained unchanged. The timeout
   propagation and immutable first-publication repair passed the real loopback OAuth
   regression and a live 71.546-second wait without state replacement. The interactive
   probe budget now includes URL setup, the full 300-second consent window, and token
   exchange; it does not change persisted ordinary connection timeouts. Ended sign-ins
   stop retrying. Concurrent temporary probes reserve their loop, and lifecycle
   serialization prevents an old loop's cleanup from killing a new loop's local MCP
   processes. State and issuer checks remain intact.

## Provider prerequisites and remaining actions

| Server | Current result / required action |
| --- | --- |
| Hugging Face | Canonical Desktop shows 12 tools and 155 resources in default and google-personal without separate sign-in. Real `hf_whoami` calls passed in both profiles; identity data was discarded. |
| Webflow | Canonical Desktop shows 31 tools and 6 resources in both profiles. The read-only guide and `data_sites_tool` with only `list_sites` passed in both. |
| Cloudflare | Fresh real Desktop sign-in succeeded. Canonical Desktop shows 3 tools in both profiles; real `docs` and `search` calls passed in both. No `execute` call was used. |
| Stripe | The additional timeout and lifecycle repairs are deployed and reviewed. A fresh default-owned grant was recorded at 15:13:18 ET. Native Desktop shows 10 tools in default and google-personal; real `search_stripe_documentation` calls passed in both without further sign-in. Failed earlier reauthentication preserved the previous grant. |
| Plaid | Connor confirmed no approved Production access. The official Dashboard MCP requires approved Production access and Production credentials; an ordinary account is insufficient. [Plaid documentation](https://plaid.com/docs/resources/mcp/) |
| Strava | Connor confirmed no subscription. The official MCP requires one and currently documents Claude clients. No subscription was purchased. [Strava documentation](https://support.strava.com/en-us/articles/15401531-what-is-the-strava-mcp-connector) |
| Indeed | The official beta currently supports Claude Connector. Hermes must not impersonate that client. [Indeed documentation](https://docs.indeed.com/mcp) |
| Unreal Engine | No MCP listener was available on 127.0.0.1:8000. The official integration requires Unreal Editor 5.8, an open project, and its MCP plugin running. No engine/project was installed or changed. [Epic documentation](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor) |

When a prerequisite is satisfied, update the default definition to remove its
`blocked_reason`; all sharing profiles inherit the change. A genuine provider outage,
revoked grant, account restriction, network loss, Windows sleep, or explicit app quit
cannot be eliminated by this repair. Successful sign-in is shared; perpetual provider
authorization is not guaranteed.

## Verification and deployment

- OAuth regression suite: 184 passed, one POSIX-only skip. Includes actual competing
  Windows processes refreshing one grant, cancellation, staged rollback, owner/client
  isolation, and pending metadata not overwriting a newer login.
- CLI sign-in regression suite: 9 passed, including three preservation cases that
  failed before the staged replacement fix.
- Shared config and real REST regression tests: 12 passed. These cover all behavioral
  loaders, fresh default changes, static credential ownership, missing-key recovery,
  unrelated settings round trips, and rejection of divergent named-profile edits.
- Callback/relay integration checks: 41 passed in the combined focused Python run;
  Desktop callback/relay checks: 9 passed. The missing-issuer regressions failed before
  forwarding the field. These groups overlap with portions of other reported suites.
- Prerequisite tests: 25 Python tests across seven files and 35 Desktop tests across
  three files passed. Desktop type checks, focused ESLint, production build, and
  `git diff --check` passed. Ruff was unavailable in the test environment.
- Additional delayed-consent/lifecycle checks passed: 48 tests with three platform
  skips, 60 existing CLI config and Desktop callback tests, and a final 22-test loop
  lifecycle/concurrent OAuth batch with three platform skips. These groups overlap.
  The delayed OAuth tests use real loopback HTTP and the MCP SDK; the restart test
  uses two real loops and the actual child ledger without signaling real processes.
  A separate code review found no remaining blocker in this scoped repair.
- The packaged candidate rendered successfully with every test window hidden. It was
  closed afterward; no test Electron process remained.
- The canonical app and old MCP-serving processes were stopped before migration.
  The detached gateway drained cleanly and restarted through its existing supervisor;
  its final root PID is 79240. The canonical app was relaunched through the pinned
  shortcut, root PID 64380. Five child processes identify the normal
  `C:\Users\conno\AppData\Roaming\Hermes` user-data directory.
- Native Desktop verification showed `Gateway ready`, `v0.21.2 5dea46d`, Hugging Face
  and Webflow tools, default-owned OAuth configuration, and the new `Prerequisite
  unmet` state. The managed release junction still targets the canonical outer
  release directory. Package content verification reported `build_needed: false`.
- Final native profile switching to google-personal showed all 19 definitions:
  15 connected and four prerequisites. No new sign-in was performed for this borrowing
  profile. Stripe, Cloudflare, Hugging Face, and Webflow were also tested
  with actual harmless calls in both default and google-personal. Separate default
  runtime diagnostics verified real calls to n8n, Figma, Vercel, Context7, Microsoft
  Learn, Twilio Docs, GitHub, Railway, DeepWiki, and Twelve Data. PayPal's five tools
  were discovered but financial operations were not invoked. Every temporary diagnostic
  connection closed and interactive authentication was suppressed.
- The installed ASAR SHA-256 is
  `D7A86DF9FAC980DF4893B37D40D3A199B9DF2EC01318403F57ACC222391C5B2F`.
- The current runtime remains Hermes 0.21.2 / Desktop package 0.17.2, including the
  latest verified release v2026.9.11 plus subsequent main-channel changes. The earlier
  completed updater repair is documented in `HERMES_DESKTOP_UPDATE_REPAIR_20260913.md`.

The required general `sync_profile_capabilities.py --apply` was attempted. It refused
before writes because default and the named profiles have conflicting copies of
`productivity/project-pilot` and `smart-home/sonos-youtube-music-playback`. Those unrelated
skills were preserved. The dedicated MCP migration independently verified all eight
profiles' definitions, enabled state, credential ownership, and unchanged other settings.

## Recovery and evidence

`C:\Dev\hermes-agent-recovery\mcp-reliability-20260913` contains:

- A verified full pre-repair Desktop package: 500 files, 402,688,614 bytes, with
  file-by-file SHA-256 manifest.
- Build, type-check, packaging, hidden launch, gateway, and profile-sync evidence.
- `profile-readback.json`: all eight profiles match, all 19 enabled, 11 shared OAuth
  definitions, four explicit prerequisites, unrelated settings preserved.
- `profile-readback-after-login.json`: the same invariants still pass after Cloudflare
  sign-in. `canonical-shared-profile-witness.json` records native Desktop profile proof.
- Final evidence supersedes the intermediate Stripe status:
  `final-profile-readback.json`, `canonical-final-mcp-witness.json`, and
  `stripe-readonly-runtime-invoke.json`. Stripe's new owner grant metadata stayed
  unchanged through both verification calls, and all temporary connections closed.
- `cloudflare-runtime-invoke.json`, `hf-webflow-runtime-invoke.json`, and
  `remaining-mcp-verified-summary.json` record the sanitized real-tool results.
- `stripe-auth-publish-timeout-witness.json` records the live delayed-consent failure
  without exposing authorization state, codes, URLs, or credentials.
- `managed-repair.patch`, 74 source/test files, and `managed-source-manifest.json`.
  This preserves the current managed working tree, including the earlier updater fixes.
- `pre-stripe-win-unpacked` is a second verified full package backup (500 files,
  402,689,884 bytes). The follow-up package passed a hidden launch check; teardown
  left zero test Electron or candidate Hermes processes.
- `stripe-backend-oauth-final-proof.md` records the additional fixes and their tests.
- `stripe-deployment-proof.json` and `final-process-proof.json` confirm the installed
  package, fresh runtime processes, normal profile, and zero test app processes.
- `gateway-startup-migration.json` records consolidation of the obsolete unsuffixed
  Startup entry into the current profile-scoped name. A manual helper start had failed
  to recognize the old entry and briefly attempted two starts; the duplicate process
  exited. Both were drained before launching the single retained retry wrapper. Its
  exact original behavior and runtime path are preserved, with recoverable backups.

Private configuration backups are under
`C:\Dev\hermes-agent\.hermes\backups\mcp-reliability-20260913`.
The canonical release also retains `win-unpacked.previous`. OAuth regression logs
are under `C:\Dev\hermes-agent-recovery\desktop-update-20260913\mcp-*`.
No credentials were included in this report or source backup. No commits or pushes
were made. The four original unrelated outer working-tree edits remain untouched.

Only the four provider prerequisites remain open for the requested MCP connections.
Cloudflare and Stripe are verified in the installed app and with real read-only calls.
No full Windows reboot or continuous-uptime guarantee is claimed.
