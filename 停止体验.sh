#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT/deploy/experience/compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  printf '[失败] 没有找到 Docker，无法停止体验环境。\n' >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" down --remove-orphans
printf 'ME-System 体验环境已停止。专用体验数据仍保留，重新启动可继续使用。\n'
printf '彻底重置数据：docker compose -f "%s" down --volumes\n' "$COMPOSE_FILE"
