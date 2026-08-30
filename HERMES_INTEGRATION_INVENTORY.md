# Hermes Desktop integration inventory

Last verified: 2026-08-28 (America/New_York)

Scope: the authoritative green Hermes Desktop app at
`C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`, using the
normal Electron profile at `C:\Users\conno\AppData\Roaming\Hermes` and the
repository-scoped backend home at `C:\Dev\hermes-agent\.hermes`.

This report intentionally contains no credential values, access/refresh tokens,
OAuth codes, recovery codes, passwords, session cookies, or private keys.
Credentials remain in Hermes' ignored local secret/OAuth stores or the operating
system/provider credential store.

## Model and inference routes

| Route | Credential reference | Desktop visibility | Read-only verification | Status / limit |
|---|---|---|---|---|
| Nous Portal | Hermes OAuth store; account `conlaxer13@gmail.com` | Provider + Solar Pro4:Free default | Authenticated; 350 catalog entries | Working |
| Anthropic | `ANTHROPIC_API_KEY` in ignored `.hermes/.env` | Provider/models visible | 10 catalog entries | Working |
| OpenAI API | `OPENAI_API_KEY` in ignored `.hermes/.env` | Provider/models visible | 130 catalog entries | Working |
| Google Gemini | `GOOGLE_API_KEY` in ignored `.hermes/.env` | Google AI Studio visible | 54 models through the official OpenAI-compatible models endpoint | Working |
| DeepSeek | `DEEPSEEK_API_KEY` in ignored `.hermes/.env` | Provider/models visible | 3 catalog entries | Working |
| Hugging Face | `HF_TOKEN` plus persisted MCP OAuth grant | Provider + MCP visible | 136 inference entries; MCP reconnect persists | Working |
| OpenRouter | `OPENROUTER_API_KEY` in ignored `.hermes/.env` | Provider/models visible | 396 catalog entries | Working |
| Vercel AI Gateway | `AI_GATEWAY_API_KEY` in ignored `.hermes/.env` | Provider/models visible | 360 catalog entries | Working |
| xAI | `XAI_API_KEY` in ignored `.hermes/.env` | Provider/models visible | Official models endpoint returns HTTP 403 | Configured; account credits/spending limit exhausted |
| LM Studio / Qwen3.5 4B Q6_K | Local endpoint; no remote secret | Provider/model visible | Desktop tool call + 60,049-token retrieval passed | Opt-in fallback; quality/speed rejected as default; 300 s idle unload |
| GitHub Copilot | Existing `GITHUB_TOKEN` is a classic PAT | Provider visible | Hermes rejects PAT as Copilot auth | Not selected; needs Copilot-specific protected OAuth/subscription |
| OpenAI Codex OAuth | No Hermes grant | Separate subscription route only | Not authenticated | Optional duplicate; protected sign-in required if selected |
| xAI OAuth | No Hermes grant | Separate subscription route only | Not authenticated | Optional duplicate; protected sign-in required if selected |

## Search, browser, media, speech, and automation

| Capability | Selected route | Verification | Status / limit |
|---|---|---|---|
| Web search | Local SearXNG (`SEARXNG_URL`) | Live query returned results | Working |
| Browser automation | Browser Use CLI, local Chrome | CLI/daemon health and Hermes route detection passed | Working; no paid cloud browser |
| Image generation | OpenAI | Credential/route availability passed | Configured; no billable generation run in readiness stage |
| Video generation | xAI | Credential/route availability passed | Configured but live generation is blocked by xAI account limit |
| Text-to-speech | OpenAI, voice `fable` | Provider availability passed | Working |
| Alternate TTS | ElevenLabs (`ELEVENLABS_API_KEY`) | Read-only voices request returned 21 voices | Available, not selected over current OpenAI preference |
| Speech-to-text | Local faster-whisper, model `base` | Package and Hermes provider checks passed | Working |
| Automation | n8n MCP + API-key connection | MCP test discovered 11 tools; API workflows endpoint returned HTTP 200 | Working |

