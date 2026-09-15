# Hermes update resolution and security audit review

Verified on September 13, 2026, on ASUS_PRO_LAPTOP.

**Subsequent completion, 20:56 ET:** the security upgrade and Desktop maintenance
reporting repairs are now installed and verified. Fresh in-app audits report
0 known vulnerabilities across 142 components, and all eight profiles load.
See [the completed repair record](C:/Dev/hermes-agent/HERMES_SECURITY_REPAIR_20260913.md).
The review section below preserves the earlier pre-installation findings.

## Installed update

The 135-commit update from `3f86ed75dad1933036c52018e991dbd839837126` to
`a7254e2d4c170725a4136591e96efc5066251d2c` is installed in the managed checkout and
the canonical taskbar app. Hermes reports 0.21.2; the Desktop package is 0.17.2
and Electron is 41.10.3. The normal updater subsequently completed successfully,
restored all resolved local repairs, and returned exit code 0 at 19:27:32 ET.

The two Git conflicts were in MCP connection registration and its regression
tests. The resolution retains the upstream checks for client certificates and
the consuming profile's trust policy. OAuth connections remain isolated unless
both profiles resolve to the same explicitly configured owner and OAuth client.
The shared owner remains `default`; no OAuth stores were copied.

The original local changes are preserved in recovery stash
`9a008997bf42f840049b08b0e4c332488a26f7ba`, a complete source backup, and a
verified 500-file package backup. The previous package is also retained by the
staged promotion mechanism. No project commits were created or pushed.

The updater's required-restore failure guard remains installed. A later conflict
must stop the update rather than silently omit local repairs. Future upstream
edits can still require a new merge; no permanent conflict-free guarantee is made.

## Verification

- 79 focused Python tests passed; one platform-specific test was skipped.
  This includes MCP isolation/ownership/trust and updater stash, preservation,
  and retry behavior. The updater fixture now isolates Windows gateway control
  and user Git signing configuration; a removed upstream argument was updated
  in the local restore regression test.
- 243 Desktop tests passed, including onboarding, MCP health/cache, profile and
  session routing, and settings localization. Production build and packaging passed.
- The packaged candidate launched with no visible test window and passed a
  native terminal smoke test. Final process inspection found no test Electron.
- Relaunched through the pinned shortcut, whose target was verified before and
  after deployment. The live root process is PID 46452 at
  `C:\Dev\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`, using
  `C:\Users\conno\AppData\Roaming\Hermes`.
- All eight profiles were opened in the canonical Desktop and reached Gateway
  ready. Their actual owned backends answered runtime readiness and session-list
  requests with matching profile identities: default, builder, development,
  google-personal, google-school, operator, researcher, reviewer.
- The messaging gateway restarted as PID 82788 and reports the same updated SHA.
- All eight profiles retain the same 15 enabled MCP definitions and nine shared
  OAuth owners. Plaid, Strava, Indeed, and Unreal Engine remain removed.
- The saved pool limit is eight, with a seven-day idle timeout.
- Installed `app.asar` SHA-256:
  `03ce41c2330d35f54b3a04fd3bb8082aa975087267fa25392fdfc9fefd0e9385`.

Evidence is in `C:\Dev\hermes-agent-recovery\update-resolution-20260913`, notably
`source-cutover-proof.json`, `updater-receipt.json`, `deployment-proof.json`,
`native-profile-checks.json`, `all-eight-after-update.json`,
`shared-mcp-readback.json`, and `final-process-proof.json`.

Readiness checks did not generate new model responses, invoke every remote MCP,
or test cold reboot/sleep recovery. Remote provider availability remains external.

## Historical security audit review — before the subsequent installation

A fresh audit of the installed managed runtime reproduced 12 findings across
142 components. Both `httpx2` and `httpcore2` remain installed at 2.7.0. The
findings describe five underlying vulnerabilities, with duplicate GHSA/PYSEC
records and one vulnerability affecting both distributions.

| Issue | Affected component | Minimum patched version | Advisory |
| --- | --- | --- | --- |
| Secure WebSocket traffic lacks TLS through SOCKS proxies | httpx2 and httpcore2 | 2.10.0 | [GHSA-7mj9-2mp8-4m2p](https://github.com/advisories/GHSA-7mj9-2mp8-4m2p) |
| Excessive memory allocation during streamed decompression | httpx2 | 2.12.0 | [GHSA-8xx6-hgc6-gc2m](https://github.com/advisories/GHSA-8xx6-hgc6-gc2m) |
| Excessive CPU use for malicious SSE input | httpx2 | 2.10.0 | [GHSA-f2fp-rgf2-35cp](https://github.com/advisories/GHSA-f2fp-rgf2-35cp) |
| Multipart header injection | httpx2 | 2.11.0 | [GHSA-h4x7-gw46-3wm6](https://github.com/advisories/GHSA-h4x7-gw46-3wm6) |
| Conflicting HTTP request framing headers | httpx2 | 2.11.0 | [GHSA-pf96-p4fj-6566](https://github.com/advisories/GHSA-pf96-p4fj-6566) |

The concrete repair is to replace the three `httpx2==2.7.0` pins in
`pyproject.toml` (dev, mcp, and computer-use extras) with `httpx2==2.12.0`,
regenerate `uv.lock`, and upgrade both runtime distributions to 2.12.0.
Changing the installed packages alone would leave the old manifest pins able to
reintroduce 2.7.0 during a future dependency synchronization.

PyPI currently lists 2.12.0 for both packages. HTTPX2 2.12.0 requires the matching
HTTPCORE2 version; MCP 2.0.0 permits HTTPX2 >=2.5.0. The installed-environment
resolver dry run succeeds and proposes exactly those two upgrades, with no
other package changes. An OSV query of the two proposed 2.12.0 distributions
returns zero known findings. This is dependency-resolution evidence, not a
completed runtime integration test or an installed security fix.

Before delivering that repair, validate the regenerated lockfile, test the MCP
HTTP/OAuth paths with the patched packages, restart Desktop and the gateway,
and rerun the full audit and canonical profile checks.

Review evidence: `security-audit-current.json`, `patched-package-metadata.json`,
`security-upgrade-plan.log`, and `patched-version-osv-check.json` in the recovery
directory above. The installed security dependencies were not changed during
this review.
