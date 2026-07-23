# Pi Integration Boundary

Pi 在 ME-Brain + Hermes 只读闭环稳定后接入。

## 推荐方式

使用薄 TypeScript Extension 调用与 Hermes MCP 相同的 Graph Query API。

## 默认权限

```text
当前项目 ME-Brain：允许
当前任务证据：允许
完整 ME-Who：拒绝
任务相关 CollaborationRule：显式允许
候选变更提交：允许
候选批准：拒绝
```

## 第一批能力

```text
brain_get_snapshot
brain_get_evidence
who_get_task_profile
submit_candidate_change
```

Pi 不应通过扫描私人目录替代 ME-System 查询，也不应自行扩大项目范围。
