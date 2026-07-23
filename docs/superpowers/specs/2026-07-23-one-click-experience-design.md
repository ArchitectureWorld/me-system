# 小白一键体验验收设计

> 状态：Approved for implementation  
> 日期：2026-07-23  
> 目标用户：只会安装并打开 Docker Desktop，不理解 Python、PostgreSQL、MCP 或命令行参数的体验者

## 1. 目标

用户从仓库下载 ZIP 或 clone 后，只执行一次平台对应的启动文件：

```text
Windows：双击 体验.bat
macOS：双击 体验.command
Linux：运行 ./体验.sh
```

系统自动完成：

```text
检查 Docker
→ 构建 ME-System 容器
→ 启动专用 PostgreSQL 16
→ 执行 Alembic 迁移
→ 导入 lighting-platform 示例
→ 登记 Source / Evidence / IngestionRun
→ 提交并批准 ME-Brain 与 ME-Who Candidate
→ 执行双图谱查询
→ 执行真实 stdio MCP Client 验收
→ 打开本地浏览器验收页
```

用户最终只需要判断页面顶部是否显示：

```text
全部通过 · ME-System 一键体验验收成功
```

## 2. 方案比较

### A. 本机 Python + PostgreSQL 安装脚本

优点：镜像小，开发者熟悉。  
缺点：要求用户安装 Python、pip、数据库、环境变量和编译依赖；不符合“小白一键”。  
结论：不采用。

### B. Docker Compose + 内置验收 Web 服务

优点：只依赖 Docker Desktop；数据库隔离；跨平台；能运行真实 PostgreSQL 和 MCP；页面可直接呈现证据。  
缺点：首次构建需要下载镜像。  
结论：采用。

### C. 公网托管演示

优点：无需本地安装。  
缺点：不能证明本地私有部署；增加运维、账号和隐私问题；与 ME-Who 本地优先原则冲突。  
结论：本阶段不采用。

## 3. 用户体验

### 3.1 启动

启动文件必须：

1. 检测 `docker` 与 `docker compose`；
2. 若 Docker 未运行，输出中文可操作错误，不显示堆栈；
3. 启动 `deploy/experience/compose.yml`；
4. 等待 `/healthz` 可用；
5. 自动打开 `http://localhost:8765`；
6. 在终端保留 URL、停止命令和故障排查提示。

### 3.2 验收页

页面分为四层：

1. **最终结论**：通过数量、总耗时、运行编号；
2. **八项验收卡片**：每项显示 PASS / FAIL、中文说明和关键证据；
3. **用户能看懂的成果**：当前项目决策、项目任务、协作规则；
4. **技术证据抽屉**：JSON 报告、节点 ID、关系 ID、EvidenceRef、MCP 工具结果。

页面提供：

- `重新验收`：在同一数据库创建新的运行编号并重新执行，不要求重启容器；
- `下载 JSON 报告`；
- `停止体验` 操作说明。

## 4. 架构

```text
体验.bat / 体验.command / 体验.sh
                  │
                  ▼
       deploy/experience/compose.yml
           ┌──────┴──────┐
           ▼             ▼
     PostgreSQL 16   ME-System Experience
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
       AcceptanceRunner  HTML Server  stdio MCP Client
              │
              ▼
 Source → Evidence → Ingestion → Candidate → Review
              │
       ┌──────┴──────┐
       ▼             ▼
   ME-Brain        ME-Who
```

代码位于：

```text
src/me_system/experience/
├── __init__.py
├── __main__.py
├── contracts.py
├── runner.py
├── mcp_check.py
├── renderer.py
└── server.py
```

每个模块只有一个职责：

- `contracts.py`：验收步骤和报告数据结构；
- `runner.py`：真实业务链执行；
- `mcp_check.py`：真实 stdio MCP 检查；
- `renderer.py`：无模板依赖的 HTML 输出；
- `server.py`：本地 HTTP API 与静态页面；
- `__main__.py`：参数解析和进程入口。

## 5. 验收场景

每次运行生成短 UUID，避免重复运行冲突。

### 5.1 基线图谱

确保 `lighting-platform` Fixture 存在。若项目节点已经存在，则不重复导入；若不存在，则导入完整 Fixture。

必须验证：

- 当前主计算核心是 Radiance；
- 已淘汰的 Cycles 决策不出现在当前快照；
- `brain:project:lighting-platform` 可以查询。

### 5.2 来源与证据

