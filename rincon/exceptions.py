class RinconError(Exception):
    """Base exception for all Rincon errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RinconConnectionError(RinconError):
    """Raised when the client cannot connect to the Rincon server."""

    def __init__(self, message: str = "Failed to connect to Rincon server"):
        super().__init__(message)


class RinconAuthError(RinconError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class RinconNotFoundError(RinconError):
    """Raised when a requested resource is not found (404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class RinconValidationError(RinconError):
    """Raised when the server rejects a request due to invalid input (400)."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=400)


class RinconConflictError(RinconError):
    """Raised when a route registration conflicts with an existing route (500)."""

    def __init__(self, message: str = "Route conflict"):
        super().__init__(message, status_code=500)
