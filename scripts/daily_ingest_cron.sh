#!/bin/bash
# Daily Paper Ingestion Cron Job
# This script runs daily_ingest.py with proper environment and logging

# 设置工作目录
cd /media/olenet/1tdisk/workfiles/papers || exit 1

# 设置日志目录
LOG_DIR="backend/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily_ingest_cron.log"

# 设置代理（如果需要访问 arXiv/Hugging Face）
# 取消下面的注释并修改为你的代理地址
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"

# 记录开始时间
echo "=== Daily Ingest Started at $(date) ===" >> "$LOG_FILE"

# 运行导入脚本（导入昨天的论文）
# --date 参数留空会自动导入昨天的数据
/home/olenet/anaconda3/bin/uv run python backend/scripts/daily_ingest.py >> "$LOG_FILE" 2>&1

# 记录结束时间和退出码
EXIT_CODE=$?
echo "=== Daily Ingest Finished at $(date) with exit code $EXIT_CODE ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 可选：日志文件轮转（保留最近30天）
find "$LOG_DIR" -name "daily_ingest_cron.log.*" -mtime +30 -delete

exit $EXIT_CODE
