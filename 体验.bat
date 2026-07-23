@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "COMPOSE_FILE=%ROOT%deploy\experience\compose.yml"
set "DASHBOARD_URL=http://localhost:8765"

echo.
echo ME-System 小白一键体验验收
echo.

docker --version >nul 2>&1
if errorlevel 1 goto no_docker

docker compose version >nul 2>&1
if errorlevel 1 goto no_compose

docker info >nul 2>&1
if errorlevel 1 goto docker_not_running

echo 正在构建并启动专用体验环境，请保持 Docker Desktop 运行。
docker compose -f "%COMPOSE_FILE%" up --build -d
if errorlevel 1 goto startup_failed

for /l %%I in (1,1,60) do (
  docker compose -f "%COMPOSE_FILE%" exec -T experience python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3).read()" >nul 2>&1
  if not errorlevel 1 goto ready
  timeout /t 2 /nobreak >nul
)

echo.
echo [失败] 体验服务没有在 120 秒内就绪。最近日志：
docker compose -f "%COMPOSE_FILE%" logs --tail=120 experience
goto failed

:ready
echo.
echo [成功] 验收页已就绪：%DASHBOARD_URL%
echo 停止体验：双击“停止体验.bat”
start "" "%DASHBOARD_URL%"
echo.
echo 可以关闭此窗口，Docker 服务会继续运行。
pause >nul
exit /b 0

:no_docker
echo [失败] 没有找到 Docker。请先安装并打开 Docker Desktop。
goto failed

:no_compose
echo [失败] 当前 Docker 不支持 docker compose。请升级 Docker Desktop。
goto failed

:docker_not_running
echo [失败] Docker 尚未运行。请打开 Docker Desktop，等待状态变为 Running。
goto failed

:startup_failed
echo [失败] 容器启动失败。请检查 Docker Desktop 的磁盘空间和网络。
goto failed

:failed
echo.
echo 处理以上问题后，再次双击“体验.bat”。
pause
exit /b 1
