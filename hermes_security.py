"""Cross-platform protection for secret-bearing Hermes paths.

POSIX mode bits do not establish a private Windows security boundary.  This
module is deliberately dependency-light so credential, snapshot, backup, and
service-state writers can all apply and read back the same invariant:

* the current user owns the object;
* only the current user and ``NT AUTHORITY\\SYSTEM`` have allowed access; and
* the DACL is protected from broader parent inheritance.

Callers must protect a directory *before* creating sensitive children.  The
directory ACEs are inheritable, and every writer should still verify its final
published file or tree after an atomic replace/copy.
"""

from __future__ import annotations

import os
import secrets
import stat
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator


class PrivatePathError(OSError):
    """A secret-bearing path could not be proven private."""


def _win32() -> tuple[Any, Any, Any, Any]:
    try:
        import ntsecuritycon
        import win32api
        import win32con
        import win32security
    except ImportError as exc:  # pragma: no cover - packaging failure on Windows
        raise PrivatePathError(
            "Windows ACL enforcement requires the pywin32 runtime dependency"
        ) from exc
    return ntsecuritycon, win32api, win32con, win32security


def _current_user_sid() -> Any:
    _, win32api, win32con, win32security = _win32()
    token = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(), win32con.TOKEN_QUERY
    )
    try:
        return win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    finally:
        token.Close()


@lru_cache(maxsize=1)
def _base_allowed_sids() -> tuple[Any, Any]:
    win32security = _win32()[3]
    return (
        _current_user_sid(),
        win32security.ConvertStringSidToSid("S-1-5-18"),
    )


def _normalize_extra_sids(extra_sids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({str(value).strip() for value in extra_sids if str(value).strip()}))
    return normalized


def _allowed_sids(extra_sids: tuple[str, ...] | list[str] = ()) -> tuple[Any, ...]:
    win32security = _win32()[3]
    converted = tuple(
        win32security.ConvertStringSidToSid(value)
        for value in _normalize_extra_sids(extra_sids)
    )
    return (*_base_allowed_sids(), *converted)


def private_sid_strings(
    extra_sids: tuple[str, ...] | list[str] = (),
) -> frozenset[str]:
    """Return all principals allowed by the private Windows boundary."""
    if sys.platform != "win32":
        return frozenset()
    win32security = _win32()[3]
    return frozenset(
        win32security.ConvertSidToStringSid(sid) for sid in _allowed_sids(extra_sids)
    )


