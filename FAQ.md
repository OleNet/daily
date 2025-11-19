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

### Q3: 运行脚本时如何不走系统代理？

**问题：**系统设置了 SOCKS 代理，但 `daily_ingest.py` 访问 arXiv 和 Hugging Face 时不希望走代理。

**解决方案：**
已在代码中禁用代理：

**`backend/app/services/hf_client.py`：**
```python
self.session = httpx.Client(
    timeout=settings.request_timeout,
    headers={"User-Agent": settings.user_agent},
    follow_redirects=True,
    proxy=None,  # 禁用代理
)
```

**`backend/app/services/arxiv_fetcher.py`：**
```python
self.client = httpx.Client(
    timeout=settings.request_timeout,
    headers={"User-Agent": settings.user_agent},
    proxy=None,  # 禁用代理
)
```

这样即使系统环境变量设置了 `HTTP_PROXY` 或 `HTTPS_PROXY`，httpx 也会忽略代理设置。

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

## 开发调试

### Q5: 如何从其他机器访问本地开发环境？

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

## 常见错误

### Q6: ImportError: Using SOCKS proxy, but the 'socksio' package is not installed

**原因：**系统配置了 SOCKS 代理，但 httpx 没有安装 SOCKS 支持。

**解决方案 1（推荐）：**禁用代理
- 已在代码中通过 `proxy=None` 禁用（见 Q3）

**解决方案 2：**安装 SOCKS 支持
```bash
# 修改 pyproject.toml
# "httpx>=0.27.2" → "httpx[socks]>=0.27.2"
uv sync
```

### Q7: 页面显示"该日期暂无论文摘要"

**可能原因：**
1. 数据库为空 → 运行 `daily_ingest.py` 导入数据（见 Q4）
2. 选择的日期没有数据 → 切换到有数据的日期
3. API 调用失败 → 检查浏览器开发者工具的 Network 标签

---

## 邮件订阅

### Q8: 如何配置邮件订阅功能？

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
