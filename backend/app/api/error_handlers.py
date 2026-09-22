import logging
from http import HTTPStatus
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.logging import reset_request_id, set_request_id
from app.schemas.errors import ErrorResponse

REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)


async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)

    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        reset_request_id(token)


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    logger.warning(
        "application_exception",
        extra={
            "request_id": get_request_id(request),
            "error_code": exc.code,
            "status_code": exc.status_code,
        },
    )
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=get_request_id(request),
    )


async def request_validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.info(
        "request_validation_error",
        extra={
            "request_id": get_request_id(request),
            "error_count": len(exc.errors()),
        },
    )
    return build_error_response(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="request_validation_error",
        message="The request body or parameters are invalid.",
        request_id=get_request_id(request),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = "The requested resource was not found."
    code = "not_found"
    if exc.status_code == HTTPStatus.METHOD_NOT_ALLOWED:
        message = "Method not allowed."
        code = "method_not_allowed"
    elif exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        message = "An internal server error occurred."
        code = "internal_error"

    logger.info(
        "http_exception",
        extra={
            "request_id": get_request_id(request),
            "status_code": exc.status_code,
        },
    )
    return build_error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        request_id=get_request_id(request),
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "unexpected_exception",
        extra={"request_id": get_request_id(request)},
    )
    return build_error_response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An internal server error occurred.",
        request_id=get_request_id(request),
    )


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    body = ErrorResponse(
        error={
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={REQUEST_ID_HEADER: request_id},
    )


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")
