import logging

# Audit logger for privileged/admin actions across Tarmar apps. Consuming
# projects can route this by configuring a handler for the "origami.audit"
# logger name in their LOGGING settings.
audit_logger = logging.getLogger("origami.audit")
