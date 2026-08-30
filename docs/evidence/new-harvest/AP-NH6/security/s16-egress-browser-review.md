# AP-NH6 S16 browser egress review

This is a document gate. Sign-off fields stay empty until an owner/reviewer actually signs. Filling a name or UTC here without that review is a forged signature.

## Checklist

- [ ] Parser remains network-denied (`unshare --net`); browser does not reuse that policy file.
- [ ] Every browser navigation hop is `EgressPolicy.check_url` / `validate_redirect` (S16-E08 / TM-04).
- [ ] Restricted redirect (metadata / private / over-budget) returns `SEC_EGRESS_DENIED` or `SEC_EGRESS_REDIRECT_DENIED` and does not start the browser process.
- [ ] In-page script cannot open a second egress path around S16 (closed proxy / no beacon).
- [ ] Production argv has no `--no-sandbox`; runtime uid is non-root.
- [ ] Render success is not accepted as print success.

## Sign-off (leave blank)

| Role | Name | UTC | Decision |
|------|------|-----|----------|
| reviewer | | | |
| owner | | | |

Evidence nodes already executed locally: `test_browser_egress_rechecks_each_redirect`, `test_browser_page_cannot_bypass_s16_prefetch`, `test_browser_runs_non_root`, `test_production_forbids_no_sandbox`.
