"""Entry point: starts FastAPI on port 3100.

Usage: python -m resume_graph.main
"""

import uvicorn

from resume_graph.config import settings


def main() -> None:
    uvicorn.run(
        "resume_graph.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