## AI, communications, and media provider audit (item 24m.1)

Last verified 2026-08-28 with read-only official API requests. API keys remain
in the ignored normal-profile `.hermes/.env`; no credential values are included
in this report.

| Provider | Credential / scope posture | Safe live verification | Desktop control surface | Status / next action |
|---|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY`; provider-wide API key | HTTP 200; 10 models | Model provider/picker | Working; revoke or replace at Anthropic to disconnect |
| OpenAI | `OPENAI_API_KEY`; provider-wide API key | HTTP 200; 130 models | Models, image generation, TTS | Working; revoke or replace at OpenAI to disconnect |
| xAI | `XAI_API_KEY`; provider-wide API key | HTTP 403 classified as account credit/spending limit | Model provider and selected video route | Limited; add credits or raise the account limit only if Connor chooses |
| ElevenLabs | `ELEVENLABS_API_KEY`; provider-wide API key | HTTP 200; 21 voices | Alternate TTS/STT route | Working; available but not selected over OpenAI TTS/local STT |
| Twilio | No account SID, auth token, or sending number stored | Account probe skipped; public Twilio Docs MCP search passes | Twilio Docs MCP visible; SMS adapter available but unconfigured | Blocked for account/SMS control; Connor must provide protected credentials and select an owned sending number |
| Google Gemini | `GOOGLE_API_KEY`; Google AI Studio API key | HTTP 200; 54 models | Google AI Studio provider/picker | Working; revoke or restrict the key in Google AI Studio to disconnect |
| DeepSeek | `DEEPSEEK_API_KEY`; provider-wide API key | HTTP 200; 3 models | Model provider/picker | Working; revoke or replace at DeepSeek to disconnect |
| OpenRouter | `OPENROUTER_API_KEY`; provider-wide routing key | HTTP 200; 396 models | Model provider/picker and auxiliary routing | Working; revoke or replace at OpenRouter to disconnect |

## Development, deployment, identity, and application audit (item 24m.2)

Last verified 2026-08-28 with bounded read-only requests. No deployment,
project, identity, league, or application data was changed.

| Service / account | Credential and permission posture | Safe verification / supported controls | Desktop visibility | Status / revocation |
|---|---|---|---|---|
| GitHub `hicklax13` and organization `connorbhickey` | Classic PAT in the ignored normal-profile secret store; organization membership is active with administrator role. The token has substantially broader scopes than Hermes needs, including administrative, repository-delete, workflow, package-delete, and enterprise scopes. The MCP is `untrusted`, so mutating calls require approval. | Official identity and organization reads passed. The official MCP exposes repository, issue, pull-request, workflow, and organization operations. | Green Desktop MCP page; 44 tools. The `/api/config` editor path now restores the raw environment reference and a deployed secret-safe verification confirms that the expanded credential is absent from its response. | Working with excessive-scope accepted risk. Connor declined token rotation on 2026-08-28. Revoke in GitHub settings to disconnect. |
| Vercel | Provider-managed OAuth grant in the persistent normal-profile MCP store | Official `list_teams` read passed; project/deployment controls are available behind MCP trust approval | Green Desktop MCP page; 37 tools | Working and persisted across restart; revoke from Vercel account integrations or remove the MCP grant |
| Clerk / HEATER | HEATER-specific protected key in `C:\Users\conno\.heater_clerk_key`; not copied into Hermes `.env` or the repository | Official owner-user read returned HTTP 200. HEATER uses this server-side identity path; no generic Clerk Desktop adapter is configured. | Available to HEATER operations, not a separate Desktop MCP tile | Working for owned HEATER identity administration; remove/rotate the protected HEATER key to disconnect |
| Railway | Provider-managed OAuth grant in the persistent normal-profile MCP store; MCP is `untrusted` | Official identity, project, service, environment, and deployment-status reads passed for HEATER. Mutating deployment controls require approval. | Green Desktop MCP page; 42 discovered / 41 enabled tools | Working and persisted across a canonical Desktop cold restart; revoke in Railway or remove the MCP grant |
| Yahoo Fantasy Sports / HEATER | OAuth client ID and secret exist in the ignored Hermes secret store; live user tokens are provisioned outside the checked-out HEATER tree. Approved use is read-only private-league access only, with no Yahoo data used for AI grounding or training. | HEATER is the supported application surface. Final production backend and frontend-proxied freshness reads returned HTTP 200, valid Yahoo attribution, three monitored sources, and zero failing sources. | Through the HEATER application, not a generic Desktop MCP | Working for the approved private-league read path; revoke the Yahoo app grant or remove server-side credentials to disconnect |
| HEATER | Vercel/Railway/Clerk/Yahoo provider credentials remain in their protected provider or local stores | Canonical frontend and backend health returned HTTP 200. Railway reports App B, the worker, Postgres, and Redis online with zero recent deployment failures; the latest App B and worker deployments reached `SUCCESS`. | Reachable through its production web application; Railway and Vercel controls are visible in Desktop | Working. Legacy Streamlit App A remains intentionally offline. No restart or redeploy was performed. |

## Google accounts and services audit (item 24m.3)

Both requested account labels are visible as signed-in Chrome accounts on this
laptop. Browser login is not reused as an API credential and no browser cookie,
password, or session token was extracted.

| Account / service | Current authorization | Supported Hermes route | Status / next action |
|---|---|---|---|
| `conlaxer13@gmail.com` | Profile-local OAuth client and full Workspace token are installed in `google-personal`, ACL-protected to Connor and SYSTEM, and ignored by git. Safe Gmail, Calendar, Drive, and Contacts reads passed, and the Gmail profile endpoint identified the account without exposing private content. | Built-in Google Workspace skill for Gmail, Calendar, Drive, Docs, Sheets, and Contacts. | Working in the canonical green Hermes Desktop. The session and auto-refreshing grant survived a full canonical app close/relaunch and a second live Gmail check on 2026-08-29. |
| `cbh76@georgetown.edu` | A separate full Workspace token is installed in `google-school`, ACL-protected to Connor and SYSTEM, and ignored by git. Georgetown granted all eight requested scopes; safe Gmail, Calendar, Drive, and Contacts reads plus an exact identity/scope assertion passed without exposing private content. | Built-in Google Workspace skill, independently profile-scoped and subject to Georgetown administrator policy. | Working in canonical Desktop. `GOOGLE_SCHOOL_DESKTOP_OK` passed, the profile/session survived a full canonical app close/relaunch, and a fresh Gmail check returned `GOOGLE_SCHOOL_RESTART_OK` on 2026-08-29. |
| Two-account persistence | The built-in integration uses one profile-scoped `google_token.json` per profile and automatically refreshes each grant. | Independent `google-personal` and `google-school` profiles prevent token sharing or overwrite. | Both accounts are identity-, API-, canonical-Desktop-, and cold-restart-verified. |
| YouTube | The YouTube Data API v3 is enabled. `google-personal` and `google-school` each have a separate ACL-protected `youtube_token.json` containing exactly `youtube.readonly`; the two grants are distinct, and neither Workspace token was expanded or reused. | The new profile-visible `youtube-account` skill supports authenticated channel, subscription, playlist, and playlist-item reads. It treats Google's `404/channelNotFound` playlist response as an empty result for valid identities that have never created a channel. The existing `youtube-content` skill remains the public-transcript route. | Personal safe probes and `YOUTUBE_PERSONAL_DESKTOP_OK` / `YOUTUBE_PERSONAL_RESTART_OK` passed. Georgetown channel and subscription probes passed; its channel-less playlist state is handled correctly, and `YOUTUBE_SCHOOL_DESKTOP_OK` / `YOUTUBE_SCHOOL_RESTART_OK` passed after a canonical cold restart on 2026-08-29. |
| YouTube Music and YouTube TV | No supported Hermes connector or authorized account-control route was found in the repository or Google's documented YouTube Data API surface. | Consumer browser/app use remains independent of Hermes; device playback routes may be assessed later through Home Assistant/Google Cast. | Unsupported as direct account integrations in the present Desktop; do not represent browser login as API control. |

## Entertainment and personal ecosystem audit (item 24m.4)

| Ecosystem / device | Local evidence | Best supported route | Status / next action |
|---|---|---|---|
| Sonos (eight physical endpoints) | Home Assistant is configured with explicit local hosts and advertises callbacks on the laptop LAN address through published port 1400; no Sonos cloud OAuth credential is required or stored. | Home Assistant's local Sonos integration exposes the endpoints as five logical rooms: Guest room, Portable, Living Room, TV Room, and Bedroom. | Working: all five media players loaded without errors and exposed supported local playback and grouping controls. |
| iCloud `hicklax13@icloud.com` | Neither classic nor Microsoft Store iCloud for Windows is installed; no protected iCloud app password is stored in Hermes | iCloud Mail can use the existing email adapter with an Apple app-specific password. Hermes Apple Notes/Reminders/Find My skills require macOS, which Connor no longer has. | Limited on this Windows-only device; no sign-in attempted |
| Xbox Series X | Windows Xbox application and identity/overlay packages are installed; no Hermes Xbox authorization exists | No supported Hermes control adapter was identified | Unsupported in the present Desktop integration |
| LG Smart Monitor | LG webOS model `27SR50F-WY` is paired on the local network and assigned to Bedroom. | Home Assistant webOS TV integration. | Working: power, volume, and playback controls are exposed. |
| Samsung Smart TV | Samsung Q70 model `QN55Q70TAFXZA` is paired on the local network and assigned to Bedroom. It is distinct from the attached Cast target. | Home Assistant Samsung TV integration. | Working: power, volume, playback, and remote entities are exposed. |
| TCL Roku TV | TCL model `50S450R` is paired on the local network and assigned to Kitchen. | Home Assistant Roku integration. | Working: nine entities include power, remote, active-app, and AirPlay status. |

## Smart-home and network audit (item 24m.5)

| System / user inventory | Current evidence | Safest integration path | Status / next action |
|---|---|---|---|
| Google Hub/Nest displays and Google TV devices | Home Assistant discovered four Google Cast targets: the Basement TV Room TV Chromecast, Connor's Room Nest Hub display, Bedroom Chromecast HD, and Basement TV Room Nest Hub display. Connor completed pairing for two Android TV Remote devices. | Home Assistant Google Cast and Android TV Remote integrations. | Working: four Cast media players and both supported TV remotes are present. |
| Nest cameras (3) and thermostats (2) | Google's official Home Assistant route requires a one-time US $5 Device Access registration. Connor explicitly excluded anything requiring real payment. | No free official control route was found. The temporary Smart Device Management API enablement was reversed; Pub/Sub was never enabled, and no Device Access project or credential was created. | Intentionally skipped under the no-paid-services policy; no charge was incurred and no Nest control is claimed. |
| Eero mesh Wi-Fi | Home Assistant's official UPnP/IGD integration found no compatible device, and Eero does not provide an official Home Assistant control integration. | Seven free Home Assistant Ping monitors cover the gateway at `192.168.4.1` and six mesh nodes at `.39`, `.67`, `.68`, `.105`, `.107`, and `.108`. | Supported monitoring is working: all seven reachability sensors were connected at final verification. Administrative control remains unsupported and no Eero credential is stored. |
| Local-network discovery | Home Assistant performed discovery from the active LAN and found the supported Cast, Android TV, Roku, Samsung, LG webOS, and Sonos devices described above. | Keep discovery and control inside Home Assistant, which is on the correct LAN and provides the supported device adapters. | Working for the discovered integrations; absence of an Eero IGD endpoint and unsupported Xbox/iCloud routes are explicitly classified. |

## Microsoft, Tailscale, and Home Assistant audit (item 24m.6)

| Service | Current evidence / authorization | Hermes route | Status / next action |
|---|---|---|---|
| Microsoft Office and Microsoft services | Word, Excel, PowerPoint, Outlook Classic, and OneDrive are installed; a personal OneDrive folder exists. The PC is not Azure AD, workplace, or domain joined. No Microsoft Graph OAuth/app credential is configured. | Current Hermes Graph code is an organization/app-only webhook and Teams pipeline, not a ready personal delegated mail/calendar/files connector. A personal Microsoft account would require a separately registered delegated OAuth application with least-privilege consent. | Assessment complete; local apps remain available and personal cloud account control is intentionally unconfigured |
| Tailscale | Official Windows client 1.102.3 is installed; Connor completed interactive browser sign-in on 2026-08-28 and the laptop is authenticated to the intended existing tailnet. The Windows service is `RUNNING` with `AUTO_START`. A 2026-08-29 status recheck reported the laptop online, MagicDNS enabled, and no health warnings. No reusable Tailscale API credential is stored in Hermes. | Windows service startup provides automatic reconnection after reboot. If ongoing tailnet administration is wanted later, use a least-privilege OAuth client rather than a broad reusable API key. | Working as the device network and restart-persistent. Tailnet API administration remains intentionally unconfigured; sign out or uninstall the client to disconnect this laptop. |
| Home Assistant | Official stable Home Assistant Container 2026.8.3 runs from `C:\Dev\home-assistant\compose.yaml`, persists configuration under `C:\Dev\home-assistant\config`, restarts unless stopped, and serves `http://127.0.0.1:8123`; ports 8123 and 1400 are published for the UI/API and Sonos callbacks. A recoverable pre-Sonos configuration backup is stored under `C:\Dev\home-assistant\backups\pre-sonos-20260830T0250Z`. Connor completed owner onboarding and created the protected `Hermes Desktop` long-lived token. | `HASS_URL` and `HASS_TOKEN` are stored in ignored profile `.env` files via Hermes's secure credential writer. The all-profile synchronizer propagated them to all eight current profiles without conflicts; future profiles clone the `default` baseline. The runtime-gated `ha_list_entities`, `ha_get_state`, `ha_list_services`, and `ha_call_service` tools are loaded in canonical Desktop. | Working. Final API verification reported 22 enabled config entries, 95 entity states, 64 service domains, and zero unavailable entities. Hermes listed 14 media players and 12 binary sensors, read the Samsung state, and enumerated all services. Revoke the named token from Home Assistant Profile → Security to disconnect Hermes. |
| Home Assistant Windows app | Chrome installed the official Home Assistant PWA directly from `http://127.0.0.1:8123` and registered Windows app ID `Chrome._crx_phgkokbgonpfjjchfdmggaoeie`. Start Menu and taskbar shortcuts are named `Home Assistant`; the taskbar shell now offers `Unpin from taskbar`, confirming the pin. | The standalone app reuses Connor's protected Chrome profile session, opens without normal browser tabs, and provides the complete official Home Assistant UI. No separate long-lived token or third-party desktop client is involved. | Working and free. A live standalone-window check was signed in as Connor Hickey and showed Living Room, Kitchen, Bedroom, Basement TV Room, Guest room, Portable, and TV Room with live media-player and weather summaries. Uninstall from the app menu or Windows Apps settings to remove it. |

