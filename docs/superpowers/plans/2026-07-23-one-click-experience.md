# 小白一键体验验收 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让只安装 Docker Desktop 的用户通过一次双击，在浏览器中完成 ME-System 的真实 PostgreSQL、双图谱、Candidate 审核和 stdio MCP 验收。

**Architecture:** 使用 Docker Compose 启动隔离的 PostgreSQL 16 和一个无外部 Web 框架的 Python 验收服务。服务通过现有 Repository、ReviewService、QueryService 和 MCP ClientSession 执行真实链路，再将结构化报告渲染为本地 HTML。

**Tech Stack:** Python 3.11/3.12、SQLAlchemy 2、Alembic、PostgreSQL 16、MCP Python SDK、Docker Compose、Python 标准库 HTTP Server。

## Global Constraints

- Docker Desktop 是体验者唯一外部依赖。
- 只有 ME-Brain 与 ME-Who 两个权威图谱领域。
- PostgreSQL 仍是唯一权威数据库。
- Candidate 管理能力不加入 MCP。
- PostgreSQL 不向宿主机暴露端口。
- 页面和错误不得显示密码、数据库完整 URL 或 traceback。
- 任何生产代码必须先有失败测试。

---

### Task 1: 验收报告契约与渲染

**Files:**
- Create: `tests/test_experience_contracts.py`
- Create: `src/me_system/experience/__init__.py`
- Create: `src/me_system/experience/contracts.py`
- Create: `src/me_system/experience/renderer.py`

**Interfaces:**
- Produces: `AcceptanceCheck`, `AcceptanceReport`, `render_report_html(report)`。

- [ ] **Step 1: 写失败测试**

测试成功报告、失败报告、HTML 转义、中文状态和 JSON 往返。

- [ ] **Step 2: 运行 RED**

```bash
pytest -q tests/test_experience_contracts.py
```

Expected: FAIL because `me_system.experience` does not exist.

- [ ] **Step 3: 实现最小契约与渲染器**

`AcceptanceCheck` 字段：

```text
check_id, title, status, summary, evidence, duration_ms, error_type, error_message
```

`AcceptanceReport` 字段：

```text
run_id, started_at, completed_at, checks, highlights, technical, version
```

总状态由 checks 自动计算，不允许调用者伪造。

- [ ] **Step 4: 运行 GREEN**

```bash
pytest -q tests/test_experience_contracts.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_experience_contracts.py src/me_system/experience
git commit -m "feat: add one-click acceptance report contracts"
```

### Task 2: 核心验收 Runner

**Files:**
- Create: `tests/test_experience_runner.py`
- Create: `src/me_system/experience/runner.py`

**Interfaces:**
- Consumes: `SqlAlchemySourceRepository`, `SqlAlchemyCandidateRepository`, `PersistentReviewService`, `SqlAlchemyGraphStore`, `GraphQueryService`。
- Produces: `run_acceptance(database_url, fixture_path, include_mcp=False) -> AcceptanceReport`。

- [ ] **Step 1: 写失败测试**

使用 SQLite 文件数据库验证：

1. Fixture 导入；
2. Source / Fragment / Run；
3. Brain Task + HAS_TASK；
4. Who CollaborationRule + HAS_COLLABORATION_RULE；
5. Snapshot、TaskProfile 和 Evidence 回溯；
6. 第二次运行生成新对象且仍成功。

- [ ] **Step 2: 运行 RED**

```bash
pytest -q tests/test_experience_runner.py
```

Expected: FAIL because `run_acceptance` is missing.

- [ ] **Step 3: 实现 Runner**

每个阶段使用独立计时包装器，异常转成失败检查后继续形成报告。ID 使用 `uuid4().hex[:8]`，所有对象 ID 带运行 token。

- [ ] **Step 4: 运行 GREEN**

```bash
pytest -q tests/test_experience_runner.py
```

