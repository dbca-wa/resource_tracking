# Prepare the base environment.
# We use osgeo/gdal instead of a python base image because of the requirement to install the GDAL library.
FROM osgeo/gdal:ubuntu-small-3.1.3 as builder_base_rt
MAINTAINER asi@dbca.wa.gov.au
RUN apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y vim unzip p7zip-full wget git telnet libmagic-dev gcc binutils libproj-dev python3-dev python3-pip python3-setuptools python3-venv software-properties-common \
  && rm -rf /var/lib/apt/lists/* \
  && pip3 install --upgrade pip

# Install Python libs from requirements.txt.
# Can't use Poetry because it won't install GDAL :/
FROM builder_base_rt as python_libs_rt
WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

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
