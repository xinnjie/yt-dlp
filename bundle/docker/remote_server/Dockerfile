# syntax=docker/dockerfile:1.6
ARG BUILDIMAGE=ghcr.io/yt-dlp/manylinux2014_x86_64-shared:latest
ARG RUNTIMEIMAGE=python:3.13-slim
ARG PYTHON_VERSION=3.13

FROM ${BUILDIMAGE} AS build

ARG PYTHON_VERSION
ARG PYTHON_BIN=/opt/shared-cpython-${PYTHON_VERSION}/bin/python${PYTHON_VERSION}
ENV VENV_PATH=/opt/yt-dlp-venv

WORKDIR /src
COPY . .

RUN set -euxo pipefail; \
    if command -v "${PYTHON_BIN}" >/dev/null 2>&1; then \
        PY_BIN="${PYTHON_BIN}"; \
    elif command -v "python${PYTHON_VERSION}" >/dev/null 2>&1; then \
        PY_BIN="python${PYTHON_VERSION}"; \
    else \
        PY_BIN="python3"; \
    fi; \
    "${PY_BIN}" -m venv "${VENV_PATH}"; \
    . "${VENV_PATH}/bin/activate"; \
    python -m ensurepip --upgrade; \
    pip install --upgrade pip setuptools wheel; \
    pip install --no-cache-dir '.[remote]'; \
    pip check

FROM ${RUNTIMEIMAGE} AS runtime

ENV VENV_PATH=/opt/yt-dlp-venv \
    PATH=/opt/yt-dlp-venv/bin:${PATH} \
    PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1

COPY --from=build ${VENV_PATH} ${VENV_PATH}

WORKDIR /srv/yt-dlp
EXPOSE 50051

ENTRYPOINT ["/opt/yt-dlp-venv/bin/python3", "-m", "yt_dlp.remote.server"]
CMD ["--port", "50051"]
