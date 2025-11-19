# 安装 Daily Paper Insights 为系统服务

## 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **systemd service** | ✅ 开机自动启动<br>✅ 崩溃自动重启<br>✅ 统一日志管理<br>✅ 状态监控 | 需要 sudo 权限 | **生产环境（推荐）** |
| **nohup 后台运行** | ✅ 简单快速<br>✅ 不需要 root | ❌ 不会自动重启<br>❌ 不会开机启动 | 临时测试 |
| **screen/tmux** | ✅ 可以重新连接<br>✅ 交互式调试 | ❌ 需要手动管理 | 开发调试 |

## 推荐方案：systemd service

### 步骤 1: 安装 systemd service

```bash
# 复制 service 文件到系统目录
sudo cp scripts/papers.service /etc/systemd/system/

# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自动启动
sudo systemctl enable papers

# 启动服务
sudo systemctl start papers
```

### 步骤 2: 检查服务状态

```bash
# 查看服务状态
sudo systemctl status papers

# 查看实时日志
sudo journalctl -u papers -f

# 查看最近的日志
sudo journalctl -u papers -n 50
```

### 步骤 3: 管理服务

```bash
# 启动服务
sudo systemctl start papers

# 停止服务
sudo systemctl stop papers

# 重启服务
sudo systemctl restart papers

# 查看服务是否开机自启
sudo systemctl is-enabled papers

# 禁用开机自启
sudo systemctl disable papers
```

### 配置代理（如果需要）

编辑 `/etc/systemd/system/papers.service`，取消注释：

```ini
Environment="HTTP_PROXY=http://127.0.0.1:7890"
Environment="HTTPS_PROXY=http://127.0.0.1:7890"
```

然后重启服务：

```bash
sudo systemctl daemon-reload
sudo systemctl restart papers
```

---

## 替代方案 1: nohup 后台运行

### 使用脚本（简单）

```bash
# 后台启动
./start_server.sh daemon

# 查看日志
tail -f backend/logs/server.log

# 停止服务
./start_server.sh stop

# 或手动停止
kill $(cat backend/logs/server.pid)
```

### 手动使用 nohup

```bash
# 启动
nohup uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 \
  > backend/logs/server.log 2>&1 &

# 记录 PID
echo $! > backend/logs/server.pid

# 停止
kill $(cat backend/logs/server.pid)
```

---

## 替代方案 2: screen/tmux

### 使用 screen

```bash
# 创建新 session
screen -S papers

# 在 screen 中启动服务
./start_server.sh dev

# 分离 session：按 Ctrl+A 然后按 D

# 重新连接
screen -r papers

# 列出所有 session
screen -ls

# 杀死 session
screen -S papers -X quit
```

### 使用 tmux

```bash
# 创建新 session
tmux new -s papers

# 在 tmux 中启动服务
./start_server.sh dev

# 分离 session：按 Ctrl+B 然后按 D

# 重新连接
tmux attach -t papers

# 列出所有 session
tmux ls

# 杀死 session
tmux kill-session -t papers
```

---

## 开发模式 vs 生产模式

### 开发模式（带热重载）

```bash
./start_server.sh dev

# 或直接运行
uv run uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0
```

**特点：**
- ✅ 代码修改自动重载
- ✅ 详细错误信息
- ❌ 性能较低
- ❌ 单进程

### 生产模式（多进程）

```bash
./start_server.sh prod

# 或直接运行
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --workers 4
```

**特点：**
- ✅ 4 个 worker 进程
- ✅ 更高性能
- ✅ 自动负载均衡
- ❌ 代码修改需要手动重启

---

## 常见问题

### Q: 如何查看服务是否在运行？

```bash
# systemd service
sudo systemctl status papers

# nohup/daemon
ps aux | grep uvicorn

# 检查端口
netstat -tlnp | grep :8000
# 或
ss -tlnp | grep :8000
```

### Q: 服务启动失败怎么办？

```bash
# 查看详细日志
sudo journalctl -u papers -n 100

# 检查配置文件
cat /etc/systemd/system/papers.service

# 检查工作目录是否正确
cd /media/olenet/1tdisk/workfiles/papers
ls backend/app/main.py

# 手动测试启动
cd /media/olenet/1tdisk/workfiles/papers
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0
```

### Q: 如何更新代码后重启服务？

```bash
# systemd service
git pull
sudo systemctl restart papers

# nohup/daemon
git pull
./start_server.sh stop
./start_server.sh daemon
```

### Q: 如何同时运行 papers 服务和 frpc 服务？

两个服务互不干扰，可以同时运行：

```bash
# 启动 frpc（内网穿透）
sudo systemctl start frpc

# 启动 papers（FastAPI 服务）
sudo systemctl start papers

# 查看两个服务状态
sudo systemctl status frpc papers
```

### Q: 日志文件太大怎么办？

systemd 的日志会自动轮转，但可以配置保留时间：

```bash
# 查看日志占用空间
journalctl --disk-usage

# 清理超过 7 天的日志
sudo journalctl --vacuum-time=7d

# 限制日志大小为 100M
sudo journalctl --vacuum-size=100M
```

对于 nohup 日志，可以在 cron 中添加清理任务：

```bash
# 每周清理超过 30 天的日志
0 3 * * 0 find /media/olenet/1tdisk/workfiles/papers/backend/logs -name "*.log" -mtime +30 -delete
```
