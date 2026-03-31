from http import HTTPStatus
from typing import Any

from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


class ArResponse(JSONResponse):
    """
    Flask-like success response envelope.

    Output:
      {
        "status_code": 200,
        "message": "success",
        "data": {...}   # optional
      }
    """

    def __init__(
        self,
        data: Any | None = None,
        message: str = "success",
        status_code: int | HTTPStatus = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        sc = int(status_code)
        payload: dict[str, Any] = {"status_code": sc, "message": message}
        if data is not None:
            payload["data"] = jsonable_encoder(data)
        super().__init__(content=payload, status_code=sc, headers=headers)


class ArErrorResponse(JSONResponse):
    """
    Flask-like error response envelope.

    Output:
      {
        "status_code": 400,
        "error_message": "failure",
        "error_code": "validation_error",
        "error_details": {...}  # optional
      }
    """

    def __init__(
        self,
        error_code: str,
        error_details: Any | None = None,
        message: str = "failure",
        status_code: int | HTTPStatus = HTTPStatus.BAD_REQUEST,
        headers: dict[str, str] | None = None,
    ) -> None:
        sc = int(status_code)
        payload: dict[str, Any] = {
            "status_code": sc,
            "error_message": message,
            "error_code": error_code,
        }
        if error_details is not None:
            payload["error_details"] = jsonable_encoder(error_details)
        super().__init__(content=payload, status_code=sc, headers=headers)


__all__ = ["ArResponse", "ArErrorResponse"]
