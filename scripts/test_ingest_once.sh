#!/bin/bash
# One-time Test Script for Daily Ingest
# This script runs daily_ingest.py once for testing purposes

# 设置工作目录
cd /media/olenet/1tdisk/workfiles/papers || exit 1

# 设置日志目录
LOG_DIR="backend/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/test_ingest_${TIMESTAMP}.log"

# 设置代理（如果需要访问 arXiv/Hugging Face）
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"

# 记录开始时间
echo "=== Test Ingest Started at $(date) ===" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 运行导入脚本（限制5篇论文用于快速测试）
echo "Running daily_ingest.py with --limit 5..." | tee -a "$LOG_FILE"
/home/olenet/anaconda3/bin/uv run python backend/scripts/daily_ingest.py --limit 5 >> "$LOG_FILE" 2>&1

# 记录结束时间和退出码
EXIT_CODE=$?
echo "" | tee -a "$LOG_FILE"
echo "=== Test Ingest Finished at $(date) with exit code $EXIT_CODE ===" | tee -a "$LOG_FILE"

# 输出日志位置
echo "Full log saved to: $LOG_FILE"

exit $EXIT_CODE
