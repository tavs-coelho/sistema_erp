"""Shared pytest configuration for the ERP backend test suite.

Sets LOGIN_RATE_LIMIT to a very high value so the rate-limiter does not
interfere with test helper logins. The test_sprint_aderencia module
overrides this to "10/minute" at module level to test the 429 behaviour.
"""

import os

# Keep tests fast — disable effective rate-limiting for all modules
# that do NOT specifically test the rate-limiting behaviour.
# test_sprint_aderencia.py tests the 429 path explicitly using its own
# isolated username ("x_ratelimit") to avoid polluting the default limit.
os.environ.setdefault("LOGIN_RATE_LIMIT", "10000/minute")
