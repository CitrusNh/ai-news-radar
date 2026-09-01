# SignalScope AI｜AI 热点摘要雷达

面向公众的 AI 行业热点摘要网站。公网版本使用 Streamlit Community Cloud 托管，通过 Neon PostgreSQL 持久保存新闻事件、来源、更新记录、匿名收藏和已读状态。

- GitHub：[https://github.com/CitrusNh/ai-news-radar](https://github.com/CitrusNh/ai-news-radar)
- Streamlit 公网 Demo：首次在 Streamlit Community Cloud 部署成功后补充实际 HTTPS 地址

## 产品功能

- 首页热点新闻列表与文字摘要；
- AI、科技、财经、娱乐、体育、游戏主题入口；
- 关键词搜索与热度、时间、相关性排序；
- 新闻详情、关键事实、关注原因与来源原文；
- 匿名收藏和已读状态；
- Neon PostgreSQL 连接状态、数据更新时间和手动重新读取；
- 加载中、无匹配结果、待接入分类和数据库错误状态；
- RSS 2.0 与 Atom 解析；
- 来源必须显式通过 robots 和合规审核后才能进入自动任务；
- 拒绝 localhost、内网和保留 IP 地址，降低 SSRF 风险；
- 单来源失败隔离、有限重试、URL 去重、事件聚类和热点评分；
- 可配置但默认关闭的数据更新任务。

## 技术架构

```text
普通用户浏览器
      │ HTTPS
      ▼
Streamlit Community Cloud
      │
      ├─ streamlit_app.py：页面、筛选、搜索、详情与交互
      ├─ backend/app：获取、清洗、去重、聚类、评分与用户行为
      └─ DATABASE_URL
             ▼
       Neon PostgreSQL
       持久保存来源、文章、事件、任务、偏好、收藏和已读
```

仓库中的 `frontend/` 与 FastAPI 服务继续用于本地完整网站和 API 开发；Docker/Compose 保留为自托管备用方案，不是当前公网发布方式。

## 部署为所有人可访问的网站

当前公网方案是 Streamlit Community Cloud，不使用 Render。

在 [Streamlit Community Cloud](https://share.streamlit.io/) 创建应用，填写：

| 字段 | 内容 |
|---|---|
| Repository | `CitrusNh/ai-news-radar` |
| Branch | `main` |
| Main file path | `streamlit_app.py` |

在应用的 **Advanced settings → Secrets** 中加入：

```toml
DATABASE_URL = "从 Neon Connect 对话框复制的 PostgreSQL 连接串"
```

不要把真实连接串写进代码、GitHub、Issue 或聊天。建议使用 Neon 的 pooled connection string，并保留 `sslmode=require`。应用启动时会严格检查 `DATABASE_URL`：缺失或不是 PostgreSQL 时会显示配置错误并停止，不会回退到 Streamlit 临时文件系统中的 SQLite。

### Streamlit Cloud 限制

- 免费应用长时间无人访问时可能休眠，首次唤醒会稍慢；
- Streamlit 进程可能重启，因此页面会话状态不是永久存储；收藏、已读和新闻数据通过 Neon PostgreSQL 持久化；
- 当前匿名身份保存在页面 URL 的随机 `visitor` 参数中。同一链接可以延续收藏和已读状态；清除参数或换设备会生成新的匿名身份；
- 当前真实来源必须先人工完成条款、robots 和接口许可审核；默认数据库只有演示数据；
- Streamlit 公网入口不对外暴露 FastAPI Swagger。API 文档仅供本地访问：`http://127.0.0.1:8000/docs`；
- 定时 RSS 更新默认关闭。Streamlit Community Cloud 不保证后台定时线程持续运行，生产级更新应使用独立调度任务或外部工作流。

## PostgreSQL 配置

公网需要持久化的服务端数据包括来源配置、原始文章、聚类事件、更新任务记录、匿名偏好、收藏和已读。正式 Streamlit 部署只接受 Neon PostgreSQL，不依赖临时 SQLite。

本地如需模拟公网入口，可以临时设置 `DATABASE_URL` 后运行：

```powershell
pip install -r requirements.txt
streamlit run streamlit_app.py
```

真实连接串只应放在本地环境变量或 Streamlit Secrets，不应保存到 `.env.example` 以外的受版本控制文件。

## 本地 FastAPI 网站与 API

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

打开 `http://127.0.0.1:8000` 查看本地网站；API 文档仅在本地通过 `http://127.0.0.1:8000/docs` 访问。

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

## Docker 自托管备用方案

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

CI 配置位于 `.github/workflows/ci.yml`，每次提交都会执行全部测试、Streamlit 入口编译、前端语法检查和备用 Docker 镜像构建。

本地 FastAPI 主要接口：

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

## 本地静态前端 Demo

```powershell
python -m http.server 4173 --directory frontend
```

打开 `http://127.0.0.1:4173/`。

## 测试

```powershell
pytest -q
```

测试命令会执行后端单元测试、API 集成测试、Streamlit 服务层测试和部署契约测试，并要求后端代码覆盖率不低于 80%。

```powershell
node --check frontend/app.js
python -m py_compile streamlit_app.py
```

MVP 使用本地样例数据和可替换的 AI 加工接口，不接入付费 API，也不抓取新闻网站。
