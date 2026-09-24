"""
Application-specific exceptions and global error handling.

Business logic raises these exceptions. The global handler in main.py
converts them to user-friendly HTTP responses while logging technical details.
"""


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | None = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(message=detail, code="NOT_FOUND")


class ValidationError(AppError):
    """Input validation failed."""

    def __init__(self, message: str):
        super().__init__(message=message, code="VALIDATION_ERROR")


class AuthenticationError(AppError):
    """Authentication failed."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthorizationError(AppError):
    """User lacks permission."""

    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message=message, code="AUTHORIZATION_ERROR")


class ConflictError(AppError):
    """Resource already exists or state conflict."""

    def __init__(self, message: str):
        super().__init__(message=message, code="CONFLICT")


class ProcessingError(AppError):
    """Error during video/analysis processing."""

    def __init__(self, message: str):
        super().__init__(message=message, code="PROCESSING_ERROR")
