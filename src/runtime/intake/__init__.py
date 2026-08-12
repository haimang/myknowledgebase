"""Single-intake LS-RAG process stage package.

Semantic split (thin entry + mixins):

- :mod:`src.runtime.intake.pipeline` — public ``IntakePipeline`` composition
- :mod:`src.runtime.intake.types` — shared dataclasses and pure helpers
- stage mixins: acquisition, clean_preflight, acceptance, generation,
  vector_publish, index_rebuild, core
"""

from src.runtime.intake.pipeline import IntakePipeline

__all__ = ["IntakePipeline"]
