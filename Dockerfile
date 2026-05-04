FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /tmp/build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY ./pyproject.toml .
COPY ./README.md .
COPY ./LICENSE .
COPY ./src ./src

RUN /bin/uv pip install --no-cache /tmp/build

FROM python:3.13-slim AS final

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN groupadd --system app \
    && useradd --system --gid app app \
    && chown -R app:app /app

USER app

ENTRYPOINT [ "crosstab" ]
