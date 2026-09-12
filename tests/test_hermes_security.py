from __future__ import annotations

import sys
from pathlib import Path

import pytest

from hermes_security import (
    PrivatePathError,
    create_private_file,
    private_sid_strings,
    secure_private_path,
    verify_private_path,
    verify_private_tree,
)


pytestmark = [
    pytest.mark.windows_only,
    pytest.mark.skipif(sys.platform != "win32", reason="Windows DACL tests"),
]


def _allowed_sid_strings(path: Path) -> set[str]:
    import win32security

    descriptor = win32security.GetNamedSecurityInfo(
        str(path),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION,
    )
    dacl = descriptor.GetSecurityDescriptorDacl()
    assert dacl is not None
    allow_types = {
        win32security.ACCESS_ALLOWED_ACE_TYPE,
        win32security.ACCESS_ALLOWED_OBJECT_ACE_TYPE,
        getattr(win32security, "ACCESS_ALLOWED_CALLBACK_ACE_TYPE", 9),
        getattr(win32security, "ACCESS_ALLOWED_CALLBACK_OBJECT_ACE_TYPE", 11),
    }
    return {
        win32security.ConvertSidToStringSid(dacl.GetAce(index)[-1])
        for index in range(dacl.GetAceCount())
        if dacl.GetAce(index)[0][0] in allow_types and dacl.GetAce(index)[1]
    }


def test_recursive_acl_replaces_broad_inheritance_and_protects_future_children(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private-root"
    child = root / "nested"
    child.mkdir(parents=True)
    existing = child / "existing.json"
    existing.write_text("{}", encoding="utf-8")

    assert secure_private_path(root, directory=True, recursive=True) == 3
    assert verify_private_tree(root) == 3
    for path in (root, child, existing):
        assert _allowed_sid_strings(path) == set(private_sid_strings())

    future_dir = root / "future"
    future_dir.mkdir()
    future_file = future_dir / "future.db"
    future_file.write_bytes(b"state")
    # Future descendants inherit only the two allowed principals from the
    # protected root. They need not each carry an explicit protected bit.
    assert verify_private_tree(root) == 5


def test_private_parent_propagates_to_existing_descendants(tmp_path: Path) -> None:
    root = tmp_path / "propagated-root"
    child = root / "existing"
    child.mkdir(parents=True)
    existing = child / "state.db"
    existing.write_bytes(b"state")

    secure_private_path(root, directory=True, recursive=False)

    assert verify_private_tree(root) == 3
    assert _allowed_sid_strings(existing) == set(private_sid_strings())


def test_readback_rejects_an_unexpected_allowed_principal(tmp_path: Path) -> None:
    import ntsecuritycon
    import win32security

    target = tmp_path / "secret.json"
    target.write_text("{}", encoding="utf-8")
    secure_private_path(target, directory=False)

    descriptor = win32security.GetNamedSecurityInfo(
        str(target),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION,
    )
    dacl = descriptor.GetSecurityDescriptorDacl()
    assert dacl is not None
    dacl.AddAccessAllowedAceEx(
        win32security.ACL_REVISION,
        0,
        ntsecuritycon.FILE_GENERIC_READ,
        win32security.ConvertStringSidToSid("S-1-1-0"),
    )
    win32security.SetNamedSecurityInfo(
        str(target),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION
        | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        dacl,
        None,
    )

    with pytest.raises(PrivatePathError, match="unexpected principal"):
        verify_private_path(target, directory=False)


def test_private_file_is_restricted_at_creation_under_a_broad_parent(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "broad-parent"
    parent.mkdir()
    target = create_private_file(parent / "secret.db")

    verify_private_path(target, directory=False)
    assert _allowed_sid_strings(target) == set(private_sid_strings())


def test_hardening_cli_recurses_by_default_and_repairs_explicit_child_acl(
    tmp_path: Path,
) -> None:
    import ntsecuritycon
    import win32security

    from scripts.harden_sensitive_state import main

    root = tmp_path / "sensitive-state"
    root.mkdir()
    child = root / "protected-but-broad.json"
    child.write_text("{}", encoding="utf-8")
    secure_private_path(root, directory=True, recursive=True)

    descriptor = win32security.GetNamedSecurityInfo(
        str(child),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION,
    )
    dacl = descriptor.GetSecurityDescriptorDacl()
    assert dacl is not None
    dacl.AddAccessAllowedAceEx(
        win32security.ACL_REVISION,
        0,
        ntsecuritycon.FILE_GENERIC_READ,
        win32security.ConvertStringSidToSid("S-1-1-0"),
    )
    win32security.SetNamedSecurityInfo(
        str(child),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION
        | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        dacl,
        None,
    )

    assert main(["--apply", "--root", str(root)]) == 0
    verify_private_tree(root)
