"""Apply or verify private ACLs on explicit sensitive-state roots.

The command is intentionally path-explicit.  It never guesses an external
Home Assistant, Desktop, or backup location and refuses drive roots, the user
profile root, and the source checkout itself.

Examples::

    python scripts/harden_sensitive_state.py --root C:\\path\\to\\state
    python scripts/harden_sensitive_state.py --apply --root C:\\path\\to\\state
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hermes_security import (  # noqa: E402
    PrivatePathError,
    is_reparse_point,
    secure_private_path,
    verify_private_path,
    verify_private_tree,
)


def _validated_root(raw: Path) -> Path:
    expanded = raw.expanduser()
    # Check the path object before resolve(), which would erase the evidence
    # that the final component is a symlink or junction.
    if expanded.is_symlink() or is_reparse_point(expanded):
        raise PrivatePathError(f"Refusing symlink/reparse ACL root: {expanded}")
    root = expanded.resolve(strict=True)
    home = Path.home().resolve(strict=True)
    forbidden = {
        Path(root.anchor).resolve(strict=True),
        home,
        PROJECT_ROOT.resolve(strict=True),
        PROJECT_ROOT.parent.resolve(strict=True),
    }
    if root in forbidden or len(root.parts) < 3:
        raise PrivatePathError(f"Refusing unsafe ACL root: {root}")
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        required=True,
        type=Path,
        help="existing sensitive-state directory; repeat for multiple roots",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply ACLs before read-back (default is verify-only)",
    )
    traversal = parser.add_mutually_exclusive_group()
    traversal.add_argument(
        "--recursive",
        dest="recursive",
        action="store_true",
        help="normalize and verify every descendant (the default)",
    )
    traversal.add_argument(
        "--root-only",
        dest="recursive",
        action="store_false",
        help="only process each named root; intended for narrow diagnostics",
    )
    parser.set_defaults(recursive=True)
    parser.add_argument(
        "--allow-sid",
        action="append",
        default=[],
        help="additional narrowly scoped Windows service SID; repeat as needed",
    )
    args = parser.parse_args(argv)

    results: list[dict[str, object]] = []
    try:
        roots = [_validated_root(path) for path in args.root]
        if len({str(path).casefold() for path in roots}) != len(roots):
            raise PrivatePathError("Duplicate ACL roots are not allowed")
        for root in roots:
            if args.apply:
                # secure_private_path performs a read-back after every DACL
                # write and on every descendant. Do not walk a very large
                # state tree a second time merely to produce the same count.
                changed = secure_private_path(
                    root,
                    directory=True,
                    recursive=args.recursive,
                    extra_sids=args.allow_sid,
                )
                verified = changed
            elif args.recursive:
                changed = 0
                verified = verify_private_tree(root, extra_sids=args.allow_sid)
            else:
                changed = 0
                verify_private_path(root, directory=True, extra_sids=args.allow_sid)
                verified = 1
            results.append(
                {
                    "path": str(root),
                    "applied_objects": changed,
                    "verified_objects": verified,
                }
            )
    except (OSError, PrivatePathError) as exc:
        print(f"Sensitive-state ACL operation failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"mode": "apply" if args.apply else "verify", "roots": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
