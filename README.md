# rincon-py

[![PyPI](https://img.shields.io/pypi/v/rincon)](https://pypi.org/project/rincon/)
[![CI](https://github.com/BK1031/rincon-py/actions/workflows/test.yml/badge.svg)](https://github.com/BK1031/rincon-py/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

rincon-py is a client library for accessing the [Rincon](https://github.com/BK1031/Rincon) API.

## Getting Started

### Prerequisites

rincon-py requires [Python](https://www.python.org/) version 3.10 or above.

### Installing

Install from PyPI with pip:

```bash
pip install rincon
```

### Usage

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

## Contributing

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement". Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b gh-username/my-amazing-feature`)
3. Commit your Changes (`git commit -m 'Add my amazing feature'`)
4. Push to the Branch (`git push origin gh-username/my-amazing-feature`)
5. Open a Pull Request
