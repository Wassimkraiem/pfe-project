from http import HTTPStatus
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.response import ArErrorResponse

logger = logging.getLogger(__name__)

class AppError(Exception):
    default_message = "generic error"
    default_error_code = "generic_error"
    default_status_code = HTTPStatus.BAD_REQUEST

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
        details: dict | list | str | None = None,
    ):
        self.message = self.default_message if message is None else message
        self.error_code = self.default_error_code if error_code is None else error_code
        self.status_code = self.default_status_code if status_code is None else status_code
        self.details = details

    def to_dict(self) -> dict:
        payload = {
            "message": self.message,
            "error_code": self.error_code,
        }
        if self.details is not None:
            payload["details"] = self.details
        return payload

    def to_ar_response(self) -> ArErrorResponse:
        return ArErrorResponse(
            error_code=str(self.error_code),
            error_details=self.details,
            message=str(self.message),
            status_code=self.status_code,
        )


def setup_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return exc.to_ar_response()

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(_request: Request, exc: RequestValidationError):
        # Match your Flask behavior (400) instead of FastAPI default (422)
        return ArErrorResponse(
            error_code="validation_error",
            error_details=exc.errors(),
            message="validation_error",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        # Keep HTTP status but wrap the body
        return ArErrorResponse(
            error_code="http_error",
            error_details={"detail": exc.detail},
            message=str(exc.detail),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s %s", request.method, request.url)
        return ArErrorResponse(
            error_code="uncaught_error",
            error_details=str(exc),
            message="uncaught_error",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

class CantoAthenticationFailed(AppError):
    default_message = "Canto authentication failed"
    default_error_code = "canto_authentication_failed"
    default_status_code = HTTPStatus.UNAUTHORIZED