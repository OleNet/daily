# FAQ - 常见问题解答

## 部署与访问

### Q1: 如何通过公网访问 Dashboard？

**问题：**从另一台机器或公网访问 `http://119.23.152.151:8000/dashboard` 时页面显示空白或无数据。

**可能的原因及解决方案：**

#### 1. 前端 API 地址配置问题

**症状：**浏览器控制台显示无法连接到 `localhost:8000`

**原因：**前端使用了硬编码的 `localhost` 地址，从其他机器访问时会尝试连接访问者本地的 8000 端口。

**解决方案：**
- 已修复：`frontend/app.js` 中的 `API_BASE` 改为相对路径 `/api`
- 这样无论从哪个 IP 访问，都会自动使用当前域名的 API

#### 2. FRP 内网穿透配置

**FRP 配置说明：**

**客户端配置 (`frpc.toml`)：**
```toml
serverAddr = "119.23.152.151"
serverPort = 9891

[auth]
method = "token"
token = "your-token-here"

[[proxies]]
name = "web8000"
type = "tcp"              # TCP 类型可以转发 HTTP 流量
localIP = "127.0.0.1"
localPort = 8000
remotePort = 8000         # 公网访问端口
```

**重要说明：**
- `type = "tcp"` 完全可以用于 HTTP 服务（HTTP 基于 TCP）
- 访问方式：`http://119.23.152.151:8000/dashboard`
- `type = "http"` 的优势是支持域名和多服务共享端口，但对于简单端口转发，TCP 就够了

**检查 frpc 服务状态：**
```bash
# 检查服务是否运行
sudo systemctl status frpc

# 重启服务
sudo systemctl restart frpc

# 查看实时日志（确认代理是否加载）
sudo journalctl -u frpc -f
```

**成功的日志应该包含：**
```
[I] login to server success, get run id [xxx]
[I] proxy added: [ssh]
[I] proxy added: [web8000]        ← 关键：确认 web8000 代理已添加
[I] [web8000] start proxy success
```

**如果只看到 `ssh` 没有 `web8000`：**
- 检查 `frpc.toml` 配置文件语法
- 确认配置文件路径正确（通过 systemd service 文件查看）
- 重启服务后查看错误日志

#### 3. 服务器端配置

**frps 服务器端 (`frps.toml`)：**
```toml
bindPort = 9891

[auth]
method = "token"
token = "your-token-here"
```

**防火墙规则：**
确保服务器端开放了必要的端口：
- 9891：frp 控制端口
- 8000：web 服务端口（或你配置的 remotePort）

```bash
# 阿里云/腾讯云等需要在安全组规则中开放端口
# 本地防火墙也需要开放
sudo ufw allow 8000/tcp
sudo ufw allow 9891/tcp
```

#### 4. FastAPI 服务配置

**确保绑定到所有网络接口：**
```bash
# 错误（只监听本地）
uvicorn app.main:app --app-dir backend

# 正确（监听所有接口，允许外部访问）
uvicorn app.main:app --app-dir backend --host 0.0.0.0
```

**检查端口监听状态：**
```bash
# 查看 8000 端口是否在监听
ss -tlnp | grep :8000

# 期望输出：0.0.0.0:8000（而不是 127.0.0.1:8000）
```

---

## 数据库相关

### Q2: 数据库文件应该放在哪里？

**推荐：放在项目根目录**

**设计理由：**
1. **数据与代码分离** - 符合关注点分离原则
2. **便于备份和迁移** - 可以单独备份数据文件
3. **多服务共享** - 如果将来添加其他服务（worker、admin），都能方便访问
4. **部署灵活性** - 容器化时可以单独挂载数据目录为 volume
5. **符合最佳实践** - Django、Rails 等框架都采用此模式

**推荐的项目结构：**
```
papers/
├── backend/          # 后端代码（纯代码）
├── frontend/         # 前端代码
├── storage/          # 文件存储
├── papers.db         # 数据库（数据层）
├── pyproject.toml
└── .gitignore       # 已包含 *.db 规则
```

