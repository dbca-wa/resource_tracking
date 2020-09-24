# Prepare the base environment.
FROM osgeo/gdal:ubuntu-small-3.1.3 as builder_base_rt
MAINTAINER asi@dbca.wa.gov.au
RUN apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y vim unzip p7zip-full wget git telnet libmagic-dev gcc binutils libproj-dev python3-dev python3-pip python3-setuptools python3-venv software-properties-common \
  && rm -rf /var/lib/apt/lists/* \
  && pip3 install --upgrade pip

# Install Python libs from requirements.txt.
FROM builder_base_rt as python_libs_rt
WORKDIR /app
ENV POETRY_VERSION=1.0.5
RUN pip install "poetry==$POETRY_VERSION"
RUN python3 -m venv /venv
COPY poetry.lock pyproject.toml /app/
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

# Install the project.
FROM python_libs_rt
COPY gunicorn.py manage.py ./
COPY resource_tracking ./resource_tracking
COPY radio ./radio
COPY tracking ./tracking
RUN python3 manage.py collectstatic --noinput

# Run the application as the www-data user.
USER www-data
EXPOSE 8080
CMD ["gunicorn", "resource_tracking.wsgi", "--config", "gunicorn.py"]
