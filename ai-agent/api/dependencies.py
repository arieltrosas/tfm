from typing import Annotated

from fastapi import Depends, Request

from core.services import AppServices


def get_services(request: Request) -> AppServices:
    return request.app.state.services


ServicesDep = Annotated[AppServices, Depends(get_services)]