## Matrix-wide permission and persistence notes

- Persistent browser sign-in, installed desktop software, and an account label
  are evidence of local availability, not authorization for Hermes to call an
  API. Hermes will use provider OAuth, a protected secret reference, or an
  explicitly paired local server only.
- OAuth refresh can normally preserve sign-in across Desktop and Windows
  restarts, but no application can guarantee permanent authorization after a
  provider revokes a grant, changes policy, requires re-consent, or disables an
  account.
- Device controls remain limited to what each provider and Home Assistant
  exposes. No unsupported “full control” claim is made for Xbox, Nest, Eero
  administration, Google consumer media accounts, or iCloud device data.
- The GitHub PAT's excessive scopes and Connor's decision not to rotate its
  previously displayed value are recorded as accepted risk and are not a
  blocker. The Desktop editor's secret-expansion defect was fixed and deployed
  on 2026-08-28: runtime expansion remains available to the MCP client while
  Desktop receives only the raw environment reference.

## Final permissions and configuration audit (item 24l)

- Backend home: `C:\Dev\hermes-agent\.hermes`; Desktop profile:
  `C:\Users\conno\AppData\Roaming\Hermes`; active connection: local with no
  saved connection token or authorization header.
- MCP inventory: 13 configured, 13 enabled, no duplicate endpoint group, no
  plaintext secret candidate; GitHub and Railway are deliberately `untrusted`.
