# Draft PR handoff

## Proposed title

`feat: finalize Hermes Desktop profile, OAuth, and local-runtime rollout`

## Summary

- synchronize installed MCP, skill, and static-account capabilities across all
  current profiles while keeping rotating OAuth stores profile-local;
- persist explicit MCP OAuth authorization correctly and harden the Windows
  Desktop/runtime paths used by Connor's canonical app;
- add the read-only YouTube account skill and optional LM Studio memory
  management;
- record the secret-safe integration inventory, clean package evidence,
  installed Desktop verification, native notification matrix, and rollback
  path.

## Verification

- 1,285 affected Python tests passed (five skipped);
- 7,998 Desktop Vitest tests passed (34 skipped);
- 625 Desktop plugin tests passed;
- TypeScript typecheck, ESLint, Python compilation, diff check, secret-shape
  scan, and eight-profile capability dry run passed;
- packaged fake/real backend smoke passed;
- fresh installed chat/tool smoke and all four native notification smoke paths
  passed.

## Required before push

The local branch is 479 commits behind `origin/main`. Resolve the read-only
merge rehearsal's six conflicts (four upstream-deleted Hermes Bots files plus
`tools/mcp_oauth_manager.py` and its bidirectional OAuth test), rerun affected
tests, rebuild with a clean stamp, and repeat the hidden installed-package
verification. Do not publish tracked readiness files if maintainers prefer them
as local handoff artifacts.

No credential or `.env` content is included. Connor must explicitly authorize
the push and PR creation.
