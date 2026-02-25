from rincon.models import Ping, Route, Service


class TestServiceModel:
    def test_from_dict(self):
        data = {
            "id": 820522,
            "name": "service_a",
            "version": "1.0.0",
            "endpoint": "http://localhost:8080",
            "health_check": "http://localhost:8080/health",
            "updated_at": "2024-08-04T19:32:40.109239-07:00",
            "created_at": "2024-08-04T19:32:40.109239-07:00",
        }
        svc = Service.model_validate(data)
        assert svc.id == 820522
        assert svc.name == "service_a"
        assert svc.version == "1.0.0"
        assert svc.endpoint == "http://localhost:8080"
        assert svc.health_check == "http://localhost:8080/health"
        assert svc.updated_at is not None
        assert svc.created_at is not None

    def test_minimal_construction(self):
        svc = Service(
            name="my_service",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        assert svc.id == 0
        assert svc.name == "my_service"
        assert svc.updated_at is None

    def test_serialization_excludes_defaults(self):
        svc = Service(
            name="test",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        data = svc.model_dump(exclude={"id", "updated_at", "created_at"})
        assert "id" not in data
        assert "updated_at" not in data
        assert data["name"] == "test"


class TestRouteModel:
    def test_from_dict(self):
        data = {
            "id": "/users-[GET,POST]",
            "route": "/users",
            "method": "GET,POST",
            "service_name": "service_a",
            "created_at": "2024-08-04T19:32:40.109239-07:00",
        }
        route = Route.model_validate(data)
        assert route.id == "/users-[GET,POST]"
        assert route.route == "/users"
        assert route.method == "GET,POST"
        assert route.service_name == "service_a"

    def test_minimal_construction(self):
        route = Route(route="/users", method="GET", service_name="test")
        assert route.id == ""
        assert route.created_at is None


class TestPingModel:
    def test_from_dict(self):
        data = {
            "message": "Rincon v2.2.0 is online!",
            "services": 2,
            "routes": 6,
        }
        ping = Ping.model_validate(data)
        assert ping.message == "Rincon v2.2.0 is online!"
        assert ping.services == 2
        assert ping.routes == 6
