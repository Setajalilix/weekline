# Weekline

Plan your week, log time by hand or with a flip-clock timer, and see how it actually went.

Weekline is a **single-user** weekly performance tracker. It is a Django app with server-rendered pages — not a React SPA, and not a public multi-user product.

**GitHub description** (About field, 350-character limit):

> Plan your week, log time by hand or with a flip-clock timer, and see how it actually went.

**Suggested topics:** `django` `postgresql` `htmx` `alpinejs` `tailwindcss` `time-tracking` `productivity`

---

## What you can do

- Set weekly goals with a target, color, and optional category
- Plan time on specific days, then edit or remove those blocks
- Log finished work with a 24-hour start/finish clock
- Run a split-flap focus timer (saves only at 5 minutes or more)
- See the week on a calendar from 01:00 to 24:00
- Review achievement (uncapped), history, and charts
- Change week start day and timezone in Settings

Weeks default to **Saturday–Friday**. Change that in Settings. The interface is English (LTR). Notes can be in any language, including Persian.

Time comes from two independent sources that both write `TimeEntry` rows:

| Source | When to use it |
| --- | --- |
| Manual log | You already did the work |
| Timer | You are sitting down to focus now |

---

## Stack

| Layer | Choice |
| --- | --- |
| App | Python 3.12+, Django 6.1 |
| Database | PostgreSQL 17 |
| Pages | Django templates, HTMX, Alpine.js |
| CSS | Tailwind CSS 4 |
| Bundler | Vite 7 (`django-vite`) |
| Charts | Chart.js |
| Icons | Lucide |

No REST API. No React, Next, or Vue.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Postgres)
- Python 3.12 or newer
- Node.js 20 or newer (to build CSS and JS)

---

## Quick start

```bash
git clone https://github.com/YOUR_USER/weekline.git
cd weekline
```

### 1. Database

Start Docker Desktop, then:

```bash
docker compose up -d
```

Postgres listens on **port 5433** so it does not collide with a local Postgres on 5432.

### 2. Python

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

Change `DJANGO_SECRET_KEY` in `.env` before you put this on a public host.

```bash
python manage.py migrate
python manage.py bootstrap
```

`bootstrap` creates the single user, app settings, and a few categories. Default sign-in:

- Username: `weekline`
- Password: `weekline`

Override those with `WEEKLINE_USERNAME` and `WEEKLINE_PASSWORD` in `.env`, then run `bootstrap` again.

### 3. Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Run

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and sign in.

---

## Live CSS and JS

For Vite hot reload while you change styles or scripts:

1. Set `VITE_DEV=1` in `.env`
2. In one terminal: `cd frontend && npm run dev`
3. In another: `python manage.py runserver`

Set `VITE_DEV=0` and run `npm run build` again before you commit a production-ready tree.

---

## Environment

Copy `.env.example` to `.env`. Do not commit `.env`.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret. Change this. |
| `DJANGO_DEBUG` | `1` locally, `0` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `POSTGRES_*` | Database name, user, password, host, port |
| `WEEKLINE_USERNAME` | The one account `bootstrap` creates |
| `WEEKLINE_PASSWORD` | Password for that account |
| `VITE_DEV` | `1` to load assets from Vite on port 5173 |

---

## Pages

| Path | What it is for |
| --- | --- |
| `/` | This week at a glance |
| `/planner/` | Weekly goals and day plans |
| `/daily/` | Log time and run the timer |
| `/calendar/` | Week grid of logged work |
| `/timer/` | Full-page flip clock |
| `/review/` | Weekly review and charts |
| `/history/` | Past weeks |
| `/settings/` | Week start, timezone, categories |

---

## Tests

Postgres must be running.

```bash
python manage.py test
```

---

## Project layout

```
weekline/
  config/                 Django settings and URLs
  performance/            Models, views, forms, services, tests
  templates/              Django HTML
  frontend/               Vite, Tailwind, Alpine, Chart.js
  static/                 Built assets after `npm run build`
  docker-compose.yml      PostgreSQL 17
```

---

## Publishing on GitHub

1. Create an empty repository. Do not add a README there if this file already exists.
2. Confirm `.env` is not tracked (`git status`). It is gitignored.
3. Rebuild frontend if `static/dist/` is missing: `cd frontend && npm run build`.
4. Push:

```bash
git init
git add .
git commit -m "Publish Weekline"
git branch -M main
git remote add origin https://github.com/YOUR_USER/weekline.git
git push -u origin main
```

5. In the repo **About** panel, paste the GitHub description from the top of this file.
6. Add a license file if you want others to reuse the code. This repo does not ship one yet.

On a public host you still need Postgres, a secret key, `DJANGO_DEBUG=0`, your real `ALLOWED_HOSTS`, and a process manager. Shared cPanel without SSH cannot run this stack. A PaaS with Postgres (Liara, Railway, or similar) can.

---

## License

No license file is included. Add one before you expect others to fork or reuse Weekline.
