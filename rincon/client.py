from __future__ import annotations

import logging
import threading
import time

import httpx

from rincon.exceptions import (
    RinconAuthError,
    RinconConflictError,
    RinconConnectionError,
    RinconError,
    RinconNotFoundError,
    RinconValidationError,
)
from rincon.models import Ping, Route, Service

logger = logging.getLogger("rincon")


class RinconClient:
    """Client for interacting with a Rincon service registry server."""

    def __init__(
        self,
        url: str,
        auth_user: str = "admin",
        auth_password: str = "admin",
        timeout: float = 10.0,
    ):
        self._base_url = url.rstrip("/")
        self._auth = (auth_user, auth_password)
        self._client = httpx.Client(base_url=self._base_url, timeout=timeout)

        self._service: Service | None = None
        self._routes: list[Route] = []
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop_event = threading.Event()

    def close(self) -> None:
        self.stop_heartbeat()
        self._client.close()

    def __enter__(self) -> RinconClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ── HTTP helpers ──────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        auth: bool = False,
    ) -> httpx.Response:
        kwargs: dict = {"params": params}
        if json is not None:
            kwargs["json"] = json
        if auth:
            kwargs["auth"] = self._auth

        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.ConnectError as exc:
            raise RinconConnectionError(
                f"Failed to connect to Rincon at {self._base_url}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RinconConnectionError(
                f"Request to Rincon timed out: {path}"
            ) from exc

        self._raise_for_status(resp)
        return resp

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code == 200:
            return

        try:
            body = resp.json()
            message = body.get("message", resp.text)
        except Exception:
            message = resp.text

        match resp.status_code:
            case 401:
                raise RinconAuthError(message)
            case 400:
                raise RinconValidationError(message)
            case 404:
                raise RinconNotFoundError(message)
            case 500:
                raise RinconConflictError(message)
            case _:
                raise RinconError(message, status_code=resp.status_code)

    # ── Ping ──────────────────────────────────────────────────────────

    def ping(self) -> Ping:
        resp = self._request("GET", "/rincon/ping")
        return Ping.model_validate(resp.json())

    # ── Services ──────────────────────────────────────────────────────

    def get_all_services(self) -> list[Service]:
        resp = self._request("GET", "/rincon/services")
        return [Service.model_validate(s) for s in resp.json()]

    def get_services_by_name(self, name: str) -> list[Service]:
        resp = self._request("GET", f"/rincon/services/{name}")
        data = resp.json()
        if isinstance(data, list):
            return [Service.model_validate(s) for s in data]
        return [Service.model_validate(data)]

    def get_service_by_id(self, service_id: int) -> Service:
        resp = self._request("GET", f"/rincon/services/{service_id}")
        return Service.model_validate(resp.json())

    def register_service(self, service: Service) -> Service:
        resp = self._request(
            "POST",
            "/rincon/services",
            json=service.model_dump(exclude={"id", "updated_at", "created_at"}),
            auth=True,
        )
        return Service.model_validate(resp.json())

    def remove_service(self, service_id: int) -> None:
        self._request("DELETE", f"/rincon/services/{service_id}", auth=True)

    # ── Routes ────────────────────────────────────────────────────────

    def get_all_routes(self) -> list[Route]:
        resp = self._request("GET", "/rincon/routes")
        return [Route.model_validate(r) for r in resp.json()]

    def get_routes_for_service(self, service_name: str) -> list[Route]:
        resp = self._request("GET", f"/rincon/services/{service_name}/routes")
        return [Route.model_validate(r) for r in resp.json()]

    def get_route(
        self,
        route: str,
        *,
        method: str | None = None,
        service: str | None = None,
    ) -> Route:
        params: dict[str, str] = {"route": route}
        if method is not None:
            params["method"] = method
        if service is not None:
            params["service"] = service
        resp = self._request("GET", "/rincon/routes", params=params)
        data = resp.json()
        if isinstance(data, list):
            if len(data) == 0:
                raise RinconNotFoundError(f"No route {route} found")
            return Route.model_validate(data[0])
        return Route.model_validate(data)

    def get_routes_by_path(self, route: str) -> list[Route]:
        params = {"route": route}
        resp = self._request("GET", "/rincon/routes", params=params)
        data = resp.json()
        if isinstance(data, list):
            return [Route.model_validate(r) for r in data]
        return [Route.model_validate(data)]

    def register_route(self, route: Route) -> Route:
        resp = self._request(
            "POST",
            "/rincon/routes",
            json=route.model_dump(exclude={"id", "created_at"}),
            auth=True,
        )
        return Route.model_validate(resp.json())

    # ── Route matching ────────────────────────────────────────────────

    def match_route(self, route: str, method: str) -> Service:
        if route.startswith("/"):
            route = route[1:]
        resp = self._request(
            "GET",
            "/rincon/match",
            params={"route": route, "method": method},
        )
        return Service.model_validate(resp.json())

    # ── High-level registration ───────────────────────────────────────

    def register(self, service: Service, routes: list[Route] | None = None) -> Service:
        registered_service = self.register_service(service)
        self._service = registered_service

        self._routes = []
        for route in routes or []:
            route.service_name = registered_service.name
            registered_route = self.register_route(route)
            self._routes.append(registered_route)

        logger.info(
            "Registered service %s (%s) with %d route(s)",
            registered_service.name,
            registered_service.endpoint,
            len(self._routes),
        )
        return registered_service

    def deregister(self) -> None:
        if self._service is None:
            raise RinconError("No service registered with this client")
        self.stop_heartbeat()
        self.remove_service(self._service.id)
        logger.info("Deregistered service %s", self._service.name)
        self._service = None
        self._routes = []

    # ── Heartbeat ─────────────────────────────────────────────────────

    def start_heartbeat(self, interval: float = 10.0) -> None:
        if self._service is None:
            raise RinconError("No service registered with this client")
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_stop_event.clear()

        def _heartbeat_loop() -> None:
            while not self._heartbeat_stop_event.is_set():
                try:
                    self.register_service(self._service)  # type: ignore[arg-type]
                    logger.debug("Heartbeat sent for %s", self._service.name)  # type: ignore[union-attr]
                except Exception:
                    logger.warning("Heartbeat failed for %s", self._service.name, exc_info=True)  # type: ignore[union-attr]
                self._heartbeat_stop_event.wait(interval)

        self._heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            daemon=True,
            name="rincon-heartbeat",
        )
        self._heartbeat_thread.start()
        logger.info("Started heartbeat (interval=%.1fs)", interval)

    def stop_heartbeat(self) -> None:
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop_event.set()
        self._heartbeat_thread.join(timeout=5.0)
        self._heartbeat_thread = None
        logger.info("Stopped heartbeat")
