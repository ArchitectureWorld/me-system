from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re
from time import perf_counter
from typing import Callable
from uuid import uuid4

from sqlalchemy import inspect

from ..contracts import (
    AuthorityLevel,
    CandidateGraphChange,
    ChangeOperation,
    ConfirmationStatus,
    GraphEdge,
    GraphNamespace,
    GraphNode,
    ReviewStatus,
    Sensitivity,
    TemporalStatus,
)
from ..errors import GraphObjectNotFoundError
from ..evidence.contracts import EvidenceFragment, FragmentType, SourceRecord
from ..fixtures import load_graph_fixture
from ..ingestion.contracts import (
    CandidateRecord,
    IngestionResult,
    IngestionRun,
    IngestionStatus,
    candidate_payload_sha256,
)
from ..ingestion.review import PersistentReviewService
from ..persistence.candidate_repository import SqlAlchemyCandidateRepository
from ..persistence.database import create_database_engine
from ..persistence.migrations import upgrade_database
from ..persistence.source_repository import SqlAlchemySourceRepository
from ..persistence.store import SqlAlchemyGraphStore
from ..query import GraphQueryService
from .contracts import AcceptanceCheck, AcceptanceReport, CheckStatus


PROJECT_ID = "brain:project:lighting-platform"
USER_ID = "who:user:master"
CURRENT_DECISION_ID = "brain:decision:radiance-primary"
SUPERSEDED_DECISION_ID = "brain:decision:cycles-primary"
SOURCE_TEXT = "用户要求：向后继续深度推进，交付“小白一键体验验收”。"
_REQUIRED_TABLES = {
    "graph_objects",
    "graph_evidence_refs",
    "source_records",
    "evidence_fragments",
    "ingestion_runs",
    "candidate_graph_changes",
    "candidate_evidence_refs",
    "candidate_review_events",
    "alembic_version",
}
_DATABASE_URL_RE = re.compile(
    r"(?:postgresql(?:\+psycopg)?|sqlite(?:\+pysqlite)?):\/\/\S+",
    re.IGNORECASE,
)


class _SkipStep(RuntimeError):
    pass


def _package_version() -> str:
    try:
        return version("me-system")
    except PackageNotFoundError:
        return "0.1.0"


def _safe_error(exc: Exception, database_url: str) -> str:
    text = str(exc).strip() or type(exc).__name__
    text = text.replace(database_url, "[database-url-redacted]")
    text = _DATABASE_URL_RE.sub("[database-url-redacted]", text)
    text = text.replace("Traceback", "错误详情")
    return text[:320]


def _candidate_record(
    change: CandidateGraphChange,
    *,
    idempotency_key: str,
    ingestion_run_id: str,
    created_at: datetime,
) -> CandidateRecord:
    return CandidateRecord(
        change=change,
        idempotency_key=idempotency_key,
        payload_sha256=candidate_payload_sha256(change.payload),
        created_at=created_at,
        reviewed_at=None,
        approved_object_id=None,
        ingestion_run_id=ingestion_run_id,
    )


def _run_check(
    check_id: str,
    title: str,
    action: Callable[[], tuple[str, dict[str, object]]],
    *,
    database_url: str,
) -> AcceptanceCheck:
    started = perf_counter()
    try:
        summary, evidence = action()
        return AcceptanceCheck(
            check_id=check_id,
            title=title,
            status=CheckStatus.PASS,
            summary=summary,
            evidence=evidence,
            duration_ms=max(0, int(round((perf_counter() - started) * 1000))),
        )
    except _SkipStep as exc:
        return AcceptanceCheck(
            check_id=check_id,
            title=title,
            status=CheckStatus.SKIPPED,
            summary=str(exc),
            evidence={},
            duration_ms=max(0, int(round((perf_counter() - started) * 1000))),
        )
    except Exception as exc:  # The dashboard must survive and explain a failed stage.
        return AcceptanceCheck(
            check_id=check_id,
            title=title,
            status=CheckStatus.FAIL,
            summary="该阶段未通过，后续依赖项可能被跳过。",
            evidence={},
            duration_ms=max(0, int(round((perf_counter() - started) * 1000))),
            error_type=type(exc).__name__,
            error_message=_safe_error(exc, database_url),
        )