**配置说明：**
- 数据库路径已自动配置为 `project_root/papers.db`
- 无需在 `.env` 中设置 `DATABASE_URL`（除非要自定义路径）
- 代码会自动计算正确的绝对路径

---

## 网络与代理

### Q3: 如何配置代理访问 arXiv 和 Hugging Face？

**代理配置说明：**

httpx 客户端会自动读取系统环境变量 `HTTP_PROXY` 和 `HTTPS_PROXY`。

**场景 1：使用代理访问国外网站（国内用户推荐）**

```bash
# HTTP 代理
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"

# 或 SOCKS5 代理（需要安装 httpx[socks]）
export HTTP_PROXY="socks5://127.0.0.1:1080"
export HTTPS_PROXY="socks5://127.0.0.1:1080"

# 然后运行脚本
uv run python backend/scripts/daily_ingest.py
```

**场景 2：部分服务使用代理（推荐）**

```bash
# FRP 等本地服务不走代理
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
export NO_PROXY="localhost,127.0.0.1,192.168.0.0/16,119.23.152.151"
```

**场景 3：不使用代理**

```bash
# 临时禁用代理
unset HTTP_PROXY
unset HTTPS_PROXY

# 或
NO_PROXY="*" uv run python backend/scripts/daily_ingest.py
```

**代理类型选择：**
- 如果使用 SOCKS 代理，需要安装：`httpx[socks]`（在 pyproject.toml 中修改依赖）
- HTTP/HTTPS 代理无需额外依赖

---

## 数据导入

### Q4: 数据库为空，如何导入论文数据？

**初次使用时需要运行数据导入：**

```bash
# 测试导入（先导入 5 篇论文）
uv run python backend/scripts/daily_ingest.py --limit 5

# 导入昨天的所有论文
uv run python backend/scripts/daily_ingest.py

# 导入特定日期的论文
uv run python backend/scripts/daily_ingest.py --date 2025-11-18

# 强制重新分析已存在的论文（更新 LLM 分析结果）
uv run python backend/scripts/daily_ingest.py --date 2025-11-18 --force-update

# 调试模式（查看详细日志）
uv run python backend/scripts/daily_ingest.py --debug
```

**检查数据库内容：**
```bash
sqlite3 papers.db
# sqlite> SELECT COUNT(*) FROM paper;
# sqlite> SELECT arxiv_id, title FROM paper LIMIT 5;
# sqlite> .exit
```

---

### Q5: 如何设置每天自动导入论文数据？

**使用 Cron Job 实现定时任务（推荐）**

项目已包含封装好的 cron 脚本：`scripts/daily_ingest_cron.sh`

**步骤 1：配置代理（如果需要）**

编辑 `scripts/daily_ingest_cron.sh`，取消注释并设置代理：

```bash
# 如果需要访问 arXiv/Hugging Face，设置代理
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
```

**步骤 2：安装 crontab**

```bash
# 查看示例配置
cat scripts/crontab.txt

# 安装 crontab（每天早上 8:00 运行）
crontab scripts/crontab.txt

# 查看已安装的任务
crontab -l
```

**步骤 3：验证和监控**

```bash
# 手动测试脚本
./scripts/daily_ingest_cron.sh

# 查看运行日志
tail -f backend/logs/daily_ingest_cron.log

# 查看 cron 系统日志
grep CRON /var/log/syslog  # Ubuntu/Debian
# 或
journalctl -u cron         # 使用 systemd 的系统
```

**Cron 时间配置示例：**

```bash
# 每天 8:00
0 8 * * * /path/to/script.sh

# 每天 8:00 和 20:00
0 8,20 * * * /path/to/script.sh

# 每 6 小时
0 */6 * * * /path/to/script.sh

# 每周一 8:00
0 8 * * 1 /path/to/script.sh
```

**注意事项：**
- cron 使用的是系统本地时间（非 UTC）
- 日志文件位于 `backend/logs/daily_ingest_cron.log`
- 脚本会自动导入昨天的论文（无需指定日期）
- 如果需要同时发送邮件，确保 FastAPI 服务也在运行（APScheduler 会处理邮件发送）

**调试技巧：**

