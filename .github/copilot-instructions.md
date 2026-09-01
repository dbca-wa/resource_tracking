# resource_tracking — agent instructions

DBCA (WA) internal Django 5.2 / GeoDjango application: harvests location data from remote tracking devices (vehicles, aircraft) into PostGIS and serves it via a map UI, GeoJSON/CSV/GeoPackage downloads, and a tastypie REST API. Core models: `Device` and `LoggedPoint` (`tracking/models.py`).

## Quick facts

- Python ≥ 3.13, Django 5.2.x (pinned), PostgreSQL + PostGIS, `django.contrib.gis`.
- Package manager is `uv` only — never `pip install`; add deps with `uv add` (updates `pyproject.toml` + `uv.lock`).
- App version lives in `pyproject.toml` `[project]` and is read at runtime (`APPLICATION_VERSION_NO`, Sentry release). Bump it there, not in code.

## Commands

```bash
uv sync                                   # install deps into .venv
source .venv/bin/activate

# Dev server: use gunicorn — `manage.py runserver` is not used in this project (async SSE view, DeviceStream).
gunicorn resource_tracking.asgi:application --config gunicorn.py --reload

# Tests (need GDAL + a PostGIS DB via DATABASE_URL — see Setup gotchas):
uv run python manage.py collectstatic                # CI does this before tests; WhiteNoise manifest storage requires it
uv run python manage.py test --noinput --failfast    # full suite (CI form)
uv run python manage.py test tracking.test_views --keepdb -v2                 # one module
uv run python manage.py test tracking.test_views.<Class>.<test> --keepdb      # one test

uv run ruff check .                       # lint — manual, CI does NOT run ruff (line-length 140; djlint profile django for templates; both configured in pyproject)
uv run python manage.py shell_plus        # django-extensions shell, models auto-imported
```

## Setup gotchas

- **System deps:** GDAL + PROJ (`gdal-bin`, `proj-bin`, `libgdal`) must be installed — GeoDjango fails without them. The Dockerfile and CI both install them.
- **`.env`** at the repo root is required: `DATABASE_URL="postgis://…"` and `SECRET_KEY` minimum; further prod vars in `README.md`. Never commit `.env` — TruffleHog runs in pre-commit and CI. Committed secrets travel as encrypted `*.env.enc` (openssl AES-256-CBC/PBKDF2); decrypt with `decrypt-env-files-recursive.sh` (prompts for passphrase, removes the `.enc`).
- **Auth model:** `SSOLoginMiddleware` is trusted-header auto-login (an upstream Auth2 proxy sends `REMOTE_USER` / `X_EMAIL` / …). It never blocks unauthenticated requests — **the only auth gate is each view's `LoginRequiredMixin`**. There is no local login flow; `LOGIN_URL` points at `/admin/`. For dev, use `createsuperuser` + admin.
- **Tests need PostGIS** — the runner creates a test database; vanilla PostgreSQL fails. CI uses a `postgis/postgis:16-3.5` service container.

## Testing conventions

- `django.test.TestCase`; fixtures via `mixer.blend(Model, ...)` from `mixer.backend.django` — never `Model.objects.create()`.
- `self.client.force_login(User.objects.create(username="testuser"))` for authenticated tests; URLs via `reverse("tracking:<name>")` — never hardcoded; assert HTTP status and `Content-Type` explicitly.
- Test files: `test_<module>.py` in the app directory (currently `test_views.py`, `test_harvest.py`, `test_signals.py`).

## Structure

```
resource_tracking/     # project package: settings, urls, asgi/wsgi, middleware (health check, client disconnects), api
tracking/              # the app: models, views, forms, api, signals, utils, harvest, email_utils
  management/commands/ # harvest commands — thin wrappers around tracking/harvest.py
  migrations/          # never edit by hand
kustomize/             # K8s: base/, template/, overlays/prod/, overlays/uat/
staticfiles/           # collectstatic output — never edit
```

## Coding conventions

### General

- Line length 140 (ruff). Type hints on signatures (`-> str`, `-> int`, `-> bool`, `-> None`).
- Loggers at module level (`LOGGER = logging.getLogger("tracking")`), stdout only. f-strings for formatting.

### Imports (project-specific)

- `import orjson as json` — always; use `json.loads()` / `json.dumps()`.
- `import unicodecsv as csv` — always.
- Order: stdlib → third-party → Django → local app.

### Settings & environment

- Env vars only through `dbca_utils.utils.env(name, default)` — never `os.environ`. No hardcoded secrets.
- Timezone is `Australia/Perth`: use `timezone.now()`, never `datetime.now()`; store aware datetimes.

