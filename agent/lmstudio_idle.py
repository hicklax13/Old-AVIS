"""Process-wide idle unloading for explicitly managed LM Studio models."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Optional


logger = logging.getLogger(__name__)

IdleKey = tuple[str, str]
TimerFactory = Callable[..., threading.Timer]
UnloadFunction = Callable[[str, str, str], bool]


@dataclass
class _IdleEntry:
    model: str
    base_url: str
    api_key: str
    timeout_seconds: int
    active_turns: int = 0
    generation: int = 0
    timer: Optional[threading.Timer] = None


class LMStudioIdleUnloadCoordinator:
    """Unload explicitly loaded models after all local turns become idle.

    The coordinator is process-wide because a Desktop backend can keep more
    than one cached agent for the same LM Studio runtime. A single lock fences
    timer expiry against a new turn; a turn that arrives after an unload then
    performs the normal explicit-load verification before inference begins.
    """

    def __init__(
        self,
        *,
        timer_factory: TimerFactory = threading.Timer,
        unload_fn: Optional[UnloadFunction] = None,
    ) -> None:
        self._timer_factory = timer_factory
        self._unload_fn = unload_fn
        self._lock = threading.RLock()
        self._entries: dict[IdleKey, _IdleEntry] = {}

    @staticmethod
    def _key(model: str, base_url: str) -> IdleKey:
        return (str(base_url or "").rstrip("/").lower(), str(model or ""))

    def _resolve_unload_fn(self) -> UnloadFunction:
        if self._unload_fn is not None:
            return self._unload_fn
        from hermes_cli.models import unload_lmstudio_model

        return unload_lmstudio_model

    def _cancel_locked(self, entry: _IdleEntry) -> None:
        timer = entry.timer
        entry.timer = None
        if timer is not None:
            timer.cancel()

    def _schedule_locked(self, key: IdleKey, entry: _IdleEntry) -> None:
        self._cancel_locked(entry)
        if entry.active_turns or entry.timeout_seconds <= 0:
            return
        entry.generation += 1
        generation = entry.generation
        timer = self._timer_factory(
            entry.timeout_seconds,
            self._expire,
            args=(key, generation),
        )
        timer.daemon = True
        entry.timer = timer
        timer.start()

    def arm(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
    ) -> Optional[IdleKey]:
        """Remember a verified load and schedule eviction when currently idle."""
        if timeout_seconds <= 0 or not model or not base_url:
            return None
        key = self._key(model, base_url)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                entry = _IdleEntry(model, base_url, api_key, timeout_seconds)
                self._entries[key] = entry
            else:
                entry.model = model
                entry.base_url = base_url
                entry.api_key = api_key
                entry.timeout_seconds = timeout_seconds
            self._schedule_locked(key, entry)
        return key

    def begin(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
    ) -> Optional[IdleKey]:
        """Cancel pending eviction and register one active LM Studio turn."""
        if timeout_seconds <= 0 or not model or not base_url:
            return None
        key = self._key(model, base_url)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                entry = _IdleEntry(model, base_url, api_key, timeout_seconds)
                self._entries[key] = entry
            else:
                entry.model = model
                entry.base_url = base_url
                entry.api_key = api_key
                entry.timeout_seconds = timeout_seconds
            self._cancel_locked(entry)
            entry.generation += 1
            entry.active_turns += 1
        return key

    def end(self, key: Optional[IdleKey]) -> None:
        """Release one active turn and schedule eviction after the quiet period."""
        if key is None:
            return
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return
            entry.active_turns = max(0, entry.active_turns - 1)
            if entry.active_turns == 0:
                self._schedule_locked(key, entry)

    def _expire(self, key: IdleKey, generation: int) -> None:
        # Hold the lock through the bounded local management request. A new
        # turn waits here, then runs its normal explicit-load verification, so
        # inference cannot race an in-progress unload.
        with self._lock:
            entry = self._entries.get(key)
            if (
                entry is None
                or entry.generation != generation
                or entry.active_turns != 0
            ):
                return
            entry.timer = None
            unloaded = self._resolve_unload_fn()(
                entry.model,
                entry.base_url,
                entry.api_key,
            )
            if unloaded:
                logger.info(
                    "LM Studio model %s unloaded after %ss idle",
                    entry.model,
                    entry.timeout_seconds,
                )
                self._entries.pop(key, None)
            else:
                logger.warning(
                    "LM Studio idle unload failed for %s; leaving runtime state unchanged",
                    entry.model,
                )


IDLE_UNLOAD_COORDINATOR = LMStudioIdleUnloadCoordinator()


def configured_idle_seconds(agent: object) -> int:
    value = getattr(agent, "lmstudio_idle_unload_seconds", 0)
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
        else 0
    )


def arm_agent_idle_unload(agent: object) -> Optional[IdleKey]:
    return IDLE_UNLOAD_COORDINATOR.arm(
        model=str(getattr(agent, "model", "") or ""),
        base_url=str(getattr(agent, "base_url", "") or ""),
        api_key=str(getattr(agent, "api_key", "") or ""),
        timeout_seconds=configured_idle_seconds(agent),
    )


def begin_agent_turn(agent: object) -> Optional[IdleKey]:
    if str(getattr(agent, "provider", "") or "").strip().lower() != "lmstudio":
        return None
    return IDLE_UNLOAD_COORDINATOR.begin(
        model=str(getattr(agent, "model", "") or ""),
        base_url=str(getattr(agent, "base_url", "") or ""),
        api_key=str(getattr(agent, "api_key", "") or ""),
        timeout_seconds=configured_idle_seconds(agent),
    )


def end_agent_turn(key: Optional[IdleKey]) -> None:
    IDLE_UNLOAD_COORDINATOR.end(key)
