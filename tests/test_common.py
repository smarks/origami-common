"""origami_common's framework-level utilities, tested in isolation."""
import json

import pytest
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory

from origami_common.decorators import rate_limit
from origami_common.helpers import (
    _json_error,
    _parse_json_body,
    _permission_denied,
    _require_field,
)
from origami_common.mixins import ActivePageMixin


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _anon_request(path="/"):
    request = RequestFactory().get(path)
    request.user = type("Anon", (), {"is_authenticated": False, "pk": None})()
    return request


def test_rate_limit_allows_under_limit_then_blocks():
    calls = {"count": 0}

    @rate_limit("test", max_requests=2, window_seconds=60)
    def view(request):
        calls["count"] += 1
        return JsonResponse({"ok": True})

    request = _anon_request()
    assert view(request).status_code == 200
    assert view(request).status_code == 200
    blocked = view(request)
    assert blocked.status_code == 429
    assert blocked["Retry-After"] == "60"
    assert calls["count"] == 2  # third call never reached the view


class _FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


class _TtlCache:
    """A minimal cache that honours per-key TTL against a controllable clock,
    with incr() preserving the existing expiry the way real backends do -- enough
    to tell a fixed window (TTL set once) from a rolling one (TTL refreshed)."""

    def __init__(self, clock: _FakeClock) -> None:
        self._clock = clock
        self._store: dict[str, tuple[int, float]] = {}

    def _live_value(self, key):
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if self._clock.now >= expires_at:
            del self._store[key]
            return None
        return value

    def get(self, key, default=None):
        value = self._live_value(key)
        return default if value is None else value

    def set(self, key, value, timeout):
        self._store[key] = (value, self._clock.now + timeout)

    def add(self, key, value, timeout) -> bool:
        if self._live_value(key) is None:
            self._store[key] = (value, self._clock.now + timeout)
            return True
        return False

    def incr(self, key, delta: int = 1) -> int:
        value = self._live_value(key)
        if value is None:
            raise ValueError(f"'{key}' is not present or has expired")
        _old, expires_at = self._store[key]   # incr must NOT push the TTL forward
        self._store[key] = (value + delta, expires_at)
        return value + delta


def test_rate_limit_is_a_fixed_window_that_resets_not_a_rolling_one(monkeypatch):
    # #311: steady sub-limit traffic must not be throttled. With a rolling window
    # (TTL refreshed each request) the counter never expires while requests keep
    # coming, so it climbs to the cap and over-throttles. A fixed window anchored
    # on the first request expires on schedule and lets the count reset.
    clock = _FakeClock()
    fake_cache = _TtlCache(clock)
    import origami_common.decorators as decorators

    monkeypatch.setattr(decorators, "cache", fake_cache)

    @decorators.rate_limit("fixed", max_requests=3, window_seconds=10)
    def view(request):
        return JsonResponse({"ok": True})

    request = _anon_request()
    assert view(request).status_code == 200   # t=0,  count 1
    clock.advance(4)
    assert view(request).status_code == 200   # t=4,  count 2
    clock.advance(4)
    assert view(request).status_code == 200   # t=8,  count 3 (at the cap)
    clock.advance(3)
    # t=11: the window opened at t=0 has elapsed. A fixed window resets, so this is
    # allowed; a rolling window would still hold count 3 and wrongly return 429.
    assert view(request).status_code == 200


def test_json_error_and_permission_denied():
    err = _json_error("nope", status=418)
    assert err.status_code == 418
    assert json.loads(err.content) == {"error": "nope"}
    assert _permission_denied().status_code == 403


def test_parse_json_body_success_and_failure():
    request = HttpRequest()
    request._body = b'{"field": "value"}'
    data, error = _parse_json_body(request)
    assert error is None
    assert data == {"field": "value"}

    bad = HttpRequest()
    bad._body = b"not json"
    data, error = _parse_json_body(bad)
    assert data == {}
    assert error.status_code == 400

    not_object = HttpRequest()
    not_object._body = b"[1, 2, 3]"
    data, error = _parse_json_body(not_object)
    assert error.status_code == 400


def test_require_field():
    value, error = _require_field({"name": "x"}, "name")
    assert value == "x" and error is None

    value, error = _require_field({"name": "  "}, "name")
    assert value is None and error.status_code == 400

    value, error = _require_field({}, "name", "custom message")
    assert json.loads(error.content)["error"] == "custom message"


def test_active_page_mixin_injects_context():
    class Base:
        def get_context_data(self, **kwargs):
            return dict(kwargs)

    class View(ActivePageMixin, Base):
        active_page = "home"

    assert View().get_context_data()["active_page"] == "home"

    class NoActive(ActivePageMixin, Base):
        pass

    assert "active_page" not in NoActive().get_context_data()
