FROM python:3.12-slim

# TRAP 8: ffmpeg must be installed for silencedetect
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY . .

# TRAP 8: Railway assigns dynamic PORT
CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
