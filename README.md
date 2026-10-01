# TestLens

A full-stack GenAI workbench that lets hardware engineers interrogate reliability test data in plain language.

TestLens works over drive-fleet SMART telemetry and the failure-prediction scores computed on it. An engineer asks a question; an LLM agent answers it by calling tools that query the test data and the prediction scores, and returns its answer together with the query results it drew on.

## Architecture

- **Backend**: Python, FastAPI, SQLAlchemy models with Alembic migrations, PostgreSQL on AWS RDS. API endpoints and the agent's tool calls are written as asyncio async/await code.
- **Agent**: an LLM agent with tool calling over the test data and the failure-prediction scores. Query results and agent session state are cached in ElastiCache Redis.
- **Frontend**: Next.js, TypeScript, React.
- **Infrastructure**: every service is containerized and deployed to AWS EKS through a Helm chart. All AWS infrastructure (VPC, EKS, RDS, ElastiCache) is provisioned with Terraform.
- **Observability**: OpenTelemetry tracing across the API, the agent's tool calls and the database; Prometheus metrics; structured logging.

## Status

Under active development. The scope above is committed; code is being added to this repository as it is built.
