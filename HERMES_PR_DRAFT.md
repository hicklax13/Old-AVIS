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

- 1,293 affected Python tests passed (five skipped);
- the post-rebase Desktop suite recorded 8,675 passes and 34 skips; every one of
  the 13 saturated/environment-dependent failures passed in focused reruns. A
  bounded-worker full rerun recorded 8,684 passes and 34 skips, with only four
  timeout/cascade failures in one timing-sensitive file; that complete file
  then passed 4/4 with one worker and a 30-second timeout;
- TypeScript typecheck, ESLint, Python compilation, diff check, secret-shape
  scan, and eight-profile capability dry run passed;
- packaged fake/real backend smoke passed;
- fresh installed chat/tool smoke and all four native notification smoke paths
  passed.

## Publication state

The signed branch is rebased onto current `origin/main`, zero commits behind,
eleven commits ahead, and conflict-free under a fresh merge-tree rehearsal. The
old line is preserved on
`codex/hermes-desktop-readiness-pre-rebase-20260830`. Post-rebase tests and
capability parity checks pass; the final clean Desktop package will be rebuilt
from the published HEAD and must repeat the hidden installed-package
verification before canonical replacement.

No credential or `.env` content is included. Connor explicitly authorized the
push and PR creation on 2026-08-30. CodeRabbit 0.7.5 was installed and
authenticated without paid credits, but its review service closed before
analysis despite all doctor checks passing; no external findings were returned.

Published upstream as `https://github.com/NousResearch/hermes-agent/pull/98393`.
