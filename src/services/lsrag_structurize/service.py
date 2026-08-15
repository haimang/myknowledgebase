"""S06 structurize leaf facade.  No I/O, no adapters."""

from __future__ import annotations

from src.services.lsrag_compiler import LsragContractCompiler
from src.services.lsrag_structurize.admit import StructurizeAdmitResult, admit_structurize
from src.services.lsrag_structurize.binder import StructurizeBinding


class LsragStructurizeService:
    """Admit a bound layered candidate into S06 structure artifacts."""

    def __init__(self, compiler: LsragContractCompiler | None = None) -> None:
        self._compiler = compiler or LsragContractCompiler()

    def admit(self, binding: StructurizeBinding) -> StructurizeAdmitResult:
        return admit_structurize(binding, compiler=self._compiler)
