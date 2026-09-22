from http import HTTPStatus


class AppException(Exception):
    """Base class for safe, client-facing application errors."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    message: str = "An internal server error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        super().__init__(self.message)


class AuthenticationError(AppException):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "authentication_required"
    message = "Authentication is required."


class AuthorizationError(AppException):
    status_code = HTTPStatus.FORBIDDEN
    code = "authorization_error"
    message = "You do not have permission to perform this action."


class ValidationError(AppException):
    status_code = HTTPStatus.BAD_REQUEST
    code = "validation_error"
    message = "The request is invalid."


class ResourceNotFoundError(AppException):
    status_code = HTTPStatus.NOT_FOUND
    code = "resource_not_found"
    message = "The requested resource was not found."


class InternalApplicationError(AppException):
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    code = "internal_error"
    message = "An internal server error occurred."


class IntegrationConfigurationError(InternalApplicationError):
    code = "integration_configuration_error"
    message = "An integration is not configured correctly."


class IntegrationUnavailableError(InternalApplicationError):
    code = "integration_unavailable"
    message = "An integration is temporarily unavailable."
