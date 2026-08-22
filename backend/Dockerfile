# Base image is configurable for offline/mirror-registry environments:
#   docker compose build --build-arg PY_IMAGE=docker.1ms.run/library/python:3.12-slim
# or via compose build.args (see docker-compose.yml PY_IMAGE variable)
ARG PY_IMAGE=python:3.12-slim
ARG PIP_INDEX_URL=https://pypi.org/simple
FROM ${PY_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (minimal, no toolchain retained) + CJK font for PDF reports
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python deps (index configurable via PIP_INDEX_URL — use a mirror when
# pypi.org is unreachable, e.g. https://pypi.tuna.tsinghua.edu.cn/simple)
COPY backend/pyproject.toml ./
RUN pip install --upgrade pip && pip install -i "${PIP_INDEX_URL}" .

# Application code
COPY backend/app ./app
COPY risk ./risk
COPY reports ./reports
COPY integrations ./integrations
COPY ai ./ai

RUN mkdir -p /data /logs /reports

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
