# syntax=docker/dockerfile:1
# Args to centralise versions.
ARG PYTHON_VERSION=3.13-debian13-dev
ARG GCC_RUNTIME_VERSION=14.2.0-19+deb13u0+dhi5

# ---- Builder stage ----
FROM dhi.io/python:${PYTHON_VERSION} AS builder
ARG GCC_RUNTIME_VERSION

RUN <<EOF
set -euxo pipefail
apt-get update
# Install the aligned GCC runtime family and dependent packages
# in one transaction so APT cannot retain incompatible DHI revisions.
apt-get install -y --allow-downgrades --no-install-recommends \
  gcc-14-base="${GCC_RUNTIME_VERSION}" \
  libgcc-s1="${GCC_RUNTIME_VERSION}" \
  libstdc++6="${GCC_RUNTIME_VERSION}" \
  libgfortran5="${GCC_RUNTIME_VERSION}" \
  gdal-bin \
  proj-bin \
  gcc \
  g++
EOF

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --no-group dev --link-mode=copy --compile-bytecode --no-python-downloads --frozen

# ---- Runtime stage ----
FROM dhi.io/python:${PYTHON_VERSION} AS runtime
ARG GCC_RUNTIME_VERSION
LABEL org.opencontainers.image.title="resource_tracking" \
  org.opencontainers.image.description="DBCA Resource Tracking System" \
  org.opencontainers.image.source="https://github.com/dbca-wa/resource_tracking" \
  org.opencontainers.image.vendor="DBCA" \
  org.opencontainers.image.authors="asi@dbca.wa.gov.au"

RUN <<EOF
set -euxo pipefail
apt-get update

# Keep the complete GCC runtime dependency transaction together.
apt-get install -y --allow-downgrades --no-install-recommends \
  gcc-14-base="${GCC_RUNTIME_VERSION}" \
  libgcc-s1="${GCC_RUNTIME_VERSION}" \
  libstdc++6="${GCC_RUNTIME_VERSION}" \
  libgfortran5="${GCC_RUNTIME_VERSION}" \
  gdal-bin \
  proj-bin

ldconfig
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOF

# Environment variables
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy installed virtualenv from builder
COPY --from=builder /app /app

# Copy the remaining project files to finish building the project
COPY --chown=nonroot:nonroot gunicorn.py manage.py pyproject.toml ./
COPY --chown=nonroot:nonroot resource_tracking ./resource_tracking
COPY --chown=nonroot:nonroot tracking ./tracking

# Compile scripts and collect static files
RUN <<EOF
python -m compileall manage.py resource_tracking tracking
python manage.py collectstatic --noinput
EOF

# Run the project as the nonroot user
USER nonroot
EXPOSE 8080
CMD ["gunicorn", "resource_tracking.asgi:application", "--config", "gunicorn.py"]
