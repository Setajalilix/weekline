# Weekline

A single-user weekly performance tracker: plan goals, log time by hand or with a flip-clock focus timer, then review the week.

## Stack

Django 6.1, PostgreSQL 17, HTMX, Alpine.js, Tailwind CSS 4, Vite, Chart.js.

## Run locally

1. Start Postgres: `docker compose up -d`
2. Create a virtualenv and install `requirements.txt`
3. Copy `.env.example` to `.env`
4. `python manage.py migrate`
5. `python manage.py bootstrap` (user `weekline` / `weekline` unless you change `.env`)
6. In `frontend/`: `npm install` then `npm run build`
7. `python manage.py runserver`

Open http://127.0.0.1:8000/ and sign in with `weekline` / `weekline`.

For live CSS/JS: `npm run dev` in `frontend/` and set `VITE_DEV=1` in `.env`.
Start Docker Desktop before `docker compose up -d` if the engine is not running.
