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
