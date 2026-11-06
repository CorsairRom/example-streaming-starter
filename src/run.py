from __future__ import annotations

import argparse

import uvicorn

from app.settings import get_settings

APP_DIR = "src"
APP_TARGET = "app.main:app"


def main() -> None:
    """Start the API using HOST and PORT from the environment or `.env`."""
    parser = argparse.ArgumentParser(description="Run the example streaming starter.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Restart the server when a source file changes (development only).",
    )
    args = parser.parse_args()

    settings = get_settings()
    uvicorn.run(
        APP_TARGET,
        host=settings.host,
        port=settings.port,
        reload=args.reload,
        app_dir=APP_DIR,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    main()
