from datetime import datetime

from pydantic import BaseModel


class Service(BaseModel):
    id: int = 0
    name: str
    version: str
    endpoint: str
    health_check: str
    updated_at: datetime | None = None
    created_at: datetime | None = None


class Route(BaseModel):
    id: str = ""
    route: str
    method: str
    service_name: str
    created_at: datetime | None = None


class Ping(BaseModel):
    message: str
    services: int
    routes: int