def is_reparse_point(path: str | Path) -> bool:
    """Return whether *path* is a symlink or Windows reparse point."""
    target = Path(path)
    try:
        attrs = target.lstat().st_file_attributes
    except (AttributeError, OSError):
        return target.is_symlink()
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _tree_entries(root: Path) -> Iterator[tuple[Path, bool]]:
    """Yield descendants without following symlinks or Windows junctions."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        parent = Path(dirpath)
        retained: list[str] = []
        for name in dirnames:
            child = parent / name
            if is_reparse_point(child):
                continue
            retained.append(name)
            yield child, True
        dirnames[:] = retained
        for name in filenames:
            child = parent / name
            if not is_reparse_point(child):
                yield child, False


def _windows_security_attributes(
    *, directory: bool, extra_sids: tuple[str, ...] | list[str] = ()
) -> Any:
    ntsecuritycon, _, _, win32security = _win32()
    current_user = _base_allowed_sids()[0]
    inherit_flags = 0
    if directory:
        inherit_flags = (
            win32security.OBJECT_INHERIT_ACE
            | win32security.CONTAINER_INHERIT_ACE
        )

    dacl = win32security.ACL()
    for sid in _allowed_sids(extra_sids):
        dacl.AddAccessAllowedAceEx(
            win32security.ACL_REVISION,
            inherit_flags,
            ntsecuritycon.FILE_ALL_ACCESS,
            sid,
        )

    descriptor = win32security.SECURITY_DESCRIPTOR()
    descriptor.SetSecurityDescriptorOwner(current_user, False)
    descriptor.SetSecurityDescriptorDacl(True, dacl, False)
    descriptor.SetSecurityDescriptorControl(
        win32security.SE_DACL_PROTECTED,
        win32security.SE_DACL_PROTECTED,
    )
    attributes = win32security.SECURITY_ATTRIBUTES()
    attributes.SECURITY_DESCRIPTOR = descriptor
    return attributes


def _set_windows_acl(
    path: Path,
    *,
    directory: bool,
    extra_sids: tuple[str, ...] | list[str] = (),
) -> None:
    _, _, _, win32security = _win32()
    current_user = _base_allowed_sids()[0]
    attributes = _windows_security_attributes(
        directory=directory,
        extra_sids=extra_sids,
    )
    descriptor = attributes.SECURITY_DESCRIPTOR
    dacl = descriptor.GetSecurityDescriptorDacl()

    # Reasserting an owner that is already correct needlessly requires
    # WRITE_OWNER.  A current-user-owned directory inherited from a parent may
    # grant only Modify; its owner can still replace the DACL, but cannot call
    # SetNamedSecurityInfo with OWNER_SECURITY_INFORMATION under a standard
    # (non-elevated) token.  Only request an ownership change when one is real.
    current_descriptor = win32security.GetNamedSecurityInfo(
        str(path),
        win32security.SE_FILE_OBJECT,
        win32security.OWNER_SECURITY_INFORMATION,
    )
    existing_owner = current_descriptor.GetSecurityDescriptorOwner()
    owner_matches = (
        win32security.ConvertSidToStringSid(existing_owner)
        == win32security.ConvertSidToStringSid(current_user)
    )
    security_info = (
        win32security.DACL_SECURITY_INFORMATION
        | win32security.PROTECTED_DACL_SECURITY_INFORMATION
    )
    owner_to_set = None
    if not owner_matches:
        security_info |= win32security.OWNER_SECURITY_INFORMATION
        owner_to_set = current_user
    try:
        win32security.SetNamedSecurityInfo(
            str(path),
            win32security.SE_FILE_OBJECT,
            security_info,
            owner_to_set,
            None,
            dacl,
            None,
        )
    except OSError as exc:
        raise PrivatePathError(f"Could not restrict Windows ACL for {path}: {exc}") from exc


def verify_private_path(
    path: str | Path,
    *,
    directory: bool | None = None,
    require_protected: bool = True,
    extra_sids: tuple[str, ...] | list[str] = (),
) -> None:
    """Raise unless *path* has the private current-user/SYSTEM boundary."""
    target = Path(path)
    if not target.exists():
        raise PrivatePathError(f"Private path does not exist: {target}")
    is_directory = target.is_dir() if directory is None else directory

    if sys.platform != "win32":
        path_stat = target.stat()
        mode = stat.S_IMODE(path_stat.st_mode)
        forbidden = stat.S_IRWXG | stat.S_IRWXO
        if mode & forbidden:
            raise PrivatePathError(
                f"Private path has group/other permissions: {target} mode={oct(mode)}"
            )
        if hasattr(os, "geteuid") and path_stat.st_uid != os.geteuid():
            raise PrivatePathError(f"Private path has an unexpected owner: {target}")
        return

    win32security = _win32()[3]
    descriptor = win32security.GetNamedSecurityInfo(
        str(target),
        win32security.SE_FILE_OBJECT,
        win32security.OWNER_SECURITY_INFORMATION
        | win32security.DACL_SECURITY_INFORMATION,
    )
    control, _ = descriptor.GetSecurityDescriptorControl()
    if require_protected and not control & win32security.SE_DACL_PROTECTED:
        raise PrivatePathError(f"Private path still inherits a parent DACL: {target}")

    allowed = private_sid_strings(extra_sids)
    owner = descriptor.GetSecurityDescriptorOwner()
    owner_string = win32security.ConvertSidToStringSid(owner)
    if owner_string not in allowed:
        raise PrivatePathError(f"Private path has an unexpected owner: {target}")

    dacl = descriptor.GetSecurityDescriptorDacl()
    if dacl is None:
        raise PrivatePathError(f"Private path has a null DACL: {target}")

    allow_types = {
        win32security.ACCESS_ALLOWED_ACE_TYPE,
        win32security.ACCESS_ALLOWED_OBJECT_ACE_TYPE,
        getattr(win32security, "ACCESS_ALLOWED_CALLBACK_ACE_TYPE", 9),
        getattr(win32security, "ACCESS_ALLOWED_CALLBACK_OBJECT_ACE_TYPE", 11),
    }
    observed: set[str] = set()
    inheritable: set[str] = set()
    required_inheritance = (
        win32security.OBJECT_INHERIT_ACE
        | win32security.CONTAINER_INHERIT_ACE
    )
    for index in range(dacl.GetAceCount()):
        ace = dacl.GetAce(index)
        ace_type, ace_flags = ace[0][0], ace[0][1]
        mask = ace[1]
        if ace_type not in allow_types or not mask:
            continue
        sid_string = win32security.ConvertSidToStringSid(ace[-1])
        if sid_string not in allowed:
            raise PrivatePathError(
                f"Private path grants access to an unexpected principal: {target}"
            )
        observed.add(sid_string)
        if ace_flags & required_inheritance == required_inheritance:
            inheritable.add(sid_string)

    if observed != set(allowed):
        raise PrivatePathError(
            f"Private path does not grant both current user and SYSTEM: {target}"
        )
    if is_directory and inheritable != set(allowed):
        raise PrivatePathError(
            f"Private directory ACL will not protect future children: {target}"
        )


def secure_private_path(
    path: str | Path,
    *,
    directory: bool | None = None,
    recursive: bool = False,
    extra_sids: tuple[str, ...] | list[str] = (),
) -> int:
    """Apply and read back the private boundary; return objects secured.

    Recursive traversal never follows symlinks or reparse points.  On POSIX,
    directories receive ``0700`` and files receive ``0600``.  On Windows each
    object receives a protected DACL containing only the current user and
    SYSTEM.  Any enforcement or read-back failure is fatal.
    """
    target = Path(path)
    if not target.exists():
        raise PrivatePathError(f"Private path does not exist: {target}")
    is_directory = target.is_dir() if directory is None else directory
    if recursive and not is_directory:
        raise PrivatePathError(f"Recursive private path must be a directory: {target}")

    def apply_one(
        candidate: Path,
        candidate_is_dir: bool,
        *,
        require_protected: bool,
    ) -> None:
        try:
            verify_private_path(
                candidate,
                directory=candidate_is_dir,
                require_protected=require_protected,
                extra_sids=extra_sids,
            )
            return
        except PrivatePathError:
            pass
        if sys.platform == "win32":
            _set_windows_acl(
                candidate,
                directory=candidate_is_dir,
                extra_sids=extra_sids,
            )
        else:
            if hasattr(os, "geteuid"):
                os.chown(candidate, os.geteuid(), -1)
            candidate.chmod(0o700 if candidate_is_dir else 0o600)
        verify_private_path(
            candidate,
            directory=candidate_is_dir,
            extra_sids=extra_sids,
        )

    apply_one(target, is_directory, require_protected=True)
    count = 1
    if recursive:
        for candidate, candidate_is_dir in _tree_entries(target):
            # A child may safely inherit the already-protected parent DACL.
            # If it carries an explicit broad ACE, read-back fails and we
            # replace that child's DACL with a protected private one.
            apply_one(candidate, candidate_is_dir, require_protected=False)
            count += 1
    return count


def secure_private_directory(
    path: str | Path,
    *,
    recursive: bool = False,
    extra_sids: tuple[str, ...] | list[str] = (),
) -> int:
    """Create a directory if needed, then protect and verify it."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return secure_private_path(
        target,
        directory=True,
        recursive=recursive,
        extra_sids=extra_sids,
    )


