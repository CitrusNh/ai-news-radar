# SignalScope｜多领域热点摘要雷达

面向公众的热点新闻聚合网站。系统通过 RSS/Atom 和公开新闻列表页采集最近 7 天内容，完成 URL 去重、事件聚类、热度排序和文字摘要，并将新闻、更新记录、匿名收藏与已读状态持久化到 Neon PostgreSQL。

- GitHub：[https://github.com/CitrusNh/ai-news-radar](https://github.com/CitrusNh/ai-news-radar)
- Streamlit 公网 Demo：[https://ai-news-radarbranchmainmainfilepathappapppy-hhjj3jwd6mj57vhpez.streamlit.app/](https://ai-news-radarbranchmainmainfilepathappapppy-hhjj3jwd6mj57vhpez.streamlit.app/)

## 产品功能

- AI、科技、财经、娱乐、体育、游戏六个分类；
- 首页热点列表、关键词搜索、热度/时间/相关性排序；
- 新闻详情、文字摘要、关键事实、关注原因和来源原文；
- 匿名收藏与已读状态；
- 每天北京时间 08:00、22:00 自动更新；
- 页面手动更新，带跨进程互斥和 15 分钟冷却；
- 更新中、空结果、部分来源失败和数据库错误状态；
- 24 个内置来源，单来源失败不会阻断其他来源；
- 每个来源最多读取 30 条，只入库最近 7 天新闻，页面展示排序后的前 60 条；
- Neon PostgreSQL 持久保存全部服务端数据，不使用 Streamlit 临时 SQLite。

## 技术架构

```text
GitHub Actions（08:00 / 22:00，北京时间）
                    │
公开 RSS / Atom / HTML 新闻列表页
                    │
                    ▼
  抓取超时与重试 → 清洗 → URL 去重 → 事件聚类 → 热度与摘要
                    │
                    ▼
             Neon PostgreSQL
                    ▲
                    │
普通用户 ──HTTPS── Streamlit Community Cloud
                    │
                    └─ 分类、搜索、详情、收藏、已读、手动更新
```

采集使用 `httpx` 显式连接/读取超时，RSS/Atom 使用结构化 XML 解析，网页列表使用可配置 CSS 选择器和 BeautifulSoup。PostgreSQL advisory lock 防止 GitHub 定时任务与页面手动更新同时写入；来源和抓取任务使用增量 upsert，用户行为始终增量追加。

仓库中的 `frontend/` 与 FastAPI 服务用于本地完整网站和 API 开发；Docker/Compose 保留为自托管备用方案，不是当前公网发布方式。公网 FastAPI Swagger 不对外提供，API 文档仅在本地访问：`http://127.0.0.1:8000/docs`。

## 数据来源

内置来源覆盖 Google 新闻中文主题 RSS、OpenAI News、Google AI Blog、Microsoft AI Blog、MIT Technology Review、BBC、The Guardian、Hacker News、CoinDesk、ESPN、Eurogamer、GameSpot、PC Gamer 等。Hacker News 与 PC Gamer 使用公开 HTML 列表页，其余优先使用 RSS/Atom。

抓取器只读取无需登录即可访问的新闻列表和摘要，不实现登录绕过、验证码绕过或付费墙绕过。来源目录位于 `backend/app/source_catalog.py`，可继续增加 `rss` 或带 CSS 选择器的 `html` 来源。

实现时参考了以下开源项目的模块化来源、定时采集和失败隔离思路，没有复制其代码：

- [Ilias1988/Universal-News-Scraper](https://github.com/Ilias1988/Universal-News-Scraper)（MIT）；
- [unsolublesugar/daily-tech-news](https://github.com/unsolublesugar/daily-tech-news)（MIT）；
- [RoseSecurity/CloudPulse](https://github.com/RoseSecurity/CloudPulse)（Apache-2.0）；
- [jaesivsm/JARR](https://github.com/jaesivsm/JARR)（AGPL-3.0，仅作架构参考）。

## 公网部署

当前方案是 Streamlit Community Cloud + Neon PostgreSQL + GitHub Actions，不使用 Render。

在 [Streamlit Community Cloud](https://share.streamlit.io/) 创建应用：

| 字段 | 内容 |
|---|---|
| Repository | `CitrusNh/ai-news-radar` |
| Branch | `main` |
| Main file path | `streamlit_app.py` |

在 Streamlit 的 **App settings → Secrets** 中配置：

```toml
DATABASE_URL = "从 Neon Connect 对话框复制的 pooled PostgreSQL 连接串"
```

自动更新还需要在 GitHub 仓库的 **Settings → Secrets and variables → Actions → New repository secret** 中创建同名 `DATABASE_URL`。连接串只应由仓库所有者直接粘贴到平台 Secrets，不要写入代码、Issue、日志或聊天。

定时工作流位于 `.github/workflows/news-update.yml`，也可在 GitHub **Actions → News update → Run workflow** 手动触发。首次真实采集成功后，系统会移除原有 12 条 AI 演示新闻；新的 PostgreSQL 数据库不会自动写入演示数据。

## 本地运行

Streamlit 页面：

```powershell
pip install -r requirements.txt
$env:DATABASE_URL="your-postgresql-connection-string"
streamlit run streamlit_app.py
```

FastAPI 网站与本地 API：

```powershell
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

打开 `http://127.0.0.1:8000`，API 文档位于 `http://127.0.0.1:8000/docs`。也可在 Windows 仓库根目录运行 `./start-demo.ps1`。

单次真实更新必须通过环境变量读取 PostgreSQL 连接串：

```powershell
python -m scripts.update_news
```

## 测试与验证

```powershell
pytest -q
python -m py_compile streamlit_app.py scripts/update_news.py
node --check frontend/app.js
```

最近一次本地完整验证：`63 passed`，后端覆盖率 `92.71%`，Python 入口编译和前端 JavaScript 语法检查通过。

2026-09-01 的无数据库真实网络试跑结果：24 个来源中 21 个成功，最近 7 天得到 512 条候选新闻，六个分类均有数据，整轮约 30 秒。3 个 AI 官方来源在本机出现 SSL 握手超时，被隔离并记录为部分失败，其余来源及任务正常完成。

## 已知限制

- GitHub Actions 免费定时任务可能因平台排队晚于 08:00 或 22:00 启动，不能承诺精确到分钟；
- Streamlit 免费应用长时间无人访问会休眠，首次唤醒较慢；
- 手动更新是同步操作，当前真实试跑约 30 秒，并设有 15 分钟冷却；
- 少数海外来源可能受网络、TLS 或限流影响，失败会记录但不会中断其他来源；
- 当前摘要是基于来源摘要的规则化整理，不是付费大模型生成，也不等同于事实核查；
- 搜索是标题关键词匹配，尚未提供全文语义搜索；
- 匿名身份保存在页面 URL 的 `visitor` 参数中，同一链接可延续收藏和已读，换链接或设备会生成新身份；
- 公网仅提供 Streamlit 页面，FastAPI API 文档仍是本地访问。
