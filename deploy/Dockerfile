FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 VNIZER_DATA_ROOT=/data PATH="/app/.venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev
EXPOSE 8080
CMD ["vnizer", "serve", "--host", "0.0.0.0", "--port", "8080"]
