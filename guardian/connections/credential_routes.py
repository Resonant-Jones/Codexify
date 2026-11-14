"""Never return Pydantic's credential-bearing input on setup validation errors."""

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute


class CredentialSetupRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def sanitized(request):
            try:
                return await original(request)
            except RequestValidationError:
                raise HTTPException(
                    422, detail={"error": "connection_setup_invalid"}
                ) from None

        return sanitized
