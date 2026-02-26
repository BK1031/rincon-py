# rincon-py

Python client library for [Rincon](https://github.com/BK1031/Rincon), a lightweight, cloud-native service registry.

## Installation

```bash
pip install rincon
```

## Quick Start

```python
from rincon import RinconClient, Service, Route

client = RinconClient("http://localhost:10311")

# Register a service with routes
service = Service(
    name="my-service",
    version="1.0.0",
    endpoint="http://localhost:5000",
    health_check="http://localhost:5000/health",
)
routes = [
    Route(route="/api/users", method="GET", service_name=""),
    Route(route="/api/users", method="POST", service_name=""),
]
client.register(service, routes)

# Start client heartbeat to keep registration alive
client.start_heartbeat(interval=10.0)

# Discover services by route
matched = client.match_route("/api/users", "GET")
print(f"{matched.name} @ {matched.endpoint}")

# Cleanup
client.deregister()
client.close()
```

The client also supports context managers for automatic cleanup:

```python
with RinconClient("http://localhost:10311") as client:
    client.register(service, routes)
    client.start_heartbeat()
    # ...
```

## API Reference

### Client

```python
RinconClient(url, auth_user="admin", auth_password="admin", timeout=10.0)

client.service      -> Service | None   # Currently registered service
client.routes       -> list[Route]      # Currently registered routes
client.is_registered -> bool
```

### Services

```python
client.ping() -> Ping
client.get_all_services() -> list[Service]
client.get_services_by_name(name) -> list[Service]
client.get_service_by_id(service_id) -> Service
client.register_service(service) -> Service
client.remove_service(service_id) -> None
```

### Routes

```python
client.get_all_routes() -> list[Route]
client.get_routes_for_service(service_name) -> list[Route]
client.get_route(route, *, method=None, service=None) -> Route
client.get_routes_by_path(route) -> list[Route]
client.register_route(route) -> Route
```

### Matching

```python
client.match_route(route, method) -> Service
```

### Registration & Heartbeat

```python
client.register(service, routes=None) -> Service
client.deregister() -> None
client.start_heartbeat(interval=10.0) -> None
client.stop_heartbeat() -> None
```