Expected: PASS with eight core checks excluding MCP represented as skipped only when `include_mcp=False`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_experience_runner.py src/me_system/experience/runner.py
git commit -m "feat: run deterministic dual-graph acceptance flow"
```

### Task 3: 真实 stdio MCP 验收

**Files:**
- Create: `tests/test_experience_mcp.py`
- Create: `src/me_system/experience/mcp_check.py`

**Interfaces:**
- Produces: `run_mcp_check(database_url, brain_task_id, who_rule_id) -> dict[str, object]`。

- [ ] **Step 1: 写协议级测试**

测试工具名常量严格等于六个只读工具，并验证结果检查函数会拒绝缺失 Brain Task 或 Who Rule 的响应。

- [ ] **Step 2: 运行 RED**

```bash
pytest -q tests/test_experience_mcp.py
```

Expected: FAIL because MCP check module is missing.

- [ ] **Step 3: 实现真实 ClientSession**

通过 `StdioServerParameters` 启动 `sys.executable -m me_system.hermes.mcp_server`，调用：

```text
list_tools
brain_get_snapshot
who_get_task_profile
```

环境固定为体验项目和用户，不继承未授权项目列表。

- [ ] **Step 4: 运行 GREEN**

```bash
pytest -q tests/test_experience_mcp.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_experience_mcp.py src/me_system/experience/mcp_check.py
git commit -m "feat: verify one-click experience through real stdio MCP"
```

### Task 4: 本地验收 Web 服务

**Files:**
- Create: `tests/test_experience_server.py`
- Create: `src/me_system/experience/server.py`
- Create: `src/me_system/experience/__main__.py`

**Interfaces:**
- Produces: HTTP `GET /`, `GET /healthz`, `GET /api/report`, `POST /api/run`。

- [ ] **Step 1: 写失败测试**

用临时端口启动服务器，验证健康检查、JSON 报告、HTML、重新运行和不支持路径的 404。

- [ ] **Step 2: 运行 RED**

```bash
pytest -q tests/test_experience_server.py
```

Expected: FAIL because server module is missing.

- [ ] **Step 3: 实现 ThreadingHTTPServer**

服务器启动时先执行一次验收；`POST /api/run` 在互斥锁内重新执行；响应禁止缓存；错误只返回脱敏摘要。

- [ ] **Step 4: 运行 GREEN**

```bash
pytest -q tests/test_experience_server.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_experience_server.py src/me_system/experience
git commit -m "feat: serve one-click acceptance dashboard"
```

### Task 5: Docker Compose 与跨平台一键入口

**Files:**
- Create: `tests/test_experience_distribution.py`
- Create: `deploy/experience/Dockerfile`
- Create: `deploy/experience/compose.yml`
- Create: `体验.sh`
- Create: `体验.command`
- Create: `体验.bat`
- Create: `停止体验.sh`
- Create: `停止体验.bat`
- Create: `.dockerignore`

**Interfaces:**
- Produces: `http://localhost:8765`。

- [ ] **Step 1: 写失败测试**

静态检查 Compose 只映射 `8765:8765`、PostgreSQL 无 `ports`、三个启动脚本使用同一 Compose 文件、Dockerfile 启动 `me_system.experience`。

- [ ] **Step 2: 运行 RED**

```bash
pytest -q tests/test_experience_distribution.py
```

Expected: FAIL because distribution files are missing.

- [ ] **Step 3: 实现容器与脚本**

脚本在 Docker 不可用时给出中文动作提示；等待 120 秒；成功后打开浏览器；失败时输出 `docker compose logs --tail=120 experience` 提示。

- [ ] **Step 4: 运行 GREEN**

```bash
pytest -q tests/test_experience_distribution.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add deploy/experience .dockerignore 体验.sh 体验.command 体验.bat 停止体验.sh 停止体验.bat tests/test_experience_distribution.py
git commit -m "feat: add Docker-only one-click experience launchers"
```

### Task 6: PostgreSQL 一键验收 E2E 与 CI

**Files:**
- Create: `tests/test_experience_postgres_e2e.py`
- Modify: `.github/workflows/me-system.yml`

**Interfaces:**
- Consumes: `run_acceptance(..., include_mcp=True)`。

- [ ] **Step 1: 写 PostgreSQL 测试**

测试从空 Schema 开始，断言八项全部通过、总状态 PASS、MCP 工具严格为六个。

- [ ] **Step 2: 运行或提交 RED**

```bash
ME_GRAPH_TEST_POSTGRES_URL='postgresql+psycopg://...' \
pytest -q tests/test_experience_postgres_e2e.py
```

Expected before wiring: FAIL because MCP integration is not included in runner.

- [ ] **Step 3: 接入 Runner 与 CI**

PostgreSQL Job 同时运行：

```text
test_postgres_integration.py
test_ingestion_postgres_e2e.py
test_experience_postgres_e2e.py
test_mcp_stdio.py
```

- [ ] **Step 4: 运行 GREEN**

Expected: all PostgreSQL and stdio MCP E2E tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_experience_postgres_e2e.py .github/workflows/me-system.yml src/me_system/experience
git commit -m "test: validate Docker experience against PostgreSQL and MCP"
```

### Task 7: 小白文档入口

**Files:**
- Modify: `README.md`
- Create: `docs/experience.md`

- [ ] **Step 1: 写文档断言**

扩展 `tests/test_experience_distribution.py`，要求 README 首个主要章节出现“小白一键体验”，并列出 Windows、macOS、Linux 三种入口。

- [ ] **Step 2: 运行 RED**

```bash
pytest -q tests/test_experience_distribution.py
```

Expected: FAIL because README lacks the required entry.

- [ ] **Step 3: 写用户文档**

README 只给三步：安装 Docker Desktop、下载仓库、双击入口。高级排错放到 `docs/experience.md`。

- [ ] **Step 4: 运行 GREEN 与全量测试**

```bash
pytest -q
python -m compileall -q src
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/experience.md tests/test_experience_distribution.py
git commit -m "docs: make one-click acceptance the primary onboarding path"
```

### Task 8: 最终验收与发布

- [ ] **Step 1: 创建 Draft PR 并运行 CI**
- [ ] **Step 2: 检查 Python 3.11、3.12、PostgreSQL 16、stdio MCP 全部成功**
- [ ] **Step 3: 下载测试 Artifact 并确认无跳过的体验验收项**
- [ ] **Step 4: 检查 PR 文件列表中没有第二数据库、写入 MCP 或第三产品命名**
- [ ] **Step 5: 转 Ready 并合并**
