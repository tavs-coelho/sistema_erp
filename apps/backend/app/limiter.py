"""Shared rate-limiter instance.

Imported by both app.main (to register the exception handler and attach it to
app.state) and app.routers.auth (to decorate the login endpoint).  Using a
single instance ensures that in-memory counters are shared across the
application and that swapping to a Redis backend only requires a change here.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
