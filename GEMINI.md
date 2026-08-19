# Stock Analysis App — Project Context

## Overview
Taiwan stock EPS divergence analysis app. Built with **Streamlit**, deployed on **Google Cloud Run** via GitHub Actions CI/CD.

- **Repo**: https://github.com/doublechiang/stocks.git
- **Cloud Run service**: `stock-app` in project `stock-app-tw-061683`, region `asia-east1`
- **Public URL**: https://stock-app-213290980608.asia-east1.run.app/

## Key Files
| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app (stock charts, EPS data) |
| `Dockerfile` | Container image with Streamlit flags in CMD |
| `.streamlit/config.toml` | Streamlit server settings |
| `.github/workflows/deploy.yml` | CI/CD pipeline (push to main → deploy to Cloud Run) |
| `init_db.py` | SQLite database initialization |

## Streamlit on Cloud Run — Critical Deployment Rules
When modifying Streamlit server settings for Cloud Run deployment, always ensure:

1. **`enableCORS = true`** — Setting this to `false` causes Streamlit's Tornado WebSocket handler to reject connections with a 403 (origin mismatch between browser URL and internal bind address).
2. **`enableWebsocketCompression = false`** — Cloud Run's load balancer does not support WebSocket compression (`permessage-deflate`).
3. **`--session-affinity`** must be set in Cloud Run deploy flags — Streamlit is stateful and requires the same container instance for both HTTP and WebSocket.
4. **Do NOT enable HTTP/2** on Cloud Run — WebSocket requires HTTP/1.1 Upgrade mechanism.

## User Preferences
- Communicate in **Traditional Chinese (繁體中文)**
- The user is learning cloud deployment concepts; explain technical terms when first introduced
