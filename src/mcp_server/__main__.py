"""Run rabbit-mcp over stdio: ``python -m src.mcp_server`` from the repo root,
or with PYTHONPATH set to it."""

from src.mcp_server.server import main

main()
