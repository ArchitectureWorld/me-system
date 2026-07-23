# ME-Graph Core

ME-Graph Core 是 ME-System 双权威图谱的首个可运行基础。

## 能力

- 双图谱和 Bridge 命名空间；
- 带来源、时间、权限和权威状态的节点与边；
- 候选变更审核；
- 项目快照；
- 决策替代链；
- 子图展开；
- 证据查询；
- 任务相关 ME-Who 查询；
- JSON Schema 与 Python 契约双重校验。

## 安装

```bash
python -m pip install -e '.[dev]'
```

## 测试

```bash
pytest -q
```

## 示例

从仓库根目录：

```bash
cd services/me-graph-core

me-graph load-fixture \
  --fixture ../../examples/graph/lighting-platform.json

me-graph project-snapshot \
  --fixture ../../examples/graph/lighting-platform.json \
  --project-id brain:project:lighting-platform

me-graph trace-decision \
  --fixture ../../examples/graph/lighting-platform.json \
  --decision-id brain:decision:radiance-primary

me-graph task-profile \
  --fixture ../../examples/graph/lighting-platform.json \
  --user-id who:user:master \
  --project-id brain:project:lighting-platform \
  --task-type implementation
```

## 当前边界

- 使用内存存储；
- 还没有生产 MCP Server；
- 还没有权限过滤器；
- 还没有自动文档抽取；
- 候选变更只支持新增节点和新增边。

这些是刻意限制。当前目标是先稳定图谱语义和查询行为。
