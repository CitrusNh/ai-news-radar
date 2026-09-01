# SignalScope AI｜AI 热点摘要雷达

独立项目三：面向公众的 AI 行业热点摘要网站。

当前仓库包含：

- `frontend/`：与后端 API 联通的公共网站 Demo，后端不可用时自动回退本地样例；
- `backend/`：SQLite 持久化、来源注册、RSS/Atom 获取、标准化、去重、事件聚类、热点评分、用户行为和 API 服务；
- `tests/`：后端单元测试、接口测试和前端关键行为说明。

## 当前已实现

- SQLite 持久化，服务重启后事件、偏好、收藏和已读状态可以恢复；
- RSS 2.0 与 Atom 解析；
- 来源必须显式通过 robots 和合规审核后才能进入自动任务；
- 拒绝 localhost、内网和保留 IP 地址，降低 SSRF 风险；
- 单来源失败隔离、有限重试、URL 去重、事件聚类和热点评分；
- 可配置但默认关闭的定时任务；
- 管理来源、触发任务和查询任务状态的接口；
- 前端显示真实后端存储、来源数量和调度状态。

## 本地启动（后端）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

打开 `http://127.0.0.1:8000/docs` 查看 API 文档。

也可以在 Windows 仓库根目录运行：

```powershell
.\start-demo.ps1
```

脚本只会启动一个网站服务，页面和 API 都在 `http://127.0.0.1:8000`。定时 RSS 任务默认关闭；只有在来源通过审核并设置环境变量后才建议启用：

```powershell
$env:SIGNALSCOPE_SCHEDULER_ENABLED="true"
$env:SIGNALSCOPE_SCHEDULER_INTERVAL_SECONDS="14400"
```

管理接口必须配置密钥：

```powershell
$env:SIGNALSCOPE_ADMIN_KEY="your-local-admin-key"
```

## Docker 运行（推荐）

安装 Docker Desktop 后，在仓库根目录执行：

```powershell
$env:SIGNALSCOPE_ADMIN_KEY="replace-with-a-strong-key"
docker compose up --build -d
```

随后打开 `http://127.0.0.1:8000`。页面、API 和 SQLite 数据库都在同一个容器应用中；数据库保存于 Docker 命名卷 `signalscope-data`，重启或升级容器不会丢失。

停止网站：

```powershell
docker compose down
```

除非明确希望清空数据，不要执行 `docker compose down -v`。

## 部署为所有人可访问的网站

仓库包含 `render.yaml`，可以部署为单一公网 Web Service：用户访问一个 HTTPS 地址即可使用，不需要安装 Python、Docker，也不需要分别打开前端和后端。

部署前需要先把这个仓库推送到你自己的 GitHub/GitLab，再在 Render 中选择 Blueprint 部署。部署配置会：

- 使用 Docker 构建一体化网站；
- 自动创建管理密钥；
- 将 `/app/data/runtime` 挂载为持久化磁盘；
- 使用 `/api/v1/health` 做健康检查；
- 每次仓库提交后自动重新部署。

部署完成后会得到类似 `https://signalscope-ai.onrender.com` 的公开网址。注意：持久化磁盘通常需要云平台的付费实例；免费临时文件系统会在重启后丢失 SQLite 数据。

CI 配置位于 `.github/workflows/ci.yml`，每次提交都会执行全部测试、前端语法检查和 Docker 镜像构建。

主要接口：

- `GET /api/v1/events`：热点事件列表；
- `GET /api/v1/events/{id}`：事件详情；
- `GET/PUT /api/v1/preferences`：匿名用户偏好；
- `POST /api/v1/events/{id}/actions`：收藏、已读等行为；
- `GET /api/v1/library`：收藏库或阅读库；
- `GET /api/v1/admin/source-health`：来源健康状态；
- `PUT /api/v1/admin/sources/{id}`：注册或更新审核后的 RSS 来源；
- `POST /api/v1/admin/runs`：运行一次增量获取；
- `GET /api/v1/admin/runs/{id}`：查询运行结果。

## 数据与合规边界

当前默认数据库只包含用于展示逻辑的本地样例数据。项目不会自动抓取任意网页，也不会绕过登录、验证码或付费墙。真实接入时应先完成来源条款审计，将 `robots_status` 设为 `allowed`、`compliance_status` 设为 `approved`，再通过管理接口注册 RSS 地址。

## 本地启动（前端 Demo）

```powershell
python -m http.server 4173 --directory frontend
```

打开 `http://127.0.0.1:4173/`。

## 测试

```powershell
pytest -q
```

测试命令会执行后端单元测试、API 集成测试、前端契约测试，并要求后端代码覆盖率不低于 80%。前端交互还需在浏览器中验证首页加载、筛选、详情、收藏和主题切换。

MVP 使用本地样例数据和可替换的 AI 加工接口，不接入付费 API，也不抓取新闻网站。
