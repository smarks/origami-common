import json

from django.http import JsonResponse


def _json_error(message, status=400):
    """Return a JSON error response."""
    return JsonResponse({"error": message}, status=status)


def _permission_denied():
    """Return a permission denied JSON response."""
    return _json_error("Permission denied", status=403)


def _parse_json_body(request) -> tuple[dict, JsonResponse | None]:
    """Parse a JSON object request body.

    Returns ``(data, None)`` on success or ``({}, error_response)`` on failure —
    an empty dict rather than None on error, so callers (which always check the
    error first) get a non-Optional ``data`` for type-checking.
    """
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return {}, _json_error("Invalid JSON")
        return data, None
    except json.JSONDecodeError:
        return {}, _json_error("Invalid JSON")


def _require_field(data: dict, field_name: str, error_msg: str | None = None):
    """Get required field from data. Returns (value, error_response) tuple."""
    value = data.get(field_name)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, _json_error(error_msg or f"{field_name} is required")
    return value, None