def run_acceptance(
    database_url: str,
    fixture_path: Path,
    *,
    include_mcp: bool = True,
    allow_test_database: bool = False,
) -> AcceptanceReport:
    """Run a real, repeatable Source → Candidate → dual-graph → MCP acceptance flow."""

    started_at = datetime.now(timezone.utc)
    token = uuid4().hex[:8]
    run_id = f"experience:{token}"
    state: dict[str, object] = {
        "token": token,
        "run_id": run_id,
        "fixture_path": Path(fixture_path),
    }
    checks: list[AcceptanceCheck] = []

    def database_step() -> tuple[str, dict[str, object]]:
        production = not allow_test_database
        upgrade_database(database_url, production=production)
        engine = create_database_engine(database_url, production=production)
        tables = set(inspect(engine).get_table_names())
        missing = sorted(_REQUIRED_TABLES - tables)
        if missing:
            raise RuntimeError(f"数据库缺少表：{', '.join(missing)}")
        state["engine"] = engine
        state["store"] = SqlAlchemyGraphStore(engine)
        state["source_repository"] = SqlAlchemySourceRepository(engine)
        state["candidate_repository"] = SqlAlchemyCandidateRepository(engine)
        state["review_service"] = PersistentReviewService(engine)
        state["query"] = GraphQueryService(state["store"])
        return "PostgreSQL/SQLite Schema 已升级到当前版本。", {
            "required_table_count": len(_REQUIRED_TABLES),
            "tables": sorted(tables),
        }

    checks.append(
        _run_check(
            "database",
            "数据库与迁移",
            database_step,
            database_url=database_url,
        )
    )

    def baseline_step() -> tuple[str, dict[str, object]]:
        store = state.get("store")
        query = state.get("query")
        if not isinstance(store, SqlAlchemyGraphStore) or not isinstance(query, GraphQueryService):
            raise _SkipStep("数据库阶段失败，无法导入基线图谱。")
        try:
            store.get_node(PROJECT_ID)
            fixture_action = "verified-existing"
        except GraphObjectNotFoundError:
            load_graph_fixture(Path(state["fixture_path"]), store)
            fixture_action = "imported"
        snapshot = query.get_project_snapshot(PROJECT_ID)
        node_ids = {node.id for node in snapshot.nodes}
        if CURRENT_DECISION_ID not in node_ids:
            raise RuntimeError("当前 Radiance 决策没有出现在项目快照中")
        if SUPERSEDED_DECISION_ID in node_ids:
            raise RuntimeError("已淘汰的 Cycles 决策错误地出现在当前快照中")
        state["baseline_snapshot"] = snapshot
        return "照明平台基线可查询，当前与历史决策区分正确。", {
            "fixture_action": fixture_action,
            "project_id": PROJECT_ID,
            "current_decision": CURRENT_DECISION_ID,
            "excluded_superseded": list(snapshot.excluded["superseded"]),
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
        }

    checks.append(
        _run_check(
            "baseline_graph",
            "双图谱基线",
            baseline_step,
            database_url=database_url,
        )
    )

    def source_step() -> tuple[str, dict[str, object]]:
        repository = state.get("source_repository")
        engine = state.get("engine")
        if not isinstance(repository, SqlAlchemySourceRepository) or engine is None:
            raise _SkipStep("数据库阶段失败，无法保存来源与证据。")
        now = datetime.now(timezone.utc)
        source_id = f"src:experience:{token}"
        fragment_id = f"fragment:experience:{token}:requirement"
        digest = hashlib.sha256(SOURCE_TEXT.encode("utf-8")).hexdigest()
        source = SourceRecord(
            source_id=source_id,
            source_type="conversation",
            external_system="me-system-experience",
            external_id=run_id,
            idempotency_key=f"experience-source:{token}",
            content_ref=f"experience://{run_id}",
            content_sha256=digest,
            media_type="text/plain",
            occurred_at=now,
            ingested_at=now,
            sensitivity=Sensitivity.PROJECT_PRIVATE,
            metadata={"purpose": "novice_one_click_acceptance"},
        )
        fragment = EvidenceFragment(
            fragment_id=fragment_id,
            source_id=source_id,
            ordinal=0,
            fragment_type=FragmentType.CONVERSATION_MESSAGE,
            text_content=SOURCE_TEXT,
            source_anchor={
                "type": "conversation_message",
                "value": {"conversation_id": run_id, "message_id": "requirement"},
            },
            content_sha256=digest,
            occurred_at=now,
            actor_id=USER_ID,
            metadata={"language": "zh-CN"},
        )
        repository.register(source)
        repository.add_fragments(source_id, (fragment,))
        recreated = SqlAlchemySourceRepository(engine)
        persisted = recreated.get(source_id)
        fragments = recreated.list_fragments(source_id)
        if persisted != source or fragments != (fragment,):
            raise RuntimeError("来源或证据片段在 Repository 重建后不一致")
        state["source"] = source
        state["fragment"] = fragment
        state["evidence_ref"] = fragment.to_evidence_ref(
            document_id=f"doc:experience:{token}",
            version_id="1",
        )
        return "用户要求已保存为不可变来源和可寻址证据片段。", {
            "source_id": source_id,
            "fragment_id": fragment_id,
            "content_sha256": digest,
            "text": SOURCE_TEXT,
        }

    checks.append(
        _run_check(
            "source_evidence",
            "来源与证据",
            source_step,
            database_url=database_url,
        )
    )

    def ingestion_step() -> tuple[str, dict[str, object]]:
        repository = state.get("source_repository")
        source = state.get("source")
        if not isinstance(repository, SqlAlchemySourceRepository) or not isinstance(source, SourceRecord):
            raise _SkipStep("来源阶段失败，无法记录摄取状态。")
        now = datetime.now(timezone.utc)
        ingestion_run_id = f"ingestion:experience:{token}"
        pending = IngestionRun.new(
            run_id=ingestion_run_id,
            source_id=source.source_id,
            adapter_name="one-click-experience",
            adapter_version="1.0.0",
            started_at=now,
            input_item_count=1,
        )
        repository.create_run(pending)
        repository.start_run(ingestion_run_id)
        completed = repository.complete_run(
            ingestion_run_id,
            IngestionResult(
                status=IngestionStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                processed_item_count=1,
                skipped_item_count=0,
                failed_item_count=0,
                fragment_count=1,
                candidate_count=4,
                coverage_ratio=1.0,
                quality_report={"warnings": [], "ambiguities": []},
                log_ref=f"experience://{run_id}/ingestion",
                error_summary=None,
            ),
        )
        if completed.status is not IngestionStatus.COMPLETED or completed.coverage_ratio != 1.0:
            raise RuntimeError("摄取运行没有完整完成")
        state["ingestion_run"] = completed
        return "摄取运行完成，覆盖率为 100%。", completed.to_dict()

    checks.append(
        _run_check(
            "ingestion",
            "摄取状态与覆盖率",
            ingestion_step,
            database_url=database_url,
        )
    )

    def brain_step() -> tuple[str, dict[str, object]]:
        candidate_repository = state.get("candidate_repository")
        review_service = state.get("review_service")
        query = state.get("query")
        ingestion_run = state.get("ingestion_run")
        evidence_ref = state.get("evidence_ref")
        if not isinstance(candidate_repository, SqlAlchemyCandidateRepository):
            raise _SkipStep("数据库阶段失败，无法提交 ME-Brain Candidate。")
        if not isinstance(review_service, PersistentReviewService) or not isinstance(query, GraphQueryService):
            raise _SkipStep("审核服务不可用。")
        if not isinstance(ingestion_run, IngestionRun) or evidence_ref is None:
            raise _SkipStep("摄取或证据阶段失败，无法建立 Candidate。")
        now = datetime.now(timezone.utc)
        task_id = f"brain:task:one-click-acceptance-{token}"
        edge_id = f"edge:project-has-one-click-acceptance-{token}"
        task = GraphNode(
            id=task_id,
            graph=GraphNamespace.ME_BRAIN,
            type="Task",
            label="小白一键体验验收",
            properties={"status": "accepted", "experience_run_id": run_id},
            authority=AuthorityLevel.CANDIDATE,
            confirmation_status=ConfirmationStatus.PENDING,
            status=TemporalStatus.CURRENT,
            valid_from=now,
            valid_to=None,
            sensitivity=Sensitivity.PROJECT_PRIVATE,
            source_refs=(evidence_ref,),
        )
        task_edge = GraphEdge(
            id=edge_id,
            graph=GraphNamespace.ME_BRAIN,
            type="HAS_TASK",
            from_id=PROJECT_ID,
            to_id=task_id,
            properties={"experience_run_id": run_id},
            authority=AuthorityLevel.CANDIDATE,
            confirmation_status=ConfirmationStatus.PENDING,
            confidence=1.0,
            valid_from=now,
            valid_to=None,
            sensitivity=Sensitivity.PROJECT_PRIVATE,
            source_refs=(evidence_ref,),
        )
        task_change = CandidateGraphChange(
            change_id=f"candidate:experience:{token}:brain-task",
            target_graph=GraphNamespace.ME_BRAIN,
            operation=ChangeOperation.ADD_NODE,
            submitted_by="adapter:one-click-experience",
            reason="用户要求提供小白一键体验验收",
            evidence_refs=(evidence_ref,),
            payload=task.to_dict(),
            review_status=ReviewStatus.PENDING,
        )
        edge_change = CandidateGraphChange(
            change_id=f"candidate:experience:{token}:brain-edge",
            target_graph=GraphNamespace.ME_BRAIN,
            operation=ChangeOperation.ADD_EDGE,
            submitted_by="adapter:one-click-experience",
            reason="将验收任务连接到体验项目",
            evidence_refs=(evidence_ref,),
            payload=task_edge.to_dict(),
            review_status=ReviewStatus.PENDING,
        )
        task_record = candidate_repository.submit(
            _candidate_record(
                task_change,
                idempotency_key=f"experience:{token}:brain-task",
                ingestion_run_id=ingestion_run.run_id,
                created_at=now,
            )
        )
        edge_record = candidate_repository.submit(
            _candidate_record(
                edge_change,
                idempotency_key=f"experience:{token}:brain-edge",
                ingestion_run_id=ingestion_run.run_id,
                created_at=now,
            )
        )
        approved_task = review_service.approve(
            task_record.change.change_id,
            "human:experience-reviewer",
            reason="一键体验自动验收批准",
        )
        approved_edge = review_service.approve(
            edge_record.change.change_id,
            "human:experience-reviewer",
            reason="一键体验自动验收批准",
        )
        snapshot = query.get_project_snapshot(PROJECT_ID)
        if task_id not in {node.id for node in snapshot.nodes}:
            raise RuntimeError("已批准的体验任务没有出现在项目快照中")
        state["brain_task_id"] = task_id
        state["brain_edge_id"] = edge_id
        state["brain_snapshot"] = snapshot
        return "ME-Brain Task 与 HAS_TASK 已在同一治理链中批准并可查询。", {
            "task_id": approved_task.id,
            "edge_id": approved_edge.id,
            "snapshot_node_count": len(snapshot.nodes),
            "snapshot_edge_count": len(snapshot.edges),
            "review_events": [
                event.to_dict()
                for event in candidate_repository.list_events(task_change.change_id)
            ],
        }

    checks.append(
        _run_check(
            "brain_review",
            "ME-Brain Candidate 审核",
            brain_step,
            database_url=database_url,
        )
    )

    def who_step() -> tuple[str, dict[str, object]]:
        candidate_repository = state.get("candidate_repository")
        review_service = state.get("review_service")
        query = state.get("query")
        ingestion_run = state.get("ingestion_run")
        evidence_ref = state.get("evidence_ref")
        if not isinstance(candidate_repository, SqlAlchemyCandidateRepository):
            raise _SkipStep("数据库阶段失败，无法提交 ME-Who Candidate。")
        if not isinstance(review_service, PersistentReviewService) or not isinstance(query, GraphQueryService):
            raise _SkipStep("审核服务不可用。")
        if not isinstance(ingestion_run, IngestionRun) or evidence_ref is None:
            raise _SkipStep("摄取或证据阶段失败，无法建立 Candidate。")
        now = datetime.now(timezone.utc)
        rule_id = f"who:collaboration-rule:one-click-{token}"
        edge_id = f"edge:user-has-one-click-rule-{token}"
        rule = GraphNode(
            id=rule_id,
            graph=GraphNamespace.ME_WHO,
            type="CollaborationRule",
            label="明确的一键验收任务直接执行并返回可视化结果",
            properties={
                "task_types": ["experience_acceptance"],
                "project_ids": [PROJECT_ID],
                "experience_run_id": run_id,
            },
            authority=AuthorityLevel.CANDIDATE,
            confirmation_status=ConfirmationStatus.PENDING,
            status=TemporalStatus.CURRENT,
            valid_from=now,
            valid_to=None,
            sensitivity=Sensitivity.PERSONAL_PRIVATE,
            source_refs=(evidence_ref,),
        )
        rule_edge = GraphEdge(
            id=edge_id,
            graph=GraphNamespace.ME_WHO,
            type="HAS_COLLABORATION_RULE",
            from_id=USER_ID,
            to_id=rule_id,
            properties={"experience_run_id": run_id},
            authority=AuthorityLevel.CANDIDATE,
            confirmation_status=ConfirmationStatus.PENDING,
            confidence=1.0,
            valid_from=now,
            valid_to=None,
            sensitivity=Sensitivity.PERSONAL_PRIVATE,
            source_refs=(evidence_ref,),
        )
        rule_change = CandidateGraphChange(
            change_id=f"candidate:experience:{token}:who-rule",
            target_graph=GraphNamespace.ME_WHO,
            operation=ChangeOperation.ADD_NODE,
            submitted_by="adapter:one-click-experience",
            reason="记录当前任务适用的协作规则",
            evidence_refs=(evidence_ref,),
            payload=rule.to_dict(),
            review_status=ReviewStatus.PENDING,
        )
        edge_change = CandidateGraphChange(
            change_id=f"candidate:experience:{token}:who-edge",
            target_graph=GraphNamespace.ME_WHO,
            operation=ChangeOperation.ADD_EDGE,
            submitted_by="adapter:one-click-experience",
            reason="将协作规则连接到体验用户",
            evidence_refs=(evidence_ref,),
            payload=rule_edge.to_dict(),
            review_status=ReviewStatus.PENDING,
        )
        rule_record = candidate_repository.submit(
            _candidate_record(
                rule_change,
                idempotency_key=f"experience:{token}:who-rule",
                ingestion_run_id=ingestion_run.run_id,
                created_at=now,
            )
        )
        edge_record = candidate_repository.submit(
            _candidate_record(
                edge_change,
                idempotency_key=f"experience:{token}:who-edge",
                ingestion_run_id=ingestion_run.run_id,
                created_at=now,
            )
        )
        approved_rule = review_service.approve(
            rule_record.change.change_id,
            "human:experience-reviewer",
            reason="一键体验自动验收批准",
        )
        approved_edge = review_service.approve(
            edge_record.change.change_id,
            "human:experience-reviewer",
            reason="一键体验自动验收批准",
        )
        profile = query.get_task_profile(USER_ID, PROJECT_ID, "experience_acceptance")
        if rule_id not in {node.id for node in profile.nodes}:
            raise RuntimeError("已批准的一键协作规则没有出现在任务画像中")
        state["who_rule_id"] = rule_id
        state["who_edge_id"] = edge_id
        state["who_profile"] = profile
        return "ME-Who CollaborationRule 与关系已批准并按任务范围返回。", {
            "rule_id": approved_rule.id,
            "edge_id": approved_edge.id,
            "profile_node_count": len(profile.nodes),
            "profile_edge_count": len(profile.edges),
            "review_events": [
                event.to_dict()
                for event in candidate_repository.list_events(rule_change.change_id)
            ],
        }

    checks.append(
        _run_check(
            "who_review",
            "ME-Who Candidate 审核",
            who_step,
            database_url=database_url,
        )
    )

    def evidence_step() -> tuple[str, dict[str, object]]:
        engine = state.get("engine")
        query = state.get("query")
        fragment = state.get("fragment")
        brain_task_id = state.get("brain_task_id")
        if engine is None or not isinstance(query, GraphQueryService):
            raise _SkipStep("查询服务不可用，无法回溯证据。")
        if not isinstance(fragment, EvidenceFragment) or not isinstance(brain_task_id, str):
            raise _SkipStep("来源或 ME-Brain 审核失败，无法回溯证据。")
        refs = query.get_evidence(brain_task_id)
        fragment_ids = {ref.content_fragment_id for ref in refs}
        if fragment.fragment_id not in fragment_ids:
            raise RuntimeError("权威任务没有保留 EvidenceFragment 引用")
        recreated = SqlAlchemySourceRepository(engine)
        persisted = recreated.list_fragments(fragment.source_id)
        matched = [item for item in persisted if item.fragment_id == fragment.fragment_id]
        if not matched or matched[0].text_content != SOURCE_TEXT:
            raise RuntimeError("EvidenceRef 无法返回原始证据正文")
        return "权威图谱对象可沿 EvidenceRef 回到用户原始要求。", {
            "object_id": brain_task_id,
            "source_id": fragment.source_id,
            "fragment_id": fragment.fragment_id,
            "source_anchor": dict(fragment.source_anchor),
            "text": matched[0].text_content,
        }

    checks.append(
        _run_check(
            "evidence_trace",
            "证据回溯",
            evidence_step,
            database_url=database_url,
        )
    )

    def mcp_step() -> tuple[str, dict[str, object]]:
        if not include_mcp:
            raise _SkipStep("当前运行关闭了 stdio MCP 检查。")
        brain_task_id = state.get("brain_task_id")
        who_rule_id = state.get("who_rule_id")
        if not isinstance(brain_task_id, str) or not isinstance(who_rule_id, str):
            raise _SkipStep("双图谱审核未完成，无法执行 MCP 检查。")
        from .mcp_check import run_mcp_check

        evidence = run_mcp_check(database_url, brain_task_id, who_rule_id)
        state["mcp"] = evidence
        return "真实 stdio MCP Client 已查询到本次 Brain Task 与 Who Rule。", evidence

    checks.append(
        _run_check(
            "mcp",
            "stdio MCP 端到端",
            mcp_step,
            database_url=database_url,
        )
    )

    completed_at = datetime.now(timezone.utc)
    baseline_snapshot = state.get("baseline_snapshot")
    brain_snapshot = state.get("brain_snapshot")
    who_profile = state.get("who_profile")
    mcp_evidence = state.get("mcp")
    return AcceptanceReport(
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        checks=tuple(checks),
        highlights={
            "current_engine": "Radiance",
            "brain_task": "小白一键体验验收",
            "collaboration_rule": "明确的一键验收任务直接执行并返回可视化结果",
            "project_nodes": len(brain_snapshot.nodes) if brain_snapshot is not None else 0,
            "profile_nodes": len(who_profile.nodes) if who_profile is not None else 0,
        },
        technical={
            "source_id": getattr(state.get("source"), "source_id", None),
            "fragment_id": getattr(state.get("fragment"), "fragment_id", None),
            "ingestion_run_id": getattr(state.get("ingestion_run"), "run_id", None),
            "brain_task_id": state.get("brain_task_id"),
            "brain_edge_id": state.get("brain_edge_id"),
            "who_rule_id": state.get("who_rule_id"),
            "who_edge_id": state.get("who_edge_id"),
            "baseline_node_count": len(baseline_snapshot.nodes) if baseline_snapshot is not None else 0,
            "tool_names": (
                list(mcp_evidence.get("tool_names", []))
                if isinstance(mcp_evidence, dict)
                else []
            ),
        },
        version=_package_version(),
    )
