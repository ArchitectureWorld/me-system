from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts import GraphNamespace
from .contracts import CandidateRecord, ReviewEvent


@runtime_checkable
class CandidateRepository(Protocol):
    def submit(self, candidate: CandidateRecord) -> CandidateRecord: ...

    def get(self, change_id: str) -> CandidateRecord: ...

    def list_pending(
        self,
        *,
        target_graph: GraphNamespace | None = None,
        source_id: str | None = None,
        limit: int = 100,
    ) -> tuple[CandidateRecord, ...]: ...

    def list_events(self, change_id: str) -> tuple[ReviewEvent, ...]: ...