- Gateway inventory: only Telegram and WhatsApp are enabled; both reported
  `connected` with no recorded error after the canonical Desktop relaunch.
- Redaction verification: related tests passed 12/12; the deployed managed
  module passed all five secret-safe response checks. Recoverable backups are
  `apps/desktop/release/win-unpacked-backup-20260828-mcp-redaction` and
  `.backups/mcp-editor-redaction-managed-runtime-20260828`.
- The formal Codex Security prompt-only scan could not snapshot the selected
  changes in the existing dirty working tree. No formal scan artifact or result
  is claimed; targeted configuration, process, response, and persistence audits
  are recorded instead.

## MCP connection persistence

The following sessions reconnected without a new browser authorization after
the canonical Desktop restart:

| Server | Authentication | Read-only connection test | Status |
|---|---|---|---|
| Cloudflare | OAuth 2.1 PKCE | Connected; 3,408 tools discovered after a full canonical Desktop restart | Working; persisted. Hermes now preserves the provider's OAuth `iss` callback parameter. |
| Hugging Face | OAuth 2.1 PKCE | Connected; 12 tools discovered | Working; persisted |
| Figma | OAuth 2.1 PKCE | Connected; 32 tools discovered | Working; persisted |
| PayPal | OAuth 2.1 PKCE | Connected; 4 tools discovered | Working; persisted |
| Vercel | OAuth 2.1 PKCE | Connected; 37 tools discovered | Working; persisted |
| Railway | OAuth 2.1 PKCE | Connected; 42 tools discovered; live `whoami` passed before and after restart | Working; persisted; 41 tools enabled because opaque `railway-agent` is excluded |
| Stripe | OAuth 2.1 PKCE | Connected; 11 tools discovered after Connor authorized the live account | Working; persisted |
| Twelve Data | OAuth 2.1 PKCE | Connected; 27 tools discovered | Working; persisted |
| n8n | Local stdio + API key in ignored MCP env | Connected; 11 tools discovered | Working |
| Indeed | OAuth 2.1 PKCE; all four advertised scopes and a rotating refresh token persisted | Direct authenticated MCP initialization returned HTTP 403 `invalid_client` / `Client not allowed` | Provider-blocked. Indeed documents this beta MCP endpoint as Claude-Connector-only; Hermes does not impersonate an allowlisted client. |
| Plaid | Classified as `client_credentials`, not interactive browser OAuth; no Plaid client ID or Production secret is stored | Plaid's Dashboard MCP requires a Production-approved team, `PLAID_CLIENT_ID`, `PLAID_PRODUCTION_SECRET`, and `mcp:dashboard`; the previous public browser callback could not satisfy that contract | Provider/account-tier blocked. The server remains installed and enabled, but Desktop no longer offers the impossible browser-consent loop. |

