from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse


def rate_limit(key_prefix: str, max_requests: int = 30, window_seconds: int = 60):
    """
    Rate limit decorator for views.

    Uses Django's cache to track request counts per user/IP.
    Returns 429 Too Many Requests if limit exceeded.

    Args:
        key_prefix: String prefix for cache key (e.g., "ajax_profile")
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Build cache key from user ID or IP
            if request.user.is_authenticated:
                identifier = f"user_{request.user.pk}"
            else:
                identifier = f"ip_{request.META.get('REMOTE_ADDR', 'unknown')}"

            cache_key = f"rate_limit:{key_prefix}:{identifier}"

            # Anchor the window on the FIRST request of the window: add() seeds the
            # counter at 0 with the window TTL only when the key is absent, and
            # incr() bumps the count while leaving that original TTL untouched. So
            # the window is a true fixed window that resets cleanly when it elapses
            # -- not the rolling window the old cache.set(..., window_seconds) made
            # by pushing a fresh TTL forward on every request, which never expired
            # under steady traffic and over-throttled sub-limit callers (#311).
            cache.add(cache_key, 0, window_seconds)
            current = cache.incr(cache_key)

            if current > max_requests:
                response = JsonResponse(
                    {
                        "error": "Rate limit exceeded. Please try again later.",
                        "retry_after": window_seconds,
                    },
                    status=429,
                )
                response["Retry-After"] = str(window_seconds)
                return response

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