创建包含用户验收要求的来源：

```text
用户要求：向后继续深度推进，交付“小白一键体验验收”。
```

保存：

- `SourceRecord`；
- 一个 `conversation_message` EvidenceFragment；
- 一个完成度为 `1.0` 的 IngestionRun。

### 5.3 ME-Brain Candidate

创建并批准：

- 一个 `Task`：小白一键体验验收；
- 一条 `HAS_TASK`：lighting-platform → Task。

必须验证项目快照中可以看到该 Task，且 Task 可回溯到 EvidenceFragment。

### 5.4 ME-Who Candidate

创建并批准：

- 一个 `CollaborationRule`：明确的一键验收任务直接执行并返回可视化结果；
- 一条 `HAS_COLLABORATION_RULE`：Master → CollaborationRule。

规则限定：

```json
{
  "task_types": ["experience_acceptance"],
  "project_ids": ["brain:project:lighting-platform"]
}
```

必须验证 `who_get_task_profile` 对该任务返回新规则。

### 5.5 MCP

启动真实子进程：

```text
python -m me_system.hermes.mcp_server
```

通过 MCP `ClientSession` 验证：

- 工具列表仍然只有六个只读工具；
- `brain_get_snapshot` 返回新 Task；
- `who_get_task_profile` 返回新 CollaborationRule；
- 未开放 Candidate 写入或审核工具。

## 6. 八项验收门槛

| 编号 | 验收项 | 通过条件 |
|---|---|---|
| 1 | PostgreSQL 与迁移 | Alembic 升级成功，核心表存在 |
| 2 | 基线图谱 | Fixture 可查询，Radiance 当前、Cycles 被排除 |
| 3 | Source / Evidence | 来源和片段跨 Repository 重建后仍存在 |
| 4 | Ingestion 状态 | completed、coverage=1.0、计数一致 |
| 5 | ME-Brain 审核 | Task 与 HAS_TASK 原子批准并出现在快照 |
| 6 | ME-Who 审核 | CollaborationRule 与关系批准并出现在任务画像 |
| 7 | 证据回溯 | 权威节点 EvidenceRef 指向原始片段正文 |
| 8 | MCP 端到端 | 六工具、Brain 与 Who 查询全部成功 |

只要任一项失败，页面总状态必须为 FAIL，HTTP 服务仍继续运行以展示错误。

## 7. 数据隔离与安全

- Compose 使用专用数据库、专用网络和专用 volume；
- 默认端口只暴露验收 Web 的 `8765`，PostgreSQL 不映射到宿主机；
- 数据库密码仅用于本地容器网络；
- 页面不显示数据库 URL、密码或 traceback；
- 错误报告只保存异常类型、脱敏摘要和失败阶段；
- 不读取用户真实 ME-Who 数据；
- 不修改用户已存在的正式数据库。

## 8. 重复运行

`重新验收` 使用新的运行 ID，因此 Source、Candidate 和图谱对象 ID 不冲突。

Fixture 导入使用“存在即验证、缺失才导入”策略。每次运行产生独立：

```text
source_id
fragment_id
run_id
brain task / edge
who rule / edge
review events
```

## 9. 测试

### 单元与 SQLite

- 报告聚合和失败状态；
- HTML 转义与中文渲染；
- 核心验收链在 SQLite 文件数据库运行；
- 重复运行生成不同 ID；
- HTTP `/healthz`、`/api/report` 和 `/api/run`。

### PostgreSQL CI

现有 PostgreSQL Job 增加一项真实验收：

```text
run_acceptance(database_url, include_mcp=True)
```

断言八项全部通过，并确认旧 Hermes E2E 不回归。

### Compose 静态验收

测试读取 Compose、Dockerfile 和三个启动脚本，验证：

- 只暴露 8765；
- PostgreSQL 不映射宿主端口；
- 所有平台脚本指向同一 Compose 文件；
- 启动失败信息为中文且包含解决动作。

## 10. 完成定义

以下条件同时满足才可合并：

- Windows、macOS、Linux 启动入口均存在；
- Docker Desktop 是唯一外部依赖；
- 浏览器页面能显示八项验收证据；
- 重新验收可重复执行；
- Python 3.11 / 3.12 全量测试通过；
- PostgreSQL 16 + 一键验收 + stdio MCP E2E 通过；
- README 首屏提供“小白一键体验”；
- 不新增第三个产品、数据库或 MCP 写入权限。
