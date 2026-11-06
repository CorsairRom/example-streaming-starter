from __future__ import annotations


class AppError(Exception):
    """Base class for every expected error. Each subclass maps to an HTTP response."""

    status_code: int = 400
    code: str = "APP_ERROR"
    default_message: str = "Unexpected error."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, object]] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or []
        super().__init__(self.message)


class StreamApiKeyMissingError(AppError):
    status_code = 401
    code = "STREAM_API_KEY_MISSING"
    default_message = "The X-API-Key header is required."


class StreamApiKeyInvalidError(AppError):
    status_code = 401
    code = "STREAM_API_KEY_INVALID"
    default_message = "The API key is unknown or revoked."


class StreamPayloadInvalidError(AppError):
    status_code = 422
    code = "STREAM_PAYLOAD_INVALID"
    default_message = "The event payload does not match the documented contract."


class ApiKeyNotFoundError(AppError):
    status_code = 404
    code = "API_KEY_NOT_FOUND"
    default_message = "The API key does not exist."


class ApiKeyAlreadyRevokedError(AppError):
    status_code = 409
    code = "API_KEY_ALREADY_REVOKED"
    default_message = "The API key was already revoked."


class AdminCredentialsInvalidError(AppError):
    status_code = 401
    code = "ADMIN_INVALID_CREDENTIALS"
    default_message = "Invalid username or password."


class CsrfTokenInvalidError(AppError):
    status_code = 403
    code = "ADMIN_CSRF_TOKEN_INVALID"
    default_message = "The form token is missing or expired. Reload the page and try again."
