# rincon-py

Python client for the Rincon service registry.

## Install

```bash
pip install rincon
```

## Quick Start

```python
from rincon import RinconClient, Service, Route

client = RinconClient("http://localhost:8080")

service = Service(
    name="my-service",
    version="1.0.0",
    endpoint="http://localhost:5000",
    health_check="/health",
)

routes = [
    Route(route="/api/users", method="GET", service_name="my-service"),
    Route(route="/api/users", method="POST", service_name="my-service"),
]

try:
    client.register(service, routes)
    client.start_heartbeat(interval=10.0)

    matched = client.match_route("/api/users", "GET")
    print(matched.endpoint)
finally:
    client.deregister()
    client.close()
```

Or use the context manager:

```python
with RinconClient("http://localhost:8080") as client:
    client.register(service, routes)
    client.start_heartbeat()
    # ...
```

## API Reference

### Constructor

```python
RinconClient(url, auth_user="admin", auth_password="admin", timeout=10.0)
```

### Services

```python
client.get_all_services() -> list[Service]
client.get_services_by_name(name: str) -> list[Service]
client.get_service_by_id(service_id: int) -> Service
client.register_service(service: Service) -> Service
client.remove_service(service_id: int) -> None
```

### Routes

```python
client.get_all_routes() -> list[Route]
client.get_routes_for_service(service_name: str) -> list[Route]
client.get_route(route: str, *, method: str | None = None, service: str | None = None) -> Route
client.get_routes_by_path(route: str) -> list[Route]
client.register_route(route: Route) -> Route
```

### Matching

```python
client.match_route(route: str, method: str) -> Service
```

### High-Level Registration

```python
client.register(service: Service, routes: list[Route] | None = None) -> Service
client.deregister() -> None
```

### Heartbeat

```python
client.start_heartbeat(interval: float = 10.0) -> None
client.stop_heartbeat() -> None
```

### Ping

```python
client.ping() -> Ping
```
