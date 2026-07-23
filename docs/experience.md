# ME-System 小白一键体验验收

这套体验只要求安装并打开 **Docker Desktop**。不需要安装 Python、PostgreSQL、Node.js，也不需要配置环境变量。

## 三步开始

### 1. 安装并打开 Docker Desktop

等待 Docker Desktop 显示正在运行。首次启动可能需要接受许可或完成系统权限设置。

### 2. 下载并解压仓库

保持目录结构不变，不要只复制单个启动文件。

### 3. 启动

| 系统 | 操作 |
|---|---|
| Windows | 双击 `体验.bat` |
| macOS | 双击 `体验.command`；若系统提示来源不明，右键文件选择“打开” |
| Linux | 在仓库目录运行 `./体验.sh` |

启动完成后浏览器会打开：

```text
http://localhost:8765
```

## 页面怎样算通过

页面顶部必须显示：

```text
全部通过
ME-System 一键体验验收成功
```

页面会逐项验证：

1. PostgreSQL 16 与 Alembic 迁移；
2. lighting-platform 双图谱基线；
3. SourceRecord 与 EvidenceFragment；
4. IngestionRun、覆盖率与质量报告；
5. ME-Brain Candidate 审核；
6. ME-Who Candidate 审核；
7. 权威对象到原始证据的回溯；
8. 真实 stdio MCP Client 查询。

这些步骤使用真实 Repository、事务、查询服务和 MCP Server，不是预先写死的动画。

## 重新验收

点击页面上的 **重新验收**。系统会生成新的运行编号和新的体验对象，不会与上一轮冲突。

## 停止

| 系统 | 操作 |
|---|---|
| Windows | 双击 `停止体验.bat` |
| macOS / Linux | 运行 `./停止体验.sh` |

停止操作不会删除专用体验数据。彻底重置：

```bash
docker compose -f deploy/experience/compose.yml down --volumes
```

## 数据与隐私

- 体验使用独立 Docker network 和独立 PostgreSQL volume；
- PostgreSQL 端口不会映射到电脑；
- 只开放本地验收页面端口 `8765`；
- 不连接正式 ME-System 数据库；
- 不读取真实 ME-Who 信息；
- 页面不显示数据库密码、完整连接 URL或 Python traceback；
- Candidate 写入与审核能力没有加入 MCP。

## 常见问题

### 提示“没有找到 Docker”

安装 Docker Desktop，然后重新打开终端或重新双击启动文件。

### 提示“Docker 尚未运行”

打开 Docker Desktop，等状态变为 Running 后重试。

### 端口 8765 被占用

停止占用该端口的程序，或执行：

```bash
docker compose -f deploy/experience/compose.yml down --remove-orphans
```

然后重新启动体验。

### 页面显示失败

展开失败卡片查看脱敏错误摘要，再查看容器日志：

```bash
docker compose -f deploy/experience/compose.yml logs --tail=120 experience
```

### 首次构建较慢

Docker 需要下载 Python 和 PostgreSQL 镜像。后续启动会复用本地镜像，速度会明显加快。

## 开发者直接运行

已有 PostgreSQL 时：

```bash
ME_GRAPH_DATABASE_URL='postgresql+psycopg://...' \
python -m me_system.experience --host 127.0.0.1 --port 8765
```

SQLite 仅用于测试：

```bash
python -m me_system.experience \
  --database-url 'sqlite+pysqlite:///experience.db' \
  --allow-test-database \
  --no-mcp
```
