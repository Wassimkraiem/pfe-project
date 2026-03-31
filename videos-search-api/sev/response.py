import json
from http import HTTPStatus
from flask import Response
from decimal import Decimal
from conf.utils import convert_decimals


class SevResponse(Response):
    def __init__(
        self, data=None, message="success", status_code=HTTPStatus.OK, headers=None
    ) -> None:
        # Convert decimals in data before passing it to the response
        if data:
            data = convert_decimals(data)  # Ensure decimals are converted to float

        payload = {"status_code": status_code, "message": message}
        if data:
            payload["data"] = data

        super().__init__(
            response=json.dumps(payload),
            status=status_code,
            headers=headers,
            mimetype="application/json",
            content_type="application/json",
        )


class SevErrorResponse(Response):
    def __init__(
        self,
        error_code,
        error_details=None,
        message="failure",
        status_code=HTTPStatus.BAD_REQUEST,
        headers=None,
    ) -> None:
        payload = {
            "status_code": status_code,
            "error_message": message,
            "error_code": error_code,
        }
        if error_details:
            payload["error_code"] = error_details
            payload["error_details"] = error_code
        super().__init__(
            response=json.dumps(payload),
            status=status_code,
            headers=headers,
            mimetype="application/json",
            content_type="application/json",
        )
