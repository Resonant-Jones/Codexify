import argparse
import os

import uvicorn

CANONICAL_ASGI_APP = "guardian.guardian_api:app"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Guardian FastAPI server"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("GUARDIAN_API_HOST", "127.0.0.1"),
        help="Bind host",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("GUARDIAN_API_PORT", "8000")),
        help="Bind port",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("GUARDIAN_API_RELOAD", "0") in ("1", "true", "True"),
        help="Enable auto-reload",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("GUARDIAN_API_WORKERS", "1")),
        help="Number of worker processes",
    )
    args = parser.parse_args()

    uvicorn.run(
        CANONICAL_ASGI_APP,
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
