# Use a Python base image
FROM python:3.13-slim

# Install system dependencies & Node.js (needed for Node MCP servers)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Astral 'uv' for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock package.json package-lock.json ./

# Install Node dependencies
RUN npm ci

# Install Python dependencies using uv (creates .venv)
RUN uv sync --frozen --no-dev

# Copy application files
COPY backend/ ./backend/
COPY agent/ ./agent/
COPY static/ ./static/

# Expose port and create data volume directory
EXPOSE 8000
RUN mkdir -p /app/data

# Define Environment Variables
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/pet_companion.db
ENV PATH="/app/.venv/bin:$PATH"

# Run the FastAPI server
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
