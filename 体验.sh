#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT/deploy/experience/compose.yml"
DASHBOARD_URL="http://localhost:8765"

fail() {
  printf '\n[失败] %s\n' "$1" >&2
  printf '解决后重新运行：%s\n' "$0" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "没有找到 Docker。请先安装并打开 Docker Desktop。"
docker compose version >/dev/null 2>&1 || fail "当前 Docker 不支持 docker compose。请升级 Docker Desktop。"
docker info >/dev/null 2>&1 || fail "Docker 尚未运行。请打开 Docker Desktop，等待状态变为 Running。"

printf '\nME-System 小白一键体验验收\n'
printf '正在构建并启动专用体验环境，请保持 Docker Desktop 运行。\n\n'

docker compose -f "$COMPOSE_FILE" up --build -d || fail "容器启动失败。请检查 Docker Desktop 的磁盘空间和网络。"

ready=0
for _ in $(seq 1 60); do
  if docker compose -f "$COMPOSE_FILE" exec -T experience \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3).read()" \
    >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  printf '\n体验服务没有在 120 秒内就绪。最近日志：\n' >&2
  docker compose -f "$COMPOSE_FILE" logs --tail=120 experience >&2 || true
  fail "体验服务启动超时。"
fi

printf '\n[成功] 验收页已就绪：%s\n' "$DASHBOARD_URL"
printf '停止体验：%s/停止体验.sh\n\n' "$ROOT"

if command -v open >/dev/null 2>&1; then
  open "$DASHBOARD_URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$DASHBOARD_URL" >/dev/null 2>&1 || true
else
  printf '请在浏览器打开：%s\n' "$DASHBOARD_URL"
fi
