FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create user/group if they don't already exist
RUN if ! getent group 100; then groupadd -g 100 appuser; fi && \
    if ! id -u 1026 >/dev/null 2>&1; then useradd -u 1026 -g 100 -m -s /bin/bash appuser; fi

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app source to a staging location
COPY core/ /app-template/core/
COPY config/ /app-template/config/
COPY templates/ /app-template/templates/
COPY storypacks/ /app-template/storypacks/
COPY utilities/ /app-template/utilities/
COPY tests/ /app-template/tests/
COPY main.py /app-template/
COPY README.md /app-template/

# Prep folders and permissions
RUN mkdir -p /app-template/storage /app-template/logs && \
    chown -R 1026:100 /app-template

# One-time initializer
RUN echo '#!/bin/bash\n\
if [ ! -f /app/main.py ]; then\n\
  echo "Initializing app directory with template files..."\n\
  cp -r /app-template/* /app/\n\
  mkdir -p /app/storage /app/logs\n\
  chown -R 1026:100 /app\n\
fi\n\
exec "$@"' > /usr/local/bin/init-app.sh && chmod +x /usr/local/bin/init-app.sh

# Final folder prep
RUN mkdir -p /app/storage /app/logs && \
    chown -R 1026:100 /app

USER 1026:100

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; exit(0)" || exit 1

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/init-app.sh"]
CMD ["python", "main.py"]
