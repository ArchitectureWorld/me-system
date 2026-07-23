@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "COMPOSE_FILE=%ROOT%deploy\experience\compose.yml"

docker --version >nul 2>&1
if errorlevel 1 (
  echo [失败] 没有找到 Docker，无法停止体验环境。
  pause
  exit /b 1
)

docker compose -f "%COMPOSE_FILE%" down --remove-orphans
if errorlevel 1 (
  echo [失败] 停止体验环境时发生错误，请打开 Docker Desktop 后重试。
  pause
  exit /b 1
)

echo ME-System 体验环境已停止。专用体验数据仍保留。
echo 彻底重置数据可执行：docker compose -f "%COMPOSE_FILE%" down --volumes
pause
