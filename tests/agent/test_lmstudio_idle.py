from agent.lmstudio_idle import LMStudioIdleUnloadCoordinator


class _FakeTimer:
    def __init__(self, interval, callback, args=()):
        self.interval = interval
        self.callback = callback
        self.args = args
        self.cancelled = False
        self.started = False
        self.daemon = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        self.callback(*self.args)


def test_idle_timer_is_cancelled_for_turn_and_rearmed_afterward():
    timers = []
    unloaded = []

    def timer_factory(*args, **kwargs):
        timer = _FakeTimer(*args, **kwargs)
        timers.append(timer)
        return timer

    coordinator = LMStudioIdleUnloadCoordinator(
        timer_factory=timer_factory,
        unload_fn=lambda model, base_url, api_key: (
            not unloaded.append((model, base_url, api_key))
        ),
    )

    coordinator.arm(
        model="qwen",
        base_url="http://127.0.0.1:1234/v1",
        api_key="local",
        timeout_seconds=300,
    )
    assert timers[0].started is True
    assert timers[0].interval == 300

    token = coordinator.begin(
        model="qwen",
        base_url="http://127.0.0.1:1234/v1",
        api_key="local",
        timeout_seconds=300,
    )
    assert timers[0].cancelled is True
    timers[0].fire()
    assert unloaded == []

    coordinator.end(token)
    assert len(timers) == 2
    assert timers[1].started is True
    timers[1].fire()
    assert unloaded == [("qwen", "http://127.0.0.1:1234/v1", "local")]


def test_last_overlapping_turn_arms_one_idle_timer():
    timers = []

    def timer_factory(*args, **kwargs):
        timer = _FakeTimer(*args, **kwargs)
        timers.append(timer)
        return timer

    coordinator = LMStudioIdleUnloadCoordinator(
        timer_factory=timer_factory,
        unload_fn=lambda *_args: True,
    )
    first = coordinator.begin(
        model="qwen",
        base_url="http://127.0.0.1:1234/v1",
        api_key="",
        timeout_seconds=60,
    )
    second = coordinator.begin(
        model="qwen",
        base_url="http://127.0.0.1:1234/v1",
        api_key="",
        timeout_seconds=60,
    )

    coordinator.end(first)
    assert timers == []
    coordinator.end(second)
    assert len(timers) == 1


def test_zero_timeout_disables_idle_tracking():
    coordinator = LMStudioIdleUnloadCoordinator(
        timer_factory=lambda *_args, **_kwargs: None,
        unload_fn=lambda *_args: True,
    )

    assert (
        coordinator.begin(
            model="qwen",
            base_url="http://127.0.0.1:1234/v1",
            api_key="",
            timeout_seconds=0,
        )
        is None
    )
