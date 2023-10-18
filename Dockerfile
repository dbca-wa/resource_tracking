# Prepare the base environment.
FROM python:3.10.13-slim as builder_base_rt
MAINTAINER asi@dbca.wa.gov.au
LABEL org.opencontainers.image.source https://github.com/dbca-wa/resource_tracking

RUN apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install -y libmagic-dev gcc binutils gdal-bin proj-bin python3-dev libpq-dev curl \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --upgrade pip

# Install Python libs using Poetry.
FROM builder_base_rt as python_libs_rt
WORKDIR /app
ARG POETRY_VERSION=1.6.1
RUN pip install poetry=="${POETRY_VERSION}"
COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --only main

# Create a non-root user.
ARG UID=10001
ARG GID=10001
RUN groupadd -g "${GID}" appuser \
  && useradd --no-create-home --no-log-init --uid "${UID}" --gid "${GID}" appuser

# Install the project.
FROM python_libs_rt
COPY gunicorn.py manage.py ./
COPY resource_tracking ./resource_tracking
COPY tracking ./tracking
RUN python manage.py collectstatic --noinput

USER ${UID}
EXPOSE 8080
CMD ["gunicorn", "resource_tracking.wsgi", "--config", "gunicorn.py"]
