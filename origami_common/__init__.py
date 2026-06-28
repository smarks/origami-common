"""origami-common — domain-agnostic Django web utilities shared across projects.

Deliberately knows nothing about the user model or any project domain: it
provides framework-level building blocks (a cache-backed rate-limit decorator,
an audit logger, JSON response helpers, and a context-injecting view mixin) that
``origami-auth`` and the consuming apps build on. Anything that reaches into the
user model or roles lives in ``origami-auth``, not here.
"""
