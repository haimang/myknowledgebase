# AP-NH6 pin / license / CVE notes

Machine-readable inventory: `sbom-inventory.json`. Repository license remains Proprietary (`pyproject.toml`). No PDF/browser/OCR library is added to Python dependencies.

| Capability | Integration | License class | Linked into main process |
|---|---|---|---|
| `pdf.parse` | `pdftotext` subprocess | GPL-2.0-or-later | no |
| `browser.render` / `browser.print_pdf` | Firefox + geckodriver subprocess | MPL-2.0 | no |
| `ocr.deterministic` | owned glyph worker + `pdftoppm` subprocess | Proprietary + PSF-2.0 + GPL-2.0-or-later (subprocess) | no |
| `s11.multimodal` | local vLLM HTTP adapter + pinned model revision | Apache-2.0 | adapter yes; weights out-of-process |

CVE floors are recorded in the inventory (`USN-8400-1` for Poppler; Firefox 154.0 / MFSA 2026-74). `latest` is absent. Owner waivers: none.