## Live canonical Desktop route sweep (item 24m.8)

The earlier 2026-08-28 running green Desktop backend listed all 13 configured MCP entries. Its
built-in connect/list-tools/disconnect test produced 11 successful routes and
zero connection failures:

| Route | Result |
|---|---|
| Context7 | Working; 2 tools |
| DeepWiki | Working; 3 tools |
| Figma | Working; 32 tools, 1 prompt, 103 resources |
| GitHub | Working; 44 tools, 2 prompts, 4 resources |
| Hugging Face | Working; 12 tools, 155 resources |
| Microsoft Learn | Working; 3 tools |
| n8n | Working; 11 tools |
| PayPal | Working; 4 tools, 1 resource |
| Railway | Working; 42 discovered tools |
| Twilio Docs | Working; 2 tools |
| Vercel | Working; 37 tools, 13 prompts |
| Indeed | Blocked; no cached OAuth grant, so no live consent was triggered |
| Plaid | Blocked; browser callback completed, but token exchange returned HTTP 401 and no token was saved because the official Production client-credentials requirements are not configured |

The same verification window confirmed Telegram and WhatsApp connected without
recorded errors, Tailscale authenticated, and the canonical Desktop process and
both Windows shortcuts resolving to the intended executable.

## All-profile capability baseline and OAuth repair (2026-08-29)

