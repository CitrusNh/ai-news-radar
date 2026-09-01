# SignalScope AI｜AI 热点摘要雷达

独立项目三：面向公众的 AI 行业热点摘要网站。

当前仓库包含：

- `frontend/`：使用本地模拟数据的前端 Demo；
- `backend/`：新闻条目标准化、去重、事件聚类、热点评分和 API 服务；
- `tests/`：后端单元测试、接口测试和前端关键行为说明。

## 本地启动（后端）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

打开 `http://127.0.0.1:8000/docs` 查看 API 文档。

也可以在仓库根目录运行：

```powershell
.\start-demo.ps1
```

脚本会在后台启动前端和后端。定时 RSS 任务默认关闭；只有在来源通过审核并设置环境变量后才建议启用：

```powershell
$env:SIGNALSCOPE_SCHEDULER_ENABLED="true"
$env:SIGNALSCOPE_SCHEDULER_INTERVAL_SECONDS="14400"
```

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
