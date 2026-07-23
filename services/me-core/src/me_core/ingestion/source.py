from __future__ import annotations

from typing import Protocol

from .contracts import EvidenceFragment, SourceRecord


class SourceLedgerRepository(Protocol):
    def register_source(self, source: SourceRecord) -> SourceRecord: ...

    def get_source(self, source_id: str) -> SourceRecord: ...

    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]: ...

    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]: ...


class SourceLedgerService:
    """Application service for immutable sources and addressable evidence."""

    def __init__(self, repository: SourceLedgerRepository) -> None:
        self._repository = repository

    def register_source(self, source: SourceRecord) -> SourceRecord:
        return self._repository.register_source(source)

    def get_source(self, source_id: str) -> SourceRecord:
        return self._repository.get_source(source_id)

    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]:
        return self._repository.add_fragments(source_id, fragments)

    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]:
        return self._repository.list_fragments(source_id)
