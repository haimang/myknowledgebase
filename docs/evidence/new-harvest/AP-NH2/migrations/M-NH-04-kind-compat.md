# M-NH-04 — kind identity and compatibility

- New public identities: three single-root kind graphs plus existing registered-API scatter root/child.
- Old 13 current profile definitions remain enabled-unselected so their workflow keys still satisfy runtime active-key compatibility.
- Existing 16 historical compatibility plans remain injected; compiled digest diff is zero.
- New resolver consumes `source_kind` only. `acquisition_mode` and media declaration are typed route facts inside the graph.
- Old selector strings may be passed only through internal compatibility call signatures and are ignored for public resolution.
- Legacy pin hits increment closed metric `mkb_workflow_legacy_pin_total`; bounded retirement remains AP-NH8 work.
- Rollback: retain/re-enable old definitions and resolver mapping; never rewrite in-flight Execution rows.

Evidence: commit `81f1271`; NH2-T01/T05/T06/T07 PASS; Q18/T-O-398; `2026-08-29T18:53:27Z`.
