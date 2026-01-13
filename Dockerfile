# CLI-first image for OpenChronicle v2
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OC_DB_PATH=/data/openchronicle.db \
    OC_CONFIG_DIR=/config \
    OC_PLUGIN_DIR=/plugins

WORKDIR /app

# Copy project
COPY pyproject.toml README.md ./
COPY src ./src
COPY plugins ./plugins

# Install core
RUN pip install --no-cache-dir .

# Prepare persistent mount points
RUN mkdir -p /data /config /plugins

ENTRYPOINT ["oc"]
