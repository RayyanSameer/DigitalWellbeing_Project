# -------------------------
# Stage 1: Build
# -------------------------
FROM python:3.12-slim AS build

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# -------------------------
# Stage 2: Production
# -------------------------
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies as root
RUN apt-get update && apt-get install -y \
    libpq-dev \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages and app from build stage
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /app /app

# Switch to non-root user
RUN useradd -m appuser
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Copy wait-for-it script (no chmod needed)
COPY wait-for-it.sh /wait-for-it.sh

# Use python -m uvicorn to avoid PATH issues
CMD ["bash", "/wait-for-it.sh", "db:5432", "--", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
