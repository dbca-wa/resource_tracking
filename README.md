# Resource Tracking application

Django and Leaflet application that collects tracking device information from a
variety of sources and aggregates it into a single database.

## Installation

The recommended way to set up this project for development is using
[Poetry](https://python-poetry.org/docs/) to install and manage a virtual Python
environment. With Poetry installed, change into the project directory and run:

    poetry install

Activate the virtualenv like so:

    poetry shell

To run Python commands in the activated virtualenv, thereafter run them as normal:

    python manage.py

Manage new or updating project dependencies with Poetry also, like so:

    poetry add newpackage==1.0

## Environment variables

This project uses confy to set environment variables (in a `.env` file).
The following variables are required for the project to run:

    DATABASE_URL="postgis://USER:PASSWORD@HOST:PORT/DATABASE_NAME"
    SECRET_KEY="ThisIsASecretKey"

Other environment variables will be required to run the project in production
(these are context-dependent). These variables include:

    ALLOWED_HOSTS
    CSRF_TRUSTED_ORIGINS
    EMAIL_HOST
    EMAIL_USER
    EMAIL_PASSWORD
    TRACPLUS_URL
    DFES_URL
    DFES_USER
    DFES_PASS
    GEOSERVER_URL

## Running

Use `gunicorn` to run the local ASGI server (`runserver` doesn't support async responses yet):

    gunicorn resource_tracking.asgi:application --config gunicorn.py --reload

Run console commands manually:

    python manage.py shell_plus

## Unit tests

Run unit tests like so:

    python manage.py test --keepdb -v2

## Docker image

To build a new Docker image from the `Dockerfile`:

    docker image build -t ghcr.io/dbca-wa/resource_tracking .

## Pre-commit hooks

This project includes the following pre-commit hooks:

- TruffleHog: <https://docs.trufflesecurity.com/docs/scanning-git/precommit-hooks/>

Pre-commit hooks may have additional system dependencies to run. Optionally
install pre-commit hooks locally like so:

    poetry run pre-commit install

Reference: <https://pre-commit.com/>
