# Stock Analysis App — Project Context

## Overview
Taiwan stock EPS divergence analysis app. Built with **Flask**, deployed on **Google Cloud Run** via GitHub Actions CI/CD.

- **Repo**: https://github.com/doublechiang/stocks.git
- **Cloud Run service**: `stock-app` in project `stock-app-tw-061683`, region `asia-east1`
- **Public URL**: https://stock-app-213290980608.asia-east1.run.app/

## Key Files
| File | Purpose |
|------|---------|
| `app.py` | Main Flask app (routes, stock charts, EPS data) |
| `templates/index.html` | Jinja2 template (UI with Bootstrap + Plotly charts) |
| `Dockerfile` | Container image with gunicorn CMD |
| `.github/workflows/deploy.yml` | CI/CD pipeline (push to main → deploy to Cloud Run) |
| `init_db.py` | SQLite database initialization |

## Flask on Cloud Run — Deployment Notes
This app uses Flask + gunicorn (pure HTTP, no WebSocket). Deployment is straightforward:

1. **gunicorn** serves the Flask app with `--workers 2 --threads 4`
2. **No session affinity needed** — Flask is stateless, each request is independent
3. **No WebSocket complications** — no CORS, compression, or HTTP/2 issues
4. Charts are rendered server-side using Plotly's `to_html()` and embedded in the response

## User Preferences
- Communicate in **Traditional Chinese (繁體中文)**
- The user is learning cloud deployment concepts; explain technical terms when first introduced
