#!/bin/bash
# Start the FastAPI backend server for Paper2Code-Enhanced on port 8099
uv run uvicorn codes.server:app --host 127.0.0.1 --port 8099
