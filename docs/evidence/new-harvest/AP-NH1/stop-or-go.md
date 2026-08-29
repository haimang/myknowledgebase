# AP-NH1 Stop-or-Go

> Verdict: `GO`
> Observed: `2026-08-29T17:12:10Z`
> Implementation: `1cdc066766a92eb1d8680bbf30689a443231234c` + `87eeadf431c44f841536dde6e964450d9aa8f8b8`

- `NH1-T01..T07`: PASS at their frozen minimum layers.
- Selected-output: optional candidate ports + one canonical output + one tail compile without changing the one-binding fence; durable zero/one/double/missing-fact behavior is fail-loud.
- Actual S05: legacy/unsealed/sealed are SQL-distinct; outcome + seal rollback together; same seal replays; different seal conflicts.
- Runtime: real parser and browser processes succeeded; no skip, 503, monkeypatch fetcher, empty clean, or model-list probe was counted as PASS.
- This GO proves feasibility only. It does not claim AP-NH2 production CONTROL, AP-NH3 production migration, AP-NH6 deployable supply, or AP-NH7 live-to-retrieval completion.

No frozen Truth was disproved; no reopen is required. NH2 may start under the serial todo-list.
