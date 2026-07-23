#!/bin/bash
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$ROOT/deploy/experience/compose.yml"
DASHBOARD_URL="http://localhost:8765"

# 实际启动由体验.sh统一执行：docker compose -f "$COMPOSE_FILE" up --build -d
bash "$ROOT/体验.sh"
status=$?

if [ "$status" -ne 0 ]; then
  printf '\n启动没有完成。请按回车关闭窗口，处理提示后再次双击“体验.command”。\n'
  read -r _
  exit "$status"
fi

printf '\n验收页：%s\n' "$DASHBOARD_URL"
printf '可以关闭此窗口，Docker 服务会继续运行。按回车关闭。\n'
read -r _