def verify_private_tree(
    path: str | Path,
    *,
    extra_sids: tuple[str, ...] | list[str] = (),
) -> int:
    """Read back a directory tree without following reparse points."""
    target = Path(path)
    if not target.is_dir():
        raise PrivatePathError(f"Private tree is not a directory: {target}")
    verify_private_path(target, directory=True, extra_sids=extra_sids)
    count = 1
    for candidate, candidate_is_dir in _tree_entries(target):
        verify_private_path(
            candidate,
            directory=candidate_is_dir,
            require_protected=False,
            extra_sids=extra_sids,
        )
        count += 1
    return count


def create_private_file(
    path: str | Path,
    *,
    extra_sids: tuple[str, ...] | list[str] = (),
) -> Path:
    """Atomically create an empty private file and verify its boundary.

    The ACL/mode is supplied to the kernel at creation time.  This avoids the
    exposure window created by ``touch()`` or ``NamedTemporaryFile`` followed
    by a post-creation chmod/DACL rewrite.
    """
    target = Path(path)
    if not target.parent.is_dir():
        raise PrivatePathError(f"Private file parent does not exist: {target.parent}")
    if sys.platform == "win32":
        try:
            import win32file
            import win32con

            handle = win32file.CreateFile(
                str(target),
                win32con.GENERIC_READ | win32con.GENERIC_WRITE | win32con.READ_CONTROL,
                win32con.FILE_SHARE_READ,
                _windows_security_attributes(
                    directory=False,
                    extra_sids=extra_sids,
                ),
                win32con.CREATE_NEW,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None,
            )
            win32file.CloseHandle(handle)
        except OSError as exc:
            raise PrivatePathError(f"Could not create private Windows file {target}: {exc}") from exc
    else:
        try:
            fd = os.open(
                str(target),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                stat.S_IRUSR | stat.S_IWUSR,
            )
            os.close(fd)
        except OSError as exc:
            raise PrivatePathError(f"Could not create private file {target}: {exc}") from exc
    try:
        verify_private_path(target, directory=False, extra_sids=extra_sids)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def create_private_temp_file(
    directory: str | Path,
    *,
    prefix: str = ".private-",
    suffix: str = ".tmp",
    extra_sids: tuple[str, ...] | list[str] = (),
) -> Path:
    """Create a randomly named private file in an existing directory."""
    parent = Path(directory)
    if not parent.is_dir():
        raise PrivatePathError(f"Private temp directory does not exist: {parent}")
    for _ in range(32):
        candidate = parent / f"{prefix}{secrets.token_hex(16)}{suffix}"
        try:
            return create_private_file(candidate, extra_sids=extra_sids)
        except FileExistsError:
            continue
        except PrivatePathError as exc:
            if candidate.exists():
                candidate.unlink(missing_ok=True)
            # A collision can be reported through pywin32 as a generic error.
            if "already exists" in str(exc).lower():
                continue
            raise
    raise PrivatePathError(f"Could not allocate a unique private temp file in {parent}")
