# origami-common

Domain-agnostic Django web utilities shared across Tarmar projects. Knows nothing
about the user model or any project domain — that lives in
[`origami-auth`](https://github.com/smarks/origami-auth) and the apps themselves.

Provides:
- `origami_common.decorators.rate_limit` — a cache-backed per-user/IP rate-limit decorator (returns 429).
- `origami_common.audit.audit_logger` — a `logging.getLogger("origami.audit")` for privileged actions.
- `origami_common.helpers` — `_json_error`, `_permission_denied`, `_parse_json_body`, `_require_field`.
- `origami_common.mixins.ActivePageMixin` — injects `active_page` into template context.

## Use it

```python
from origami_common.decorators import rate_limit
from origami_common.audit import audit_logger
from origami_common.helpers import _json_error, _parse_json_body, _permission_denied
from origami_common.mixins import ActivePageMixin
```

Route the audit log by configuring a handler for the `origami.audit` logger name
in your project's `LOGGING` settings.

## Develop

```bash
pip install -e '.[test]'
pytest
```
