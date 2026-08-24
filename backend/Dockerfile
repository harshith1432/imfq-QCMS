FROM python:3.11-slim

# Install system utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user
RUN groupadd -r qcms && useradd -r -g qcms -m -s /bin/bash qcms

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set permissions to non-root user
RUN chown -R qcms:qcms /app

USER qcms

EXPOSE 5000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/auth/maintenance-status')" || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "run:app"]


