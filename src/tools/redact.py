"""
Redaction guard for a PUBLIC-facing agent.

The knowledge base (Confluence pages, file descriptions) contains internal
infrastructure details — host IPs, DB usernames, connection strings, employee
emails. This module scrubs those before tool results reach the LLM context or
the user, so the agent cannot leak internal infra even if prompted to.
"""

import re

# INTERNAL/private IPv4 only (10.x, 172.16-31.x, 192.168.x). Restricted to private
# ranges so version strings / metrics like "spark 3.1.2.0" are NOT false-matched.
_IPV4 = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3})\b"
)
# Email addresses (employee PII).
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Explicit DB credential keys only (database.user/password, db_user/password) —
# narrow so ordinary prose mentioning "password" is not mangled.
_DB_CRED = re.compile(
    r"(?i)\b(database\.user|database\.password|db_user|db_password)\s*[:=]\s*\S+"
)

_IP_TOKEN = "<redacted-ip>"
_EMAIL_TOKEN = "<redacted-email>"
_CRED_TOKEN = r"\1: <redacted>"


def redact(value):
    """Recursively redact IPs, emails and DB credentials from strings / dicts / lists."""
    if isinstance(value, str):
        v = _DB_CRED.sub(_CRED_TOKEN, value)
        v = _IPV4.sub(_IP_TOKEN, v)
        v = _EMAIL.sub(_EMAIL_TOKEN, v)
        return v
    if isinstance(value, dict):
        return {k: redact(x) for k, x in value.items()}
    if isinstance(value, list):
        return [redact(x) for x in value]
    return value
