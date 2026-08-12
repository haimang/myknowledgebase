# MyKnowledgeBase (MKB)

MKB is a standalone Python 3.12 LS-RAG leaf worker. It exposes a small internal
Task API, runs a durable intake-to-retrieval pipeline, and deliberately does not
provide a UI, membership system, billing, webhooks, or a final-answer endpoint.

The implementation is governed by `docs/baseline/domain-truth/`, with
`D07-v1-acceptance-truth.md` as the delivery ledger. Runtime code does not import
or depend on the retired implementations in `context/`.

## Local development

```bash
uv sync --extra dev
MKB_INTERNAL_TOKENS=dev-token uv run uvicorn api.app:app --reload
uv run pytest
```

Business endpoints require `Authorization: Bearer <internal-token>`. The minimal
bootstrap flow is: register a Team, create an `intake.ingest` Task, run the local
worker (or use the test runner), then poll the Task or issue synchronous retrieval.

`/live` is dependency-free. `/ready` reports whether migrations, registries,
object storage, configured capabilities, and the active internal token set are
available.