- All eight current local profiles now carry the same enabled baseline of 19
  MCP servers, 103 installed skill paths, and 37 static account/environment
  keys. `scripts/sync_profile_capabilities.py --apply` makes recoverable
  backups, refuses conflicting static credentials, and its final dry-run
  read-back reported zero changes.
- Desktop's create-profile dialog initializes `clone_from` to `default`, so new
  profiles inherit the canonical capability baseline. Refreshable OAuth stores
  remain profile-local and are never copied by the synchronizer.
- Cloudflare's repeated tabs were caused by the Desktop callback bridge dropping
  the authorization server's required `iss` parameter. The callback bridge now
  preserves it through token exchange. The live post-restart test returned
  3,408 tools without opening Chrome.
- Indeed required two narrowly scoped compatibility measures: accept only an
  otherwise byte-identical trailing-slash issuer difference, and omit the
  provider's advertised scopes only from dynamic client registration while
  preserving all four on authorization. The token and refresh token now persist;
  the remaining 403 is provider-side client allowlisting.
- The packaged canonical build stamp is `2026-08-30T01:55:55.276Z`. All live
  `Hermes.exe` processes resolved to
  `apps/desktop/release/win-unpacked/Hermes.exe`, no test `electron.exe` remained,
  the pinned taskbar shortcut resolved to that executable, and the separate
  default gateway retained connected Telegram and WhatsApp sessions.
