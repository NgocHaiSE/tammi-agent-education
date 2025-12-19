# ========================================================================
# Multi-stage build for optimized production image
# ========================================================================
FROM python:3.12-slim AS builder

WORKDIR /opt/build

# Install build dependencies in a single layer
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libssl-dev \
        libffi-dev \
        pkg-config \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt /opt/build/requirements.txt

# Upgrade pip and build tools, then build wheels
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install grpcio-tools>=1.75.1 \
    && python -m pip wheel --wheel-dir=/opt/build/wheels -r /opt/build/requirements.txt \
    && ls -la /opt/build/wheels/

# Copy proto files and generate stubs
COPY agent/proto/ /opt/build/agent/proto/
RUN cd /opt/build && python agent/proto/generate_stubs.py

# ========================================================================
# Production stage - minimal runtime image
# ========================================================================
FROM python:3.12-slim

WORKDIR /app

# Install supervisor and runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        supervisor \
        net-tools \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /var/run

# Install runtime dependencies from pre-built wheels
COPY --from=builder /opt/build/wheels /wheels
RUN python -m pip install --no-cache-dir --no-deps /wheels/* \
    && rm -rf /wheels \
    && python -m pip install --no-cache-dir uvloop==0.19.0 \
    && python -m pip install --no-cache-dir gunicorn "uvicorn[standard]" \
    && python -m pip list

# Copy application code
COPY . /app

# Copy generated proto stubs from builder stage (ensures fresh generation)
COPY --from=builder /opt/build/agent/proto/ /app/agent/proto/


# Copy supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Entrypoint: run supervisord to manage both gRPC and HTTP servers
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
