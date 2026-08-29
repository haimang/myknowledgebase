# NH1 runtime smoke supply record

| Capability | Observed identity | Bounded execution | Result |
|---|---|---|---|
| PDF text | `pdftotext version 24.02.0` | new network namespace; uid/gid `nobody`; CPU 5s; AS 512MiB; fd 64; output 8MiB; wall timeout 8s | real Firefox-produced PDF text extracted; encrypted PDF typed 422 |
| Browser render | `Mozilla Firefox 154.0` | direct local executable; uid/gid `nobody`; headless; data-URL fixture; wall timeout 20s; no `no-sandbox` argument | JavaScript replaced static shell with real DOM marker |
| Browser print | `geckodriver 0.37.1 (2026-08-14)` + Firefox 154.0 | same hardened process boundary as render, distinct WebDriver print operation | returned bytes begin `%PDF-1.7` |
| Multimodal request | `Nh1MultimodalProbeRequest` spike contract | PromptRef + model identity + media type + content digest + bounded bytes-or-handle | real PDF bytes accepted; legacy text-only `GenerateRequest` rejects the shape |

License/deployment note: host executables are invoked as subprocesses and are not linked into the proprietary Python package. This is a feasibility record, not NH6 production SBOM approval.

CVE note: current production-grade CVE scan, malicious corpus, package pin/rollback, and owner waiver registry remain AP-NH6 hard gates. No waiver was used to pass NH1.
