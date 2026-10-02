# TestLens

A full-stack GenAI workbench that lets hardware engineers interrogate reliability test data in plain language.

TestLens works over drive-fleet SMART telemetry and the failure-prediction scores computed on it by [FailSight](https://github.com/coderloganli/failsight). An engineer asks a question; an LLM agent answers it by calling tools that query the test data and the prediction scores, and returns its answer together with the query results it drew on.

## Architecture

- **Backend**: Python, FastAPI, SQLAlchemy models with Alembic migrations, PostgreSQL on AWS RDS. API endpoints and the agent's tool calls are written as asyncio async/await code.
- **Agent**: an LLM agent with tool calling over the test data and the failure-prediction scores. Query results and agent session state are cached in ElastiCache Redis.
- **Frontend**: Next.js, TypeScript, React.
- **Infrastructure**: every service is containerized and deployed to AWS EKS through a Helm chart. All AWS infrastructure (VPC, EKS, RDS, ElastiCache) is provisioned with Terraform.
- **Observability**: OpenTelemetry tracing across the API, the agent's tool calls and the database; Prometheus metrics; structured logging.

## Getting started

Run the whole stack (PostgreSQL, Redis, API, frontend) with Docker Compose. A one-off `migrate` service applies the Alembic migrations and loads a small synthetic sample of drive telemetry and prediction scores.

```bash
docker compose up --build
# Frontend: http://localhost:3000   API: http://localhost:8000   Metrics: http://localhost:8000/metrics/
```

The API uses a deterministic fake LLM provider by default. To use Claude, set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` before starting.

Backend development (Python 3.12+), against the Compose `postgres` and `redis` services:

```bash
cd backend
python -m venv ../.venv && ../.venv/Scripts/activate   # Linux/macOS: source ../.venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head && python -m app.seed
uvicorn app.main:create_app --factory --reload
pytest                      # runs on SQLite and an in-memory Redis; no services needed
ruff check . && ruff format --check .
```

Frontend development (Node 24):

```bash
cd frontend
npm install
API_URL=http://localhost:8000 npm run dev
npm run typecheck && npm run build
```

Deployment assets live in `deploy/helm/testlens` (Helm chart for EKS) and `infra/terraform` (modules for VPC, EKS, RDS and ElastiCache, composed in `environments/dev`).

## Status

Under active development. The scope above is committed; code is being added to this repository as it is built.
