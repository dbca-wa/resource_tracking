# syntax=docker/dockerfile:1
FROM dhi.io/python:3.14-debian13-dev AS build-stage
LABEL org.opencontainers.image.authors=asi@dbca.wa.gov.au
LABEL org.opencontainers.image.source=https://github.com/dbca-wa/resource_tracking

# Install system packages required to run the project
RUN apt-get update -y \
  && apt-get install -y --no-install-recommends gdal-bin proj-bin libgdal36 \
  # Run shared library linker after installing packages
  && ldconfig \
  && rm -rf /var/lib/apt/lists/*

# Import uv to install dependencies
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/
WORKDIR /app
# Install project dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --no-group dev --link-mode=copy --compile-bytecode --no-python-downloads --frozen \
  # Remove uv and lockfile after use
  && rm -rf /bin/uv \
  && rm uv.lock

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"


# Copy the remaining project files to finish building the project
COPY gunicorn.py manage.py pyproject.toml ./
COPY resource_tracking ./resource_tracking
COPY tracking ./tracking
RUN python manage.py collectstatic --noinput
# Compile scripts and collect static files
RUN python -m compileall manage.py resource_tracking tracking \
  && python manage.py collectstatic --noinput

# Run the project as the nonroot user
USER nonroot
EXPOSE 8080
CMD ["gunicorn", "resource_tracking.asgi:application", "--config", "gunicorn.py"]