```bash
# 临时修改为每分钟运行一次（测试用）
* * * * * /media/olenet/1tdisk/workfiles/papers/scripts/daily_ingest_cron.sh

# 观察日志确认是否执行
watch -n 5 tail -10 backend/logs/daily_ingest_cron.log
```

---

## 开发调试

### Q6: 如何从其他机器访问本地开发环境？

**启动服务时绑定所有接口：**
```bash
uv run uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0
```

**局域网访问：**
```bash
# 查看本机 IP
ip addr show

# 从其他机器访问
# 例如：http://192.168.2.105:8000/dashboard
```

**注意事项：**
- CORS 已配置为允许所有来源（开发环境）
- 生产环境建议限制 CORS 来源
- 确保防火墙允许 8000 端口访问

---

### Q7: 如何让服务器在后台运行（SSH 退出后继续运行）？

**方案 1: systemd service（推荐 - 生产环境）**

类似 frpc 服务，使用 systemd 管理，最稳定专业：

```bash
# 安装服务
sudo cp scripts/papers.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable papers  # 开机自动启动
sudo systemctl start papers   # 启动服务

# 管理服务
sudo systemctl status papers   # 查看状态
sudo systemctl restart papers  # 重启
sudo systemctl stop papers     # 停止

# 查看日志
sudo journalctl -u papers -f  # 实时日志
sudo journalctl -u papers -n 50  # 最近 50 行
```

**优点：**
- ✅ 开机自动启动
- ✅ 崩溃自动重启
- ✅ 统一日志管理
- ✅ 和 frpc 一样的管理方式

**方案 2: 使用 start_server.sh 脚本（快速简单）**

```bash
# 后台启动（使用 nohup）
./start_server.sh daemon

# 查看日志
tail -f backend/logs/server.log

# 停止服务
./start_server.sh stop

# 其他模式
./start_server.sh dev    # 开发模式（前台，带热重载）
./start_server.sh prod   # 生产模式（前台，4个worker）
```

**方案 3: screen/tmux（开发调试）**

```bash
# 使用 screen
screen -S papers
./start_server.sh dev
# 按 Ctrl+A 然后按 D 分离
# 重新连接：screen -r papers

# 使用 tmux
tmux new -s papers
./start_server.sh dev
# 按 Ctrl+B 然后按 D 分离
# 重新连接：tmux attach -t papers
```

**详细说明见：** `scripts/INSTALL_SERVICE.md`

---

## 常见错误

### Q8: ImportError: Using SOCKS proxy, but the 'socksio' package is not installed

**原因：**系统配置了 SOCKS 代理，但 httpx 没有安装 SOCKS 支持。

**解决方案 1（推荐）：**禁用代理
- 已在代码中通过 `proxy=None` 禁用（见 Q3）

**解决方案 2：**安装 SOCKS 支持
```bash
# 修改 pyproject.toml
# "httpx>=0.27.2" → "httpx[socks]>=0.27.2"
uv sync
```

### Q9: 页面显示"该日期暂无论文摘要"

**可能原因：**
1. 数据库为空 → 运行 `daily_ingest.py` 导入数据（见 Q4）
2. 选择的日期没有数据 → 切换到有数据的日期
3. API 调用失败 → 检查浏览器开发者工具的 Network 标签

---

## 邮件订阅

### Q10: 如何配置邮件订阅功能？

**获取 Brevo API Key：**
1. 注册 Brevo 账号：https://app.brevo.com
2. 前往 API Keys 页面：https://app.brevo.com/settings/keys/api
3. 创建 API Key
4. 免费套餐：300 封邮件/天

**配置 `.env`：**
```bash
BREVO_API_KEY=your-brevo-api-key
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Daily Paper Insights
FRONTEND_URL=http://119.23.152.151:8000  # 公网访问地址
DAILY_DIGEST_HOUR=8  # UTC 时间
```

**测试邮件功能：**
```bash
# 订阅测试
curl -X POST http://localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 手动发送测试邮件
uv run python backend/scripts/send_daily_digest.py --limit 1
```

**注意：**
- 如果不配置 `BREVO_API_KEY`，订阅功能仍可用，但不会发送邮件
- 邮件在服务器运行时会自动发送（每天配置的时间）
