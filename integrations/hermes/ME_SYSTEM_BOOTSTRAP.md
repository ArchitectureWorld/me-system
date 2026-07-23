# ME-System Tool Usage

- 涉及已有项目、历史决策、项目约束、项目证据或长期协作规则时，先使用 ME-System MCP。
- 不知道 canonical project ID 时，先调用 `brain_resolve_project`。
- 默认调用 `brain_get_snapshot`，不要先遍历全部项目文件。
- 只有需要分析关系时才调用 `brain_expand_subgraph`。
- 只有需要核验历史变化时才调用 `brain_trace_decision`。
- 需要引用或确认来源时调用 `brain_get_evidence`。
- 需要确定怎样与用户协作时调用 `who_get_task_profile`。
- 工具返回只读信息；不要声称已修改 ME-Brain 或 ME-Who。
- `not_found` 或 `ambiguous` 不是许可进行模糊猜测，应向用户说明范围不明确。