### Models

- Model fields imported from `django.contrib.gis.db.models`, not `django.db.models`.
- All spatial data in WGS84 / EPSG:4326.
- Choice constants are module-level, defined above the `*_CHOICES` tuples.
- `save()` populates denormalised display fields (`district_display`, `callsign_display`, `rin_display`); `clean()` raises `ValidationError` for business rules; `Meta.ordering` always set.
- `DEFAULT_AUTO_FIELD = AutoField` — don't introduce BigAutoField.

### Views

- CBVs only; always set `http_method_names`; URLs via `reverse("tracking:<name>")`.
- Authorisation in `dispatch()` returning `HttpResponseForbidden` directly.
- Multi-format downloads (GeoJSON/CSV/GeoPackage) via a `format` query param or class attribute; `StreamingHttpResponse` for large exports; orjson for JSON in views.
- JS config goes to templates via a `javascript_context` dict in `get_context_data()`.

### Caching × auth (incident-earned)

- Caching a `LoginRequiredMixin` view? Decorate **`get`**, not `dispatch` — `cache_page` on `dispatch` serves cached responses _before_ the auth check runs, and cache keys are path-based unless the response sets `Vary`. (This exact bypass was found on `/api/prtg/`.)
- Cache backend: shared Valkey when `VALKEY_CACHE_HOST` is set, otherwise per-worker locmem.

### Forms / API / URLs

- Crispy forms + `crispy_bootstrap5`; layout via `FormHelper` / `Layout`; `CRISPY_TEMPLATE_PACK = "bootstrap5"`.
- Tastypie resources extend `APIResource`; `Meta` via `generate_meta()` / `generate_filtering()` (`tracking/utils.py`); base path `/api/v1/`; `CSVSerializer` for CSV; `HttpCache` for cache-control.
- Old URL patterns are kept as permanent `RedirectView`s — never delete them.

### Harvest / ingestion

- Parse functions in `tracking/utils.py`; save functions in `tracking/harvest.py`; command classes stay thin. The email-based sources (iriditrak, mp70, spot, dplus) share the single `harvest_tracking_email` command; the other feeds have one command each.
- `validate_latitude_longitude(lat, lon)` before creating any `LoggedPoint`; `get_or_create` for `Device`; `typing.Literal` for `device_type` params.
- Ingestion is triggered by K8s CronJobs (`kustomize/overlays/<env>/cronjobs/harvest-*`), not by the web pod — a new source needs a cronjob entry in each overlay.

### Signals & middleware

- `@receiver` handlers in `tracking/signals.py`, connected in `TrackingConfig.ready()`.
- Custom middleware: callable-class pattern. `HealthCheckMiddleware` is first in `MIDDLEWARE` and serves `/readyz` + `/livez` before the security stack.

### Spatial output

- GeoJSON via `django.core.serializers` `"geojson"` (djgeojson). GeoPackage via `fudgeo` (`WGS84` constant, `SpatialReferenceSystem` from `tracking/utils.py`).
- Content types: `application/vnd.geo+json`, `text/csv`, `application/x-sqlite3`.

## Dependencies & database

- **deptry deliberately ignores several "unused dependency" (DEP002) hits** (`gunicorn`, `whitenoise`, `psycopg`, `uvloop`, … — runtime deps that aren't imported). Don't remove them when tidying.
- DB access goes through PgBouncer transaction pooling: `CONN_MAX_AGE = 0`, server-side cursors disabled (`settings.py`). Don't write code that assumes persistent DB connections.

## Auth & permissions

- Device edits require membership of `DEVICE_EDITOR_USER_GROUP` (default `"Edit Resource Tracking Device"`) or superuser — checked in `DeviceUpdate.dispatch()`. New users are auto-added to the group by a `post_save` signal on `User`.
- Never disable Sentry or weaken the security middleware / CSRF settings.

## CI & deployment

- **run-tests.yml** (push/PR to main): `uv sync` → `collectstatic` → `manage.py test --noinput --failfast`, on a PostGIS 16 service with GDAL installed. Lint is manual — run `ruff` yourself.
- **multi-build.yml**: multi-arch image (amd64/arm64) → `ghcr.io/dbca-wa/resource_tracking` on pushes to main, semver tags (tag → image tag) and a weekday schedule; Trivy results go to the Security tab.
- **Pre-commit**: TruffleHog secret scan only (requires the `trufflehog` binary); no linters wired in.
- Runtime: gunicorn ASGI, 4 workers, uvloop, port 8080, nonroot; static files baked at build time via `collectstatic`.
- **Migrations run as a separate step — never in container startup.**
