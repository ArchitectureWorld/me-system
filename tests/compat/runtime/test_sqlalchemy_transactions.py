from __future__ import annotations

import pytest

from me_core.contracts import (
    AuthorityLevel,
    ConfirmationStatus,
    EvidenceRef,
    GraphNamespace,
    GraphNode,
    Sensitivity,
    TemporalStatus,
)
from me_core.errors import GraphObjectNotFoundError, GraphStoreUnavailableError
from me_core.persistence import graph_writer as graph_writer_module
from me_core.persistence.models import EvidenceRefRecord, create_schema
from me_core.persistence.store import SqlAlchemyGraphStore
from me_core.persistence.testing import create_sqlite_test_engine


def test_failed_evidence_write_rolls_back_graph_object(monkeypatch) -> None:
    engine = create_sqlite_test_engine()
    create_schema(engine)
    store = SqlAlchemyGraphStore(engine)
    ref = EvidenceRef(
        source_id="src:rollback",
        source_anchor={"type": "fixture", "value": {"id": "rollback"}},
    )
    value = GraphNode(
        id="brain:project:rollback",
        graph=GraphNamespace.ME_BRAIN,
        type="Project",
        label="rollback",
        properties={},
        authority=AuthorityLevel.CANONICAL,
        confirmation_status=ConfirmationStatus.HUMAN_CONFIRMED,
        status=TemporalStatus.CURRENT,
        valid_from=None,
        valid_to=None,
        sensitivity=Sensitivity.PROJECT_PRIVATE,
        source_refs=(ref,),
    )

    def duplicate_evidence(object_id: str, refs) -> list[EvidenceRefRecord]:
        evidence = tuple(refs)[0]
        payload = {
            "object_id": object_id,
            "ordinal": 0,
            "source_id": evidence.source_id,
            "document_id": evidence.document_id,
            "version_id": evidence.version_id,
            "content_fragment_id": evidence.content_fragment_id,
            "source_anchor": {
                "type": evidence.source_anchor["type"],
                "value": dict(evidence.source_anchor["value"]),
            },
        }
        return [EvidenceRefRecord(**payload), EvidenceRefRecord(**payload)]

    monkeypatch.setattr(
        graph_writer_module,
        "_evidence_records",
        duplicate_evidence,
    )
    with pytest.raises(GraphStoreUnavailableError):
        store.add_node(value)
    with pytest.raises(GraphObjectNotFoundError):
        store.get_node(value.id)
