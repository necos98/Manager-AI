"""Custom exception hierarchy for Manager AI services."""


class AppError(Exception):
    """Base for all application errors."""
    status_code: int = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""
    status_code = 404


class InvalidTransitionError(AppError):
    """Invalid state transition attempted."""
    status_code = 409


class ValidationError(AppError):
    """Input validation failed."""
    status_code = 422
