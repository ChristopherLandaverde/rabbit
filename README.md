# Rabbit

Rabbit is a multi-touch marketing attribution API with a React frontend. The API analyzes customer touchpoint data with five attribution models: first touch, last touch, linear, time decay, and position based. Results describe attribution under the selected model; they do not estimate causal impact.

## Requirements

- Python 3.12
- `uv` (recommended) or Python's built-in `venv` and `pip`

## Install

From the repository root, create a virtual environment and install the pinned dependencies:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Or use the standard Python tools:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The `.venv` directory is local and gitignored. `requirements.txt` includes the runtime and test dependencies.

## Run the API

From the repository root, activate the environment if needed, then run the single backend entrypoint:

```bash
source .venv/bin/activate
python run.py
```

The API listens on `http://localhost:8000`. Check that it is responding:

```bash
curl http://127.0.0.1:8000/health
```

The endpoint returns an HTTP response when the API is running; its JSON `status` also reflects dependency health and can report `unhealthy` when Redis is not available.

Interactive API documentation is at <http://localhost:8000/docs>. Health routes include `/health`, `/health/ready`, and `/health/live`.

## Test

Run the complete test inventory, continuing past existing collection errors so runnable tests execute too:

```bash
python -m pytest -q --continue-on-collection-errors
```

The current test baseline and known failures are documented in [docs/b0-baseline.md](docs/b0-baseline.md). CI runs this same command on pushes to `main` and on pull requests.

## Frontend

The React application is in `frontend/`. To run its development server, use Node.js and npm, then run `npm install` and `npm run dev` from that directory. Frontend setup is separate from the Python API.

## Docker

Docker Compose files remain available for local container use. Review `docker-compose.yml` and `docker-compose.override.yml` for the current services and ports before starting them; this README documents the supported Python API path.

## Attribution input

CSV analysis expects `timestamp`, `channel`, and `event_type`. Customer and conversion fields such as `customer_id`, `session_id`, `email`, and `conversion_value` are optional. For example:

```csv
timestamp,channel,event_type,customer_id,conversion_value
2024-01-01 10:00:00,email,click,cust_001,
2024-01-01 13:00:00,email,conversion,cust_001,100.00
```

Submit a CSV using the API:

```bash
curl -X POST http://127.0.0.1:8000/attribution/analyze \
  -F 'file=@data.csv' \
  -F 'model_type=linear'
```

Available model names are `first_touch`, `last_touch`, `linear`, `time_decay`, and `position_based`.
