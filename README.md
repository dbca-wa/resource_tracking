# Resource Tracking application

Django and Leaflet application that collects tracking information using IMAP
from a mailbox and displays it on a collection of layers provided by
Geoserver. The application also downloads observation data from
automatic weather stations.

# Installation

The recommended way to set up this project for development is using
[Poetry](https://python-poetry.org/docs/) to install and manage a virtual Python
environment. With Poetry installed, change into the project directory and run:

    poetry install

To run Python commands in the virtualenv, thereafter run them like so:

    poetry run python manage.py

Manage new or updating project dependencies with Poetry also, like so:

    poetry add newpackage==1.0

# Environment variables

This project uses confy to set environment variables (in a `.env` file).
The following variables are required for the project to run:

    DATABASE_URL="postgis://USER:PASSWORD@HOST:PORT/DATABASE_NAME"
    SECRET_KEY="ThisIsASecretKey"

Other environment variables will be required to run the project in production
(these are context-dependent).

# Running

Use `runserver` to run a local copy of the application:

    poetry run python manage.py runserver 0:8080

Run console commands manually:

    poetry run python manage.py shell_plus

# Unit tests

Run unit tests like so:

    poetry run python manage.py test --keepdb -v2

# Docker image

To build a new Docker image from the `Dockerfile`:

    docker image build -t ghcr.io/dbca-wa/resource_tracking .

# Pre-commit hooks

This project includes the following pre-commit hooks:

- TruffleHog (credential scanning): https://github.com/marketplace/actions/trufflehog-oss

Pre-commit hooks may have additional system dependencies to run. Optionally
install pre-commit hooks locally like so:

    poetry run pre-commit install

Reference: https://pre-commit.com/
