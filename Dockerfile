FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy requirements and source for building
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --frozen

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# PYTHONPATH
ENV PYTHONPATH=/app/src

# Run application
CMD ["uv", "run", "python", "src/fastauth/main.py"]