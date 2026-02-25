import pytest
from pytest_httpx import HTTPXMock

from rincon import (
    RinconAuthError,
    RinconClient,
    RinconConflictError,
    RinconError,
    RinconNotFoundError,
    RinconValidationError,
)
from rincon.models import Route, Service
from tests.conftest import SAMPLE_PING, SAMPLE_ROUTE, SAMPLE_SERVICE


class TestPing:
    def test_ping(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/ping", json=SAMPLE_PING
        )
        ping = client.ping()
        assert ping.message == "Rincon v2.2.0 is online!"
        assert ping.services == 2
        assert ping.routes == 6


class TestGetServices:
    def test_get_all_services(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services",
            json=[SAMPLE_SERVICE],
        )
        services = client.get_all_services()
        assert len(services) == 1
        assert services[0].name == "service_a"

    def test_get_services_by_name(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services/service_a",
            json=[SAMPLE_SERVICE],
        )
        services = client.get_services_by_name("service_a")
        assert len(services) == 1

    def test_get_service_by_id(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services/820522",
            json=SAMPLE_SERVICE,
        )
        svc = client.get_service_by_id(820522)
        assert svc.id == 820522
        assert svc.name == "service_a"

    def test_get_service_not_found(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services/999999",
            status_code=404,
            json={"message": "No service with id 999999 found"},
        )
        with pytest.raises(
            RinconNotFoundError, match="No service with id 999999 found"
        ):
            client.get_service_by_id(999999)


class TestRegisterService:
    def test_register_service(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services",
            method="POST",
            json=SAMPLE_SERVICE,
        )
        svc = Service(
            name="Service A",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        result = client.register_service(svc)
        assert result.id == 820522
        assert result.name == "service_a"

    def test_register_service_auth_failure(
        self, client: RinconClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services",
            method="POST",
            status_code=401,
            json={"message": "Invalid credentials"},
        )
        svc = Service(
            name="test",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        with pytest.raises(RinconAuthError, match="Invalid credentials"):
            client.register_service(svc)

    def test_register_service_validation_error(
        self, client: RinconClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services",
            method="POST",
            status_code=400,
            json={"message": "Service name is required"},
        )
        svc = Service(
            name="",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        with pytest.raises(RinconValidationError, match="Service name is required"):
            client.register_service(svc)


class TestRemoveService:
    def test_remove_service(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services/820522",
            method="DELETE",
            json={"message": "Service with id 820522 removed"},
        )
        client.remove_service(820522)


class TestRoutes:
    def test_get_all_routes(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/routes",
            json=[SAMPLE_ROUTE],
        )
        routes = client.get_all_routes()
        assert len(routes) == 1
        assert routes[0].route == "/users"

    def test_get_routes_for_service(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services/service_a/routes",
            json=[SAMPLE_ROUTE],
        )
        routes = client.get_routes_for_service("service_a")
        assert len(routes) == 1

    def test_register_route(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/routes",
            method="POST",
            json=SAMPLE_ROUTE,
        )
        route = Route(route="/users", method="GET,POST", service_name="service_a")
        result = client.register_route(route)
        assert result.id == "/users-[GET,POST]"


class TestMatchRoute:
    def test_match_route(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(json=SAMPLE_SERVICE)
        svc = client.match_route("/users", "GET")
        assert svc.name == "service_a"
        assert svc.endpoint == "http://localhost:8080"

    def test_match_route_strips_leading_slash(
        self, client: RinconClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(json=SAMPLE_SERVICE)
        client.match_route("/users/123", "GET")
        request = httpx_mock.get_requests()[0]
        assert "route=users%2F123" in str(request.url) or "route=users/123" in str(
            request.url
        )

    def test_match_route_not_found(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            status_code=404,
            json={"message": "No route [GET] /nonexistent found"},
        )
        with pytest.raises(RinconNotFoundError):
            client.match_route("/nonexistent", "GET")


class TestHighLevelRegistration:
    def test_register_with_routes(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services",
            method="POST",
            json=SAMPLE_SERVICE,
        )
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/routes",
            method="POST",
            json=SAMPLE_ROUTE,
        )
        svc = Service(
            name="Service A",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        route = Route(route="/users", method="GET,POST", service_name="")
        result = client.register(svc, routes=[route])
        assert result.id == 820522
        assert client.is_registered
        assert client.service is not None
        assert client.service.name == "service_a"
        assert len(client.routes) == 1

    def test_deregister(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services",
            method="POST",
            json=SAMPLE_SERVICE,
        )
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services/820522",
            method="DELETE",
            json={"message": "Service with id 820522 removed"},
        )
        svc = Service(
            name="Service A",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        client.register(svc)
        client.deregister()
        assert not client.is_registered
        assert client.service is None
        assert client.routes == []

    def test_deregister_without_registration_raises(self, client: RinconClient):
        with pytest.raises(RinconError, match="No service registered"):
            client.deregister()


class TestProperties:
    def test_initial_state(self, client: RinconClient):
        assert client.service is None
        assert client.routes == []
        assert not client.is_registered

    def test_routes_returns_copy(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/services",
            method="POST",
            json=SAMPLE_SERVICE,
        )
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/routes",
            method="POST",
            json=SAMPLE_ROUTE,
        )
        svc = Service(
            name="Service A",
            version="1.0.0",
            endpoint="http://localhost:8080",
            health_check="http://localhost:8080/health",
        )
        route = Route(route="/users", method="GET,POST", service_name="")
        client.register(svc, routes=[route])
        routes = client.routes
        routes.clear()
        assert len(client.routes) == 1


class TestErrorHandling:
    def test_conflict_error(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/routes",
            method="POST",
            status_code=500,
            json={"message": "route overlaps with existing routes"},
        )
        route = Route(route="/users", method="GET", service_name="service_a")
        with pytest.raises(RinconConflictError, match="overlaps"):
            client.register_route(route)

    def test_unknown_status_code(self, client: RinconClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://localhost:10311/rincon/ping",
            status_code=503,
            json={"message": "Service unavailable"},
        )
        with pytest.raises(RinconError) as exc_info:
            client.ping()
        assert exc_info.value.status_code == 503

    def test_heartbeat_without_registration_raises(self, client: RinconClient):
        with pytest.raises(RinconError, match="No service registered"):
            client.start_heartbeat()
