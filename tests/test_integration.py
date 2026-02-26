"""Integration tests against a live Rincon server.

Requires a Rincon instance running at http://localhost:10311
with default credentials (admin/admin).

Run with: pytest tests/test_integration.py -v
"""

import time

import pytest

from rincon import (
    RinconAuthError,
    RinconClient,
    RinconError,
    RinconNotFoundError,
)
from rincon.models import Route, Service

RINCON_URL = "http://localhost:10311"


@pytest.fixture
def client():
    with RinconClient(url=RINCON_URL) as c:
        yield c
        if c.is_registered:
            c.stop_heartbeat()
            try:
                c.deregister()
            except Exception:
                pass


class TestPingIntegration:
    def test_ping(self, client: RinconClient):
        ping = client.ping()
        assert "Rincon" in ping.message
        assert ping.services >= 1
        assert ping.routes >= 0


class TestServiceLifecycle:
    def test_register_and_get_service(self, client: RinconClient):
        svc = Service(
            name="Integration Test",
            version="1.0.0",
            endpoint="http://localhost:9999",
            health_check="http://localhost:9999/health",
        )
        registered = client.register_service(svc)

        assert registered.id > 0
        assert registered.name == "integration_test"
        assert registered.version == "1.0.0"
        assert registered.endpoint == "http://localhost:9999"
        assert registered.created_at is not None

        fetched = client.get_service_by_id(registered.id)
        assert fetched.id == registered.id
        assert fetched.name == registered.name

        by_name = client.get_services_by_name("integration_test")
        assert any(s.id == registered.id for s in by_name)

        client.remove_service(registered.id)

    def test_get_all_services_includes_rincon(self, client: RinconClient):
        services = client.get_all_services()
        assert len(services) >= 1
        names = [s.name for s in services]
        assert "rincon" in names

    def test_remove_service(self, client: RinconClient):
        svc = Service(
            name="To Remove",
            version="1.0.0",
            endpoint="http://localhost:9998",
            health_check="http://localhost:9998/health",
        )
        registered = client.register_service(svc)
        client.remove_service(registered.id)

        with pytest.raises(RinconNotFoundError):
            client.get_service_by_id(registered.id)

    def test_register_same_endpoint_updates(self, client: RinconClient):
        svc = Service(
            name="Updatable",
            version="1.0.0",
            endpoint="http://localhost:9997",
            health_check="http://localhost:9997/health",
        )
        first = client.register_service(svc)

        svc.version = "2.0.0"
        second = client.register_service(svc)

        assert second.id == first.id
        assert second.version == "2.0.0"

        client.remove_service(first.id)

    def test_service_not_found(self, client: RinconClient):
        with pytest.raises(RinconNotFoundError):
            client.get_service_by_id(999999)


class TestRouteLifecycle:
    def test_register_and_get_routes(self, client: RinconClient):
        svc = Service(
            name="Route Test Svc",
            version="1.0.0",
            endpoint="http://localhost:9996",
            health_check="http://localhost:9996/health",
        )
        registered = client.register_service(svc)

        route = Route(
            route="/api/widgets",
            method="GET",
            service_name=registered.name,
        )
        created_route = client.register_route(route)
        assert created_route.route == "/api/widgets"
        assert created_route.service_name == registered.name

        all_routes = client.get_all_routes()
        assert any(r.route == "/api/widgets" for r in all_routes)

        service_routes = client.get_routes_for_service(registered.name)
        assert any(r.route == "/api/widgets" for r in service_routes)

        client.remove_service(registered.id)

    def test_route_method_stacking(self, client: RinconClient):
        svc = Service(
            name="Stack Test",
            version="1.0.0",
            endpoint="http://localhost:9995",
            health_check="http://localhost:9995/health",
        )
        registered = client.register_service(svc)

        route_get = Route(
            route="/api/items",
            method="GET",
            service_name=registered.name,
        )
        client.register_route(route_get)

        route_post = Route(
            route="/api/items",
            method="POST",
            service_name=registered.name,
        )
        stacked = client.register_route(route_post)
        assert "GET" in stacked.method
        assert "POST" in stacked.method

        client.remove_service(registered.id)


class TestRouteMatching:
    def test_match_route(self, client: RinconClient):
        svc = Service(
            name="Match Test",
            version="1.0.0",
            endpoint="http://localhost:9994",
            health_check="http://localhost:9994/health",
        )
        registered = client.register_service(svc)

        route = Route(
            route="/api/match/test",
            method="GET",
            service_name=registered.name,
        )
        client.register_route(route)

        matched = client.match_route("/api/match/test", "GET")
        assert matched.name == registered.name
        assert matched.endpoint == "http://localhost:9994"

        client.remove_service(registered.id)

    def test_match_route_not_found(self, client: RinconClient):
        with pytest.raises(RinconNotFoundError):
            client.match_route("/nonexistent/path/xyz", "GET")


class TestHighLevelAPI:
    def test_register_and_deregister(self, client: RinconClient):
        svc = Service(
            name="High Level Test",
            version="1.0.0",
            endpoint="http://localhost:9993",
            health_check="http://localhost:9993/health",
        )
        routes = [
            Route(route="/api/hl/a", method="GET", service_name=""),
            Route(route="/api/hl/b", method="POST", service_name=""),
        ]
        result = client.register(svc, routes=routes)

        assert client.is_registered
        assert client.service is not None
        assert client.service.id == result.id
        assert len(client.routes) == 2

        matched = client.match_route("/api/hl/a", "GET")
        assert matched.name == result.name

        client.deregister()
        assert not client.is_registered
        assert client.service is None
        assert client.routes == []

    def test_deregister_without_register_raises(self, client: RinconClient):
        with pytest.raises(RinconError, match="No service registered"):
            client.deregister()


class TestHeartbeat:
    def test_heartbeat_sends_registration(self, client: RinconClient):
        svc = Service(
            name="Heartbeat Test",
            version="1.0.0",
            endpoint="http://localhost:9992",
            health_check="http://localhost:9992/health",
        )
        client.register(svc)
        first_update = client.service.updated_at

        client.start_heartbeat(interval=1.0)
        time.sleep(2.5)
        client.stop_heartbeat()

        refreshed = client.get_service_by_id(client.service.id)
        assert refreshed.updated_at > first_update


class TestAuthErrors:
    def test_bad_credentials(self):
        with RinconClient(
            url=RINCON_URL, auth_user="wrong", auth_password="creds"
        ) as client:
            svc = Service(
                name="Auth Fail",
                version="1.0.0",
                endpoint="http://localhost:9991",
                health_check="http://localhost:9991/health",
            )
            with pytest.raises(RinconAuthError):
                client.register_service(svc)

    def test_reads_do_not_require_auth(self):
        with RinconClient(
            url=RINCON_URL, auth_user="wrong", auth_password="creds"
        ) as client:
            ping = client.ping()
            assert "Rincon" in ping.message

            services = client.get_all_services()
            assert len(services) >= 1
