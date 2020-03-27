# Prepare the base environment.
FROM python:3.7-slim-buster as builder_base_rt
MAINTAINER asi@dbca.wa.gov.au
RUN apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y vim unzip p7zip-full wget git telnet libmagic-dev gcc binutils libproj-dev gdal-bin python3-dev \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --upgrade pip
RUN apt-get update -y && apt-get install --no-install-recommends -y vim unzip p7zip-full
RUN apt-get install software-properties-common -y && apt-get update
RUN apt-get update && apt-get install gdal-bin
RUN apt-get install g++ libgdal-dev -y
# Install Python libs from requirements.txt.
FROM builder_base_rt as python_libs_rt
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install the project.
FROM python_libs_rt
COPY gunicorn.ini manage.py pollstations.py ./
COPY resource_tracking ./resource_tracking
COPY tracking ./tracking
COPY weather ./weather
COPY radio ./radio

COPY env ./.env
RUN python manage.py collectstatic --noinput
RUN rm .env
# Run the application as the www-data user.
USER www-data
EXPOSE 8080
CMD ["gunicorn", "resource_tracking.wsgi", "--config", "gunicorn.ini"]
