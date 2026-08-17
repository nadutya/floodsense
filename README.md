# FloodSense — Oxford operations demonstrator

An interactive, asset-level urban drainage scenario for the Oxford Saïd Global Climate Tech Challenge 2026. It answers a deliberately operational question: **which inlet fails first, when, what does it affect, and what changes if a crew clears it now?**

This is an explainable demonstration model, not a calibrated Oxford flood forecast. All locations, capacities, blockage values and observations in the application are synthetic and are kept in `backend/floodsense/data/oxford_demo.json`.

## Product and technical scope

The source documentation has a compelling closed-loop concept, but its city-scale sensor fusion, CCTV vision, satellite inputs, ML correction and hydraulic twin are not credible to build as one competition MVP. This prototype keeps the differentiator—the prediction-to-action-to-counterfactual loop—and represents future inputs through a clean data boundary.

The Python engine uses a transparent storage-bucket network:

1. rainfall becomes surface runoff using catchment area and a runoff coefficient;
2. pipe capacity is reduced by inlet blockage;
3. each inlet stores water up to its local surface threshold;
4. excess water is split between surface ponding and a downstream inlet;
5. time-to-overflow, risk and consequence-weighted priority are derived each minute;
6. cleaning changes blockage to 8%, then the complete scenario is re-simulated;
7. baseline and intervention runs produce prevented overflow and risk reduction.

The model is intentionally deterministic and is not described as machine learning. React does no hydraulic, risk, priority or recommendation calculation; it only selects and renders states returned by the API. Canvas rain is decorative.

## Architecture

- `backend/floodsense/model.py` — pure, framework-independent calculation engine
- `backend/floodsense/data/oxford_demo.json` — synthetic scenario and future ingestion boundary
- `backend/floodsense/api.py` — validated FastAPI endpoints
- `backend/tests/` — standard-library model tests
- `frontend/` — React, TypeScript, Vite, MapLibre and Canvas rain

API endpoints:

- `GET /api/health`
- `GET /api/network`
- `POST /api/scenarios/run`
- `POST /api/scenarios/compare`

## Run locally

Requirements: Python 3.10+ and Node.js 20+.

Terminal 1:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn floodsense.api:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://localhost:5173`. The map tiles and web font require an internet connection; the application and scenario data otherwise run locally.

### Run on a Linux server

Start both processes on the same server (in separate terminals or services):

```bash
PYTHONPATH=backend .venv/bin/python -m uvicorn floodsense.api:app --host 127.0.0.1 --port 8000
cd frontend
npm run dev -- --host 0.0.0.0
```

Vite proxies `/api` to `http://127.0.0.1:8000` by default. Using the explicit IPv4 address avoids Node resolving `localhost` to `::1` while Uvicorn listens on IPv4 only. If the backend runs in another container or on another host, set its reachable address before starting Vite:

```bash
FLOODSENSE_API_TARGET=http://backend:8000 npm run dev -- --host 0.0.0.0
```

Do not expose Uvicorn separately when using the Vite proxy; only port `5173` needs to be reachable for this development setup.

### Production deployment on port 80 with Nginx

The repository includes a ready Nginx configuration at `deploy/nginx/floodsense.conf`. It serves the production frontend directly and forwards `/api` requests to FastAPI. Vite does not run in this setup.

The supplied configuration expects the project at `/var/www/floodsense`. Copy or clone it there, then run from the project directory:

```bash
cd /var/www/floodsense

python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt

cd frontend
npm install
npm run build
cd ..
```

Test the backend before configuring Nginx:

```bash
cd /var/www/floodsense
PYTHONPATH=backend .venv/bin/python -m uvicorn floodsense.api:app --host 127.0.0.1 --port 8000
```

In another terminal, check that `curl http://127.0.0.1:8000/api/health` returns `{"status":"ok"}`, then stop this test process with `Ctrl+C`.

Install and enable the Nginx configuration:

```bash
sudo apt update
sudo apt install -y nginx
sudo cp /var/www/floodsense/deploy/nginx/floodsense.conf /etc/nginx/sites-available/floodsense
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/floodsense /etc/nginx/sites-enabled/floodsense
sudo nginx -t
sudo systemctl reload nginx
```

Install the included systemd service so FastAPI starts automatically and survives SSH logout and server restarts:

```bash
sudo cp /var/www/floodsense/deploy/systemd/floodsense-api.service /etc/systemd/system/floodsense-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now floodsense-api
sudo systemctl status floodsense-api
```

Verify the complete deployment:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1/api/health
```

Both commands should return `{"status":"ok"}`. Then open `http://SERVER_IP/`. Port `8000` should remain private; only ports `80` (and later `443` for HTTPS) need to be opened in the firewall.

Useful diagnostics:

```bash
sudo journalctl -u floodsense-api -n 100 --no-pager
sudo nginx -t
```

If the repository is installed somewhere other than `/var/www/floodsense`, change the paths in both deployment files before copying them into Nginx and systemd.

On Windows, verify first that `py -3.10 --version` reports Python 3.10.x. Do not use the bare `python` command if it resolves to MSYS/MinGW. If `.venv` was previously created by that Python, delete that broken `.venv` directory and recreate it with `py -3.10 -m venv .venv`.

## Verification

```powershell
$env:PYTHONPATH="backend"
py -3.10 -m unittest discover -s backend/tests -v
cd frontend
npm.cmd run build
```

## Demonstration path

Set rainfall to about 38–50 mm/h, start the storm and scrub the timeline. Select `OX-103`, the constrained Hythe Bridge Street inlet upstream of the clinic route. When its forecast becomes urgent, choose **Dispatch crew & recalculate**. The API runs both scenarios; the map continues on the intervention timeline and the panel reports avoided surface water.

## Highest-value next improvements

1. Calibrate catchments and capacities with Oxfordshire drainage/GIS and observed storm incidents.
2. Replace constant rainfall with a weather-API hyetograph and uncertainty bands.
3. Validate flow routing using terrain rasters or EPA SWMM, while keeping the current API contract.
4. Add persistent incident/crew state and sensor adapters (MQTT/HTTP) behind the existing data boundary.
5. Test accessibility, mobile dispatch use and operator comprehension with public-works users.
