# OJ Microline Dashboard

A monitoring and control dashboard for [OJ Microline WG4](https://www.ojelectronics.com) floor heating thermostats.

- **React frontend** — live dashboard showing current/set temperatures, mode, vacation state, and per-thermostat controls
- **FastAPI backend** — REST API with a 60-second TTL cache, proxies reads and writes to the OJ cloud API
- **Prometheus metrics** — all thermostat values exported as gauges, scraped by kube-prometheus-stack
- **Kubernetes deployment** — single container serving both the API and the built frontend

## Usage

### Dashboard

Open https://oj-microline.kamenet.org in a browser.

- Cards refresh automatically every 60 seconds
- Click **↺ Refresh** to force an immediate re-fetch from the thermostat API
- Click **▼ Controls** on any card to set the manual temperature, comfort setpoint, vacation setpoint, or mode for that thermostat
- Click **⚙ All** in the header to apply a setting to all thermostats at once

### API

The REST API is documented in [API.md](API.md). Quick reference:

| Method | Path | Description |
|---|---|---|
| `GET` | `/thermostats` | All thermostats |
| `POST` | `/thermostats/refresh` | Force re-fetch |
| `POST` | `/thermostats/all/manual` | Set manual SP on all |
| `POST` | `/thermostats/{name}/manual` | Set manual SP on one |
| `GET` | `/metrics/` | Prometheus scrape endpoint |

### Prometheus / Grafana

Metrics are available at `/metrics/` and scraped automatically via the `ServiceMonitor` in `k8s/servicemonitor.yaml`.

Grafana is at https://grafana.kamenet.org — see [MONITORING.md](MONITORING.md) for details.

## Development

### Run locally

```bash
# Pulls credentials from the cluster, starts uvicorn with --reload on :8001
./scripts/unseal.sh
```

### Run the frontend dev server

```bash
cd frontend
pnpm install
pnpm dev   # proxies /api → localhost:8001
```

### Run E2E tests

Requires the backend to be running on `:8001`.

```bash
cd frontend
pnpm exec playwright test
```

## Build and Deploy

```bash
./scripts/build.sh
```

## Configuration

| Env var | Default | Description |
|---|---|---|
| `THERMOSTAT_USERNAME` | required | OJ cloud account email |
| `THERMOSTAT_PASSWORD` | required | OJ cloud account password |
| `CACHE_TTL` | `60` | Seconds before re-fetching from the thermostat API |
| `API_PORT` | `8001` | Port the server listens on |

Credentials in k8s are managed with Sealed Secrets — see [SECRETS.md](SECRETS.md).

## Repo layout

```
main.py              # FastAPI app + Prometheus metrics
frontend/            # React + TypeScript (Vite)
  src/
    App.tsx          # Main layout, polling, bulk controls
    ThermostatCard.tsx
    Controls.tsx     # Per-thermostat and bulk control panel
    api.ts           # Typed API client
  e2e/               # Playwright tests
k8s/                 # Kubernetes manifests
scripts/
  unseal.sh          # Decrypt SealedSecret and run server locally
API.md               # Upstream OJ API documentation and quirks
SECRETS.md           # Sealed Secrets workflow
TODO.md              # Known gaps and planned work
```
