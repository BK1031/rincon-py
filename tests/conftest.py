import pytest

from rincon import RinconClient


@pytest.fixture
def client():
    with RinconClient(url="http://localhost:10311") as c:
        yield c


SAMPLE_SERVICE = {
    "id": 820522,
    "name": "service_a",
    "version": "1.0.0",
    "endpoint": "http://localhost:8080",
    "health_check": "http://localhost:8080/health",
    "updated_at": "2024-08-04T19:32:40.109239344-07:00",
    "created_at": "2024-08-04T19:32:40.109239386-07:00",
}

SAMPLE_ROUTE = {
    "id": "/users-[GET,POST]",
    "route": "/users",
    "method": "GET,POST",
    "service_name": "service_a",
    "created_at": "2024-08-04T19:32:40.109239344-07:00",
}

SAMPLE_PING = {
    "message": "Rincon v2.2.0 is online!",
    "services": 2,
    "routes": 6,
}
