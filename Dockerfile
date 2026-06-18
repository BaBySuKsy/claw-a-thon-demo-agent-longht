FROM python:3.10-slim

# Prevent .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

WORKDIR /app

# Install deps first — cached layer, only busts when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source (includes src/data_platform/ knowledge cache)
COPY src/ src/

# Copy web UI (served at GET / by the agent so the public endpoint is browsable)
COPY ui/ ui/

# Non-root user for security
RUN adduser --disabled-password --no-create-home --uid 1001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

# Health check — AgentBase pings /ping every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; r=requests.get('http://localhost:8080/health',timeout=5); exit(0 if r.status_code==200 else 1)"

CMD ["python", "src/main.py"]
