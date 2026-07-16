# ADR-0001：采用 Monorepo 起步并保持可拆分边界

- 状态：Accepted
- 日期：2026-07-16
- 决策范围：仓库组织、产品边界、构建与部署

## 背景

ME-System 包含两个独立产品：

- ME-Who：用户理解与个性化上下文；
- ME-Brain：项目结构化元数据与 Agent 项目上下文。

二者共享大量基础能力：

- Source Ledger；
- Provenance；
- Temporal Model；
- Identity Resolution；
- Permissions；
- Connector SDK；
- MCP / REST 协议；
- Context Pack 基础类型；
- Context Compiler。

当前处于产品边界、Schema 和上下文协议的高频调整阶段。如果立即拆成多个仓库，需要同时维护 `me-who`、`me-brain` 和 `me-core` 的版本兼容，增加跨仓修改、端到端测试和部署成本。

## 备选方案

### 方案 A：两个完全独立仓库

```text
me-who
me-brain
```

优点：

- 产品边界直观；
- 可独立发布、开源和授权；
- 隐私与团队权限隔离较强。

缺点：

- 共享类型容易复制；
- Schema 高频调整时协议漂移严重；
- 实际上还需要第三个 `me-core` 仓库；
- 跨仓库端到端调试复杂；
- 不适合当前单人或小团队快速验证阶段。

### 方案 B：一个无边界的统一仓库

优点：

- 开发速度快；
- 所有模块可直接调用。

缺点：

- ME-Who 与 ME-Brain 容易直接访问彼此内部数据；
- 共享包逐渐吞并领域逻辑；
- 无法独立部署；
- 后续拆分成本极高。

### 方案 C：Monorepo + 强模块边界

优点：

- 共享协议可以原子修改；
- 端到端测试和本地部署简单；
- 适合早期快速重构；
- 仍可独立构建、部署和发布；
- 当产品成熟后可以低成本拆仓。

缺点：

- 需要主动治理依赖方向；
- CI 和构建需要增量执行；
- 必须防止业务逻辑进入共享核心。

## 决策

采用 **方案 C：Monorepo + 强模块边界**。

仓库使用 `me-system`，建议目标结构：

```text
me-system/
├── apps/
│   ├── me-who/
│   └── me-brain/
├── services/
│   ├── context-compiler/
│   ├── ingestion/
│   ├── retrieval/
│   └── identity-resolution/
├── packages/
│   ├── me-core/
│   ├── source-ledger/
│   ├── provenance/
│   ├── temporal-model/
│   ├── permissions/
│   ├── connector-sdk/
│   └── mcp-sdk/
├── domains/
│   ├── me-who-schema/
│   └── me-brain-schema/
├── tests/
│   ├── contract/
│   └── e2e/
└── docs/
```

## 强制边界

### 1. 产品不得直接读取对方数据库

错误方式：

```text
ME-Brain → SELECT * FROM me_who.preferences
```

正确方式：

```text
Context Compiler
├── 调用 ME-Brain API
└── 调用 ME-Who API
```

### 2. 共享核心不得包含领域判断

共享核心可以包含：

- ID；
- 时间区间；
- SourceReference；
- Provenance；
- Permission；
- EventEnvelope；
- Context Pack 基础协议。

共享核心不得包含：

- 用户偏好推断；
- 项目决策逻辑；
- 科研本体；
- 设计本体；
- 用户画像算法。

### 3. 产品必须可独立构建和运行

目标命令形态：

```bash
docker compose up me-brain
docker compose up me-who
docker compose up me-who me-brain context-compiler
```

### 4. 产品使用独立数据库 Schema

第一阶段可以共用一个 PostgreSQL 实例，但至少分为：

```text
core
me_who
me_brain
```

业务代码只能访问自己的领域 Schema 和经过授权的共享 Schema。

### 5. API 独立版本化

```text
/api/me-who/v1/...
/api/me-brain/v1/...
/api/context/v1/...
```

### 6. 独立镜像和版本

```text
me-who:<version>
me-brain:<version>
me-context:<version>
```

Monorepo 不要求三个组件使用相同发布周期。

## 拆仓触发条件

不按固定时间拆仓。当下列条件满足至少三项时重新评估：

1. ME-Who 与 ME-Brain 已由独立团队长期维护；
2. 发布周期显著不同；
3. 开源或许可证策略不同；
4. ME-Who 需要独立安全审计和代码访问控制；
5. `me-core` 公共协议已稳定，变更频率明显下降；
6. 两个产品均可脱离对方独立运行；
7. 单仓 CI 和代码权限成为实际阻碍，而不是预期风险。

## 后果

### 正面后果

- 可以同步修改共享 Schema 和两侧适配器；
- 更容易建立组合上下文端到端测试；
- NAS / Linux Docker 部署更简单；
- 第一阶段无需维护跨仓版本矩阵。

### 需要治理的风险

- 使用依赖规则和测试防止越界访问；
- 使用按变更范围执行的 CI；
- 共享包必须保持最小化；
- 所有跨产品调用通过明确协议完成；
- 定期审查模块是否仍可独立部署。
