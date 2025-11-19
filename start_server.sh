#!/bin/bash
# Daily Paper Insights - Server Startup Script
#
# Usage:
#   ./start_server.sh          # 前台运行（开发模式，带热重载）
#   ./start_server.sh dev      # 前台运行（开发模式）
#   ./start_server.sh prod     # 前台运行（生产模式，无热重载）
#   ./start_server.sh daemon   # 后台运行（使用 nohup）
#
# 推荐：使用 systemd service（见 scripts/papers.service）

cd "$(dirname "$0")" || exit 1

MODE="${1:-dev}"
LOG_DIR="backend/logs"
mkdir -p "$LOG_DIR"

case "$MODE" in
  dev)
    echo "🚀 Starting server in development mode (with auto-reload)..."
    uv run uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000
    ;;

  prod)
    echo "🚀 Starting server in production mode (no auto-reload)..."
    uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 4
    ;;

  daemon)
    echo "🚀 Starting server in daemon mode (background)..."
    nohup uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 \
      > "$LOG_DIR/server.log" 2>&1 &
    PID=$!
    echo "Server started with PID: $PID"
    echo "$PID" > "$LOG_DIR/server.pid"
    echo "📋 Log file: $LOG_DIR/server.log"
    echo "🛑 Stop server: kill \$(cat $LOG_DIR/server.pid)"
    ;;

  stop)
    if [ -f "$LOG_DIR/server.pid" ]; then
      PID=$(cat "$LOG_DIR/server.pid")
      echo "🛑 Stopping server (PID: $PID)..."
      kill "$PID" 2>/dev/null && rm "$LOG_DIR/server.pid"
      echo "✅ Server stopped"
    else
      echo "❌ No PID file found. Server may not be running."
    fi
    ;;

  *)
    echo "Usage: $0 {dev|prod|daemon|stop}"
    echo ""
    echo "  dev    - Development mode with auto-reload (default)"
    echo "  prod   - Production mode with 4 workers"
    echo "  daemon - Run in background using nohup"
    echo "  stop   - Stop daemon server"
    echo ""
    echo "Recommended: Use systemd service instead (see scripts/papers.service)"
    exit 1
    ;;
esac
