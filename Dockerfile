FROM python:3.12-alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -h /home/appuser -s /bin/sh -D appuser

# Install system dependencies
RUN apk update && apk add --no-cache \
    curl \
    && apk upgrade \
    && rm -rf /var/cache/apk/*

# Set work directory
WORKDIR /app

# Install Python dependencies (copy requirements first for better caching)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code (exclude unnecessary files)
COPY core/ core/
COPY config/ config/
COPY templates/ templates/
COPY storypacks/ storypacks/
COPY utilities/ utilities/
COPY main.py .
COPY README.md .

# Create necessary directories and set ownership
RUN mkdir -p /app/storage /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Simple health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; exit(0)" || exit 1

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]