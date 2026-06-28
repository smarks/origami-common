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

            # Get current count
            current = cache.get(cache_key, 0)

            if current >= max_requests:
                response = JsonResponse(
                    {
                        "error": "Rate limit exceeded. Please try again later.",
                        "retry_after": window_seconds,
                    },
                    status=429,
                )
                response["Retry-After"] = str(window_seconds)
                return response

            # Increment counter
            cache.set(cache_key, current + 1, window_seconds)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
