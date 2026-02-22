from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, error: str, detail: str, status: int) -> None:
        self.error = error
        self.detail = detail
        self.status = status
        super().__init__(detail)


def error_payload(error: str, detail: str, status: int) -> dict[str, str | int]:
    return {"error": error, "detail": detail, "status": status}


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status, content=error_payload(exc.error, exc.detail, exc.status)
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "VALIDATION_ERROR",
            "; ".join(str(item.get("msg", "invalid value")) for item in exc.errors()),
            422,
        ),
    )
