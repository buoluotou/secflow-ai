FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (minimal, no toolchain retained) + CJK font for PDF reports
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Application code
COPY backend/app ./app
COPY risk ./risk
COPY reports ./reports
COPY integrations ./integrations
COPY ai ./ai

RUN mkdir -p /data /logs /reports

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
