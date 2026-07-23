from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import EvidenceFragment, SourceRecord
from ..ingestion.contracts import IngestionResult, IngestionRun


@runtime_checkable
class SourceRepository(Protocol):
    def register(self, source: SourceRecord) -> SourceRecord: ...

    def get(self, source_id: str) -> SourceRecord: ...

    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]: ...

    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]: ...

    def create_run(self, run: IngestionRun) -> IngestionRun: ...

    def get_run(self, run_id: str) -> IngestionRun: ...

    def start_run(self, run_id: str) -> IngestionRun: ...

    def complete_run(self, run_id: str, result: IngestionResult) -> IngestionRun: ...