- Recoverable deployment copies are at
  `apps/desktop/.deployment-backups/win-unpacked-before-oauth-iss-20260829-212838`,
  `apps/desktop/release/win-unpacked.bak`, and
  `.backups/managed-backend-before-oauth-iss-20260829-212838`.

## Selected MCP and standalone-plugin expansion (item 24k)

The 2026-08-28 selection favors official provider endpoints and the smallest
non-duplicative capability surface. The normal backend configuration keeps
secret material in the ignored `.hermes/.env`; the GitHub MCP header on disk is
an environment reference rather than a plaintext token.

| Integration | Provenance and permission posture | Verification | Status |
|---|---|---|---|
| Context7 | Official hosted MCP; anonymous; documentation-only tools | 2 tools discovered; live `resolve-library-id` read returned the expected Next.js library | Working and visible in canonical Desktop |
| Microsoft Learn | Official Microsoft endpoint; anonymous; documentation-only tools | 3 tools discovered; live documentation search returned official Learn results | Working and visible in canonical Desktop |
| Twilio Docs | Official Twilio endpoint; anonymous public beta; read-only documentation search | 2 tools discovered; live WhatsApp documentation search returned Twilio results | Working and visible in canonical Desktop |
| GitHub | Official GitHub remote MCP; existing protected `GITHUB_TOKEN`; `trust: untrusted` so non-read-only tools require approval | 44 tools discovered; token validated as `hicklax13`; live `get_me` read passed; trust-gating tests 11/11 | Working and visible in canonical Desktop |
| Railway | Official Railway hosted MCP; OAuth; `trust: untrusted`; opaque `railway-agent` remains excluded | Query-bearing authorization endpoint and exact registered redirect reuse repaired; official consent completed; 42 tools discovered; live `whoami` passed before and after canonical Desktop restart | Working, persisted, and visible in canonical Desktop; 41 safe tools enabled |

