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

An internal `intake.ingest` payload selects prompt catalog identities rather
than shipping prompt bytes or filesystem paths. Provide `json_prompt_id`, a
closed `domain` (+ optional `flavor`), and/or `granularity`. Explicit
`*_prompt_id` fields override domain defaults. `markdown_prompt_id` is optional.

```json
{
  "request_intent": "intake.ingest",
  "payload": {
    "domain": "documentation",
    "flavor": "qna",
    "granularity": "g1",
    "source": {
      "source_kind": "inline_payload",
      "external_key": "example-1",
      "content": "source material"
    }
  }
}
```

`domain=documentation` resolves to `promptA.documentation.default`,
`promptB.documentation.g1`, and `promptC.documentation.default`.
A flavor of `qna` / `eval` / `closure` / `plan` / `code-review` also selects
`promptB.documentation.{flavor}` as the optional markdown hop.

`granularity` is a closed level that picks the json template:

- `g0` → `{0}` (`promptB.documentation.g0` or `promptB.json.g0`)
- `g1` → `{0,1}` (default)
- `g2` → `{0,1,2}`

If both `json_prompt_id` and `granularity` are sent, the catalog row must
match that level or materialize fails closed.

The catalog resolves version, git-relative path, role, granularity profile, and
content hash during materialization; the execution keeps that selection frozen.
