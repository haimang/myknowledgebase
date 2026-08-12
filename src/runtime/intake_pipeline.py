"""Compatibility shim: implementation lives in :mod:`src.runtime.intake`.

Prefer ``from src.runtime.intake import IntakePipeline``.  This module remains
so existing composition roots and tests keep a stable import path.
"""

from src.runtime.intake import IntakePipeline

__all__ = ["IntakePipeline"]