No standalone plugin was added. Package-index searches for GitHub, Playwright,
Serena, Firebase, and Pinecone produced no audited addition that was both needed
and non-overlapping. Playwright duplicates the existing browser route and adds a
high-privilege browser-control server; Serena overlaps the existing GitNexus
code-analysis installation; no Firebase project/configuration or credential was
found; and no owned Pinecone service or approved package was found. These can be
reconsidered only when the later service inventory establishes a concrete owned
consumer.

## Messaging readiness

All adapters are visible in the authoritative Desktop Messaging page. Access is
deny-by-default until an explicit allowlist or approved pairing exists.

| Platform | Hermes-side preparation | User-owned action still required | Status |
|---|---|---|---|
| Telegram | Token saved in ignored Hermes secret store; one numeric owner ID allowlisted; enabled; installed gateway restarted | None | Finished: Bot API authenticated, polling healthy, gateway state connected, Desktop green, and `/status` returned a live response to Connor's iPhone |
| WhatsApp (bundled Baileys bridge) | Personal self-chat selected; QR linked-device session saved in ignored Hermes state; one derived owner number allowlisted without exposing it; pairing DM policy enabled; source/managed dependencies installed; 22 tests pass; gateway restarted | None | Finished end to end: `/status` returned a live response in Connor's iPhone self-chat listing `telegram, whatsapp`; bridge HTTP 200/connected, gateway state connected with no error, and canonical Desktop green |
| BlueBubbles (iMessage) | Desktop URL/password/allowlist controls present | Requires an always-on Mac with Messages + BlueBubbles Server; Connor confirmed the Mac is no longer available | Not selected / unavailable on current devices |
| WhatsApp Business Cloud | Adapter exists but intentionally not duplicated with personal bridge | Requires Meta Business/WABA, app secret/token, public webhook, and recipient policy | Not selected |

## Persistence and revocation

- Hermes OAuth grants and MCP tokens use the persistent normal-profile/backend
  stores and have been verified across canonical Desktop restart. A provider can
  still require reauthentication after server-side revocation, policy change, or
  credential expiry; Hermes cannot bypass those security controls.
- WhatsApp linked-device credentials are stored under the ignored Hermes
  platform session directory and normally survive app/device restarts. The
  one-time pairing QR image was removed after the connection was confirmed.
- Windows denied Scheduled Task creation for this standard-user account, so the
  installed per-user Startup fallback is authoritative. Its hidden watchdog now
  waits on the gateway, exits after an intentional clean stop, and retries a
  nonzero/unexpected exit after 60 seconds. A controlled crash test replaced PID
  22496 with PID 38952 and automatically reconnected both Telegram and WhatsApp.
- A canonical Desktop close/reopen test left the supervised gateway and both
  adapters connected while the app was closed; the pinned canonical executable
  then returned to `Gateway ready` with both platform indicators green. Windows
  shutdown necessarily disconnects while the laptop is powered off; the Startup
  watchdog relaunches at the next Windows sign-in. The final clean supervised
  instance is PID 39412 with all six deep gateway probes passing.
- To revoke a provider, disconnect it in Hermes/provider settings and rotate or
  revoke the provider credential. To revoke WhatsApp, unlink the Hermes device
  in WhatsApp's Linked Devices screen. To revoke BlueBubbles, rotate its server
  password or remove the Hermes webhook/client.
- Desktop package rollback for the local-model deployment is
  `apps/desktop/release/win-unpacked-backup-20260828-lmstudio-idle`.
