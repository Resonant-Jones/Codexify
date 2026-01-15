#!/usr/bin/env python3
"""Print FastAPI route inventory for the Guardian API."""

from fastapi.routing import APIRoute

from guardian.guardian_api import app


def _format_methods(methods: set[str]) -> str:
    cleaned = [m for m in methods if m not in {"HEAD", "OPTIONS"}]
    return ",".join(sorted(cleaned))


def main() -> None:
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(
                (
                    route.path,
                    _format_methods(route.methods or set()),
                    route.name,
                )
            )

    for path, methods, name in sorted(routes):
        print(f"{methods:12} {path} -> {name}")


if __name__ == "__main__":
    main()
