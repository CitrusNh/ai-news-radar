const NEWS = [
  { id: 1, channel: "模型与产品", type: "MODEL RELEASE", color: "", time: "35 分钟前", source: "OpenAI", sourceMark: "O", sourceColor: "green", sources: 4, heat: 96, relevance: 94, title: "OpenAI 发布新一代推理模型，复杂任务准确率再上一个台阶", summary: "新模型针对长链路推理与工具调用做了系统性优化，首批 API 能力已向开发者开放。", facts: ["支持更长上下文与多步任务规划", "开发者预览版现已开放申请", "定价策略仍待官方进一步说明"], why: "你关注了“推理模型”；该事件由 4 个公开来源交叉报道。", entities: ["OpenAI", "推理模型", "API"], uncertainty: "中", detail: "官方公告确认了模型的推理能力与开发者预览计划，但完整定价和企业可用范围仍需等待后续说明。", link: "https://openai.com/news/" },
  { id: 2, channel: "企业应用", type: "ENTERPRISE", color: "coral", time: "1 小时前", source: "The Information", sourceMark: "T", sourceColor: "coral", sources: 3, heat: 91, relevance: 89, title: "制造业 AI 采购从“试点”进入规模化，企业开始重算 ROI", summary: "多家制造企业将 AI 项目从创新部门移交到业务线，采购关注点转向可量化的效率收益。", facts: ["质检与客服仍是最常见落地场景", "采购周期比去年平均缩短约 20%", "数据治理成为部署前置条件"], why: "你关注了“企业应用”；这是今天最具落地信号的事件之一。", entities: ["制造业", "企业采购", "ROI"], uncertainty: "低", detail: "公开报道和企业案例都显示，AI 采购正在从概念验证走向业务部门负责的长期项目。", link: "https://www.theinformation.com/" },
  { id: 3, channel: "政策安全", type: "POLICY / SAFETY", color: "yellow", time: "2 小时前", source: "MIT Technology Review", sourceMark: "M", sourceColor: "", sources: 5, heat: 88, relevance: 82, title: "全球 AI 安全评测开始趋向统一，模型厂商面临新的透明度要求", summary: "监管机构与研究组织正在推动更可比的评测框架，重点关注高风险能力的披露方式。", facts: ["评测指标从单项能力扩展到系统风险", "企业需保留模型版本与测试记录", "标准仍处在协商与试点阶段"], why: "5 个来源指向同一趋势，值得提前关注合规准备。", entities: ["AI 安全", "模型评测", "监管"], uncertainty: "中", detail: "目前更像是多个监管和研究组织正在形成的共同方向，而非一项已经生效的统一法规。", link: "https://www.technologyreview.com/" },
  { id: 4, channel: "模型与产品", type: "PRODUCT UPDATE", color: "", time: "3 小时前", source: "Google DeepMind", sourceMark: "G", sourceColor: "green", sources: 2, heat: 84, relevance: 80, title: "Gemini 新增实时协作能力，AI 从“回答问题”走向“共同工作”", summary: "更新后的工作流允许用户在文档和代码环境中持续调整目标，模型会保留任务上下文。", facts: ["支持跨文档的任务状态保存", "协作功能先面向 Workspace 用户", "开发者可通过新接口接入"], why: "产品形态出现明显变化，可能影响下一代 AI 助手设计。", entities: ["Gemini", "协作", "Workspace"], uncertainty: "低", detail: "该更新把模型放进更长时间跨度的工作流里，产品价值从单次问答转向持续协作。", link: "https://deepmind.google/" },
  { id: 5, channel: "资本市场", type: "CAPITAL", color: "coral", time: "4 小时前", source: "Bloomberg", sourceMark: "B", sourceColor: "coral", sources: 3, heat: 82, relevance: 76, title: "欧洲 AI 基础设施融资升温，算力与能源绑定成为新叙事", summary: "新一轮投资关注数据中心、电力和模型服务的组合方案，资本市场开始重新评估基础设施的边界。", facts: ["数据中心项目获得长期电力协议", "投资人更关注现金流而非模型参数", "区域监管仍是主要不确定因素"], why: "资本正在从模型层向算力和能源层外溢。", entities: ["AI 基础设施", "算力", "能源"], uncertainty: "中", detail: "目前公开信息主要来自融资披露和市场报道，具体项目回报周期仍需更多数据验证。", link: "https://www.bloomberg.com/" },
  { id: 6, channel: "模型与产品", type: "OPEN SOURCE", color: "", time: "5 小时前", source: "Hugging Face", sourceMark: "H", sourceColor: "green", sources: 2, heat: 78, relevance: 91, title: "开源社区发布轻量级多模态模型，端侧部署门槛继续下降", summary: "新模型在消费级 GPU 上即可运行，开发者可以更低成本尝试图像、文本和语音组合任务。", facts: ["7B 规模模型支持图文输入", "提供量化版本与推理脚本", "社区许可允许研究与原型使用"], why: "与你关注的“多模态”匹配，且可能降低产品原型成本。", entities: ["开源模型", "多模态", "端侧部署"], uncertainty: "低", detail: "模型卡片和代码仓库已公开，但不同硬件下的实际性能仍需要独立测试。", link: "https://huggingface.co/" },
  { id: 7, channel: "企业应用", type: "WORKFLOW", color: "coral", time: "6 小时前", source: "Microsoft AI", sourceMark: "M", sourceColor: "", sources: 2, heat: 76, relevance: 85, title: "企业开始把 AI Agent 接入审批和运营流程，而非单独部署聊天机器人", summary: "新的企业案例显示，Agent 的价值正在从对话体验转向跨系统执行和流程自动化。", facts: ["常见入口是销售、采购和 IT 服务台", "权限管理成为落地关键", "人工审核仍保留在高风险节点"], why: "这是“AI Agent”从概念走向工作流的落地信号。", entities: ["AI Agent", "工作流", "权限管理"], uncertainty: "中", detail: "案例数量正在增加，但不同企业对 Agent 的定义并不完全一致，不能简单横向比较效果。", link: "https://blogs.microsoft.com/" },
  { id: 8, channel: "政策安全", type: "SAFETY", color: "yellow", time: "7 小时前", source: "Stanford HAI", sourceMark: "S", sourceColor: "", sources: 2, heat: 73, relevance: 78, title: "研究团队提出新的 Agent 风险基准，关注模型自主执行时的边界", summary: "基准测试覆盖任务规划、工具调用和越权行为，为评估 Agent 的可控性提供统一样例。", facts: ["加入了长任务与失败恢复测试", "强调日志和可追溯性", "基准代码将公开发布"], why: "对设计安全的 Agent 产品有直接参考价值。", entities: ["Agent 安全", "评测基准", "工具调用"], uncertainty: "低", detail: "这是研究基准而非监管要求，适合作为产品测试方法的参考。", link: "https://hai.stanford.edu/" },
  { id: 9, channel: "资本市场", type: "MARKET", color: "coral", time: "8 小时前", source: "TechCrunch", sourceMark: "T", sourceColor: "coral", sources: 4, heat: 71, relevance: 73, title: "AI 应用公司融资逻辑变化：从“模型能力”转向“客户留存”", summary: "投资人开始要求 AI 应用证明重复使用率和毛利改善，产品分发和工作流粘性成为新指标。", facts: ["垂直场景融资占比提升", "客户续费成为核心追问", "模型成本下降带来毛利空间"], why: "可帮助你理解 AI 商业化叙事正在如何变化。", entities: ["AI 应用", "融资", "客户留存"], uncertainty: "中", detail: "趋势来自多笔公开融资与投资人访谈，尚不足以代表所有 AI 应用公司的融资标准。", link: "https://techcrunch.com/" },
  { id: 10, channel: "模型与产品", type: "RESEARCH", color: "", time: "9 小时前", source: "Anthropic", sourceMark: "A", sourceColor: "green", sources: 2, heat: 69, relevance: 86, title: "新研究显示：更好的上下文管理可能比更大的模型更重要", summary: "研究者将注意力放在任务拆解、上下文压缩和记忆策略，给应用层优化提供了新方向。", facts: ["长上下文并不等于有效利用", "分层记忆能降低推理成本", "应用侧提示设计仍有较大空间"], why: "与你关注的模型产品设计相关，适合加入研究清单。", entities: ["上下文管理", "模型优化", "记忆"], uncertainty: "低", detail: "研究结论基于特定任务集合，落到不同应用时需要重新测试。", link: "https://www.anthropic.com/research" },
  { id: 11, channel: "企业应用", type: "CASE STUDY", color: "coral", time: "10 小时前", source: "AWS Machine Learning", sourceMark: "A", sourceColor: "", sources: 2, heat: 66, relevance: 81, title: "零售企业用生成式 AI 重做客服知识库，响应时间缩短近一半", summary: "项目重点不在单一模型，而在知识更新、人工复核和效果监控组成的完整闭环。", facts: ["先从内部知识问答开始", "建立了人工升级通道", "效果按解决率和满意度衡量"], why: "体现了 AI 项目从 Demo 到持续运营的关键路径。", entities: ["零售", "客服", "知识库"], uncertainty: "中", detail: "案例数据由企业公开，具体效果与业务规模和流程设计有关。", link: "https://aws.amazon.com/machine-learning/" },
  { id: 12, channel: "模型与产品", type: "PRODUCT UPDATE", color: "", time: "11 小时前", source: "Meta AI", sourceMark: "M", sourceColor: "green", sources: 3, heat: 63, relevance: 79, title: "社交平台把生成式 AI 工具前置到创作入口，竞争转向默认可用", summary: "从图片编辑到短视频辅助，AI 能力开始以低门槛方式嵌入用户已有的创作流程。", facts: ["用户无需单独进入 AI 应用", "内容生成和编辑合并到同一入口", "平台需要新增内容标识机制"], why: "观察 AI 能力如何从独立产品变成基础功能。", entities: ["生成式 AI", "内容创作", "平台"], uncertainty: "低", detail: "该趋势反映产品分发方式变化，不代表所有用户都会长期使用相关功能。", link: "https://ai.meta.com/" }
];

const DOMAINS = [
  { id: "全部", label: "全部", count: 12, status: "" },
  { id: "AI", label: "AI", count: 12, status: "当前已接入" },
  { id: "科技", label: "科技", count: 0, status: "即将接入" },
  { id: "财经", label: "财经", count: 0, status: "即将接入" },
  { id: "娱乐", label: "娱乐", count: 0, status: "即将接入" },
  { id: "体育", label: "体育", count: 0, status: "即将接入" },
  { id: "游戏", label: "游戏", count: 0, status: "即将接入" }
];
const SUBCHANNELS = {
  "全部": [{ id: "全部", label: "全部", count: 12 }],
  AI: [{ id: "全部", label: "全部", count: 12 }, { id: "模型与产品", label: "模型与产品", count: 5 }, { id: "企业应用", label: "企业应用", count: 3 }, { id: "政策安全", label: "政策安全", count: 2 }, { id: "资本市场", label: "资本市场", count: 2 }],
  科技: [{ id: "全部", label: "全部", count: 0 }, { id: "消费电子", label: "消费电子", count: 0 }, { id: "芯片与算力", label: "芯片与算力", count: 0 }, { id: "软件与互联网", label: "软件与互联网", count: 0 }],
  财经: [{ id: "全部", label: "全部", count: 0 }, { id: "宏观经济", label: "宏观经济", count: 0 }, { id: "公司动态", label: "公司动态", count: 0 }, { id: "市场投资", label: "市场投资", count: 0 }],
  娱乐: [{ id: "全部", label: "全部", count: 0 }, { id: "影视音乐", label: "影视音乐", count: 0 }, { id: "明星动态", label: "明星动态", count: 0 }],
  体育: [{ id: "全部", label: "全部", count: 0 }, { id: "足球", label: "足球", count: 0 }, { id: "篮球", label: "篮球", count: 0 }, { id: "综合赛事", label: "综合赛事", count: 0 }],
  游戏: [{ id: "全部", label: "全部", count: 0 }, { id: "主机与 PC", label: "主机与 PC", count: 0 }, { id: "手游", label: "手游", count: 0 }, { id: "电竞", label: "电竞", count: 0 }]
};
const state = { domain: "AI", channel: "全部", search: "", sort: "heat", saved: new Set(JSON.parse(localStorage.getItem("signal-saved") || "[]")), read: new Set(JSON.parse(localStorage.getItem("signal-read") || "[]")), muted: new Set(JSON.parse(localStorage.getItem("signal-muted") || "[]")), keywords: new Set(JSON.parse(localStorage.getItem("signal-keywords") || '["AI Agent"]')), sourceMutes: new Set(JSON.parse(localStorage.getItem("signal-source-mutes") || "[]")) };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function saveState() {
  localStorage.setItem("signal-saved", JSON.stringify([...state.saved]));
  localStorage.setItem("signal-read", JSON.stringify([...state.read]));
  localStorage.setItem("signal-muted", JSON.stringify([...state.muted]));
  localStorage.setItem("signal-keywords", JSON.stringify([...state.keywords]));
  localStorage.setItem("signal-source-mutes", JSON.stringify([...state.sourceMutes]));
}

function visibleNews() {
  if (state.domain !== "AI" && state.domain !== "全部") return [];
  let list = NEWS.filter(item => !state.muted.has(item.id) && !state.sourceMutes.has(item.source));
  if (state.domain === "AI" && state.channel !== "全部") list = list.filter(item => item.channel === state.channel);
  if (state.search.trim()) { const q = state.search.toLowerCase(); list = list.filter(item => [item.title, item.summary, item.source, ...item.entities, ...item.facts].join(" ").toLowerCase().includes(q)); }
  if (state.sort === "fresh") list.sort((a,b) => a.id - b.id);
  if (state.sort === "relevance") list.sort((a,b) => b.relevance - a.relevance);
  if (state.sort === "heat") list.sort((a,b) => b.heat - a.heat);
  return list;
}

function cardTemplate(item) {
  const saved = state.saved.has(item.id), read = state.read.has(item.id);
  return `<article class="news-card ${read ? "is-read" : ""}" data-id="${item.id}">
    <span class="card-accent ${item.color}"></span>
    <div class="card-content">
      <div class="card-topline"><span class="category-label ${item.color}">${item.type}</span><span class="time-label">${item.time}</span><span class="source-count">· ${item.sources} 个来源</span></div>
      <h3 class="card-title">${item.title}</h3>
      <p class="card-summary">${item.summary}</p>
      <ul class="fact-list">${item.facts.map(f => `<li>${f}</li>`).join("")}</ul>
      <div class="card-bottom"><span class="source-link"><span class="source-logo ${item.sourceColor}">${item.sourceMark}</span>${item.source}</span><span class="why-matters">${item.why}</span></div>
    </div>
    <div class="card-actions"><span class="heat-badge ${item.color}">${item.heat} 热度</span><div class="action-row"><button class="card-action ${saved ? "saved" : ""}" data-action="save" aria-label="${saved ? "取消收藏" : "收藏"}" title="${saved ? "取消收藏" : "收藏"}">${saved ? "★" : "☆"}</button><button class="card-action ${read ? "read" : ""}" data-action="read" aria-label="标记已读" title="标记已读">${read ? "✓" : "○"}</button><button class="card-action" data-action="mute" aria-label="不感兴趣" title="不感兴趣">⊘</button><button class="card-action" data-action="open" aria-label="查看详情" title="查看详情">↗</button></div></div>
  </article>`;
}

function render() {
  const list = visibleNews();
  renderDomainTabs();
  renderChannelTabs();
  $("#newsFeed").innerHTML = list.map(cardTemplate).join("");
  $("#emptyState").classList.toggle("hidden", list.length > 0);
  $("#loadMore").classList.toggle("hidden", list.length === 0);
  $("#visibleCount").textContent = list.length;
  $("#savedCount").textContent = state.saved.size;
  $("#readCount").textContent = state.read.size;
  $("#mutedCount").textContent = state.muted.size + state.sourceMutes.size;
  $("#filterBadge").textContent = state.keywords.size + state.sourceMutes.size;
  $$(".card-action").forEach(btn => btn.addEventListener("click", handleAction));
  $$(".news-card").forEach(card => card.addEventListener("dblclick", () => openDetail(Number(card.dataset.id))));
}

function renderDomainTabs() {
  $("#domainTabs").innerHTML = DOMAINS.map(domain => `<button class="domain-tab ${state.domain === domain.id ? "active" : ""}" data-domain="${domain.id}">${domain.label} <span>${domain.count || "—"}</span></button>`).join("");
  const current = DOMAINS.find(domain => domain.id === state.domain);
  const note = $("#domainNote");
  note.textContent = current?.status || "跨主题热点";
  note.classList.toggle("soon", current?.status === "即将接入");
  $$(".domain-tab").forEach(tab => tab.addEventListener("click", () => selectDomain(tab.dataset.domain)));
}

function renderChannelTabs() {
  const channels = SUBCHANNELS[state.domain] || SUBCHANNELS.AI;
  $("#channelTabs").innerHTML = channels.map(channel => `<button class="channel-tab ${state.channel === channel.id ? "active" : ""}" data-channel="${channel.id}">${channel.label} <span>${channel.count || "—"}</span></button>`).join("");
  $$(".channel-tab").forEach(tab => tab.addEventListener("click", () => { state.channel = tab.dataset.channel; render(); }));
}

function selectDomain(domain) {
  state.domain = domain;
  state.channel = "全部";
  state.search = "";
  $("#searchInput").value = "";
  if (domain !== "AI" && domain !== "全部") toast(`${domain} 频道正在准备中，先为你保留导航入口`);
  else toast(domain === "全部" ? "已切换到跨主题视图" : "已切换到 AI 主题");
  render();
}

function handleAction(event) {
  event.stopPropagation();
  const button = event.currentTarget, card = button.closest(".news-card"), id = Number(card.dataset.id), action = button.dataset.action;
  if (action === "save") { state.saved.has(id) ? state.saved.delete(id) : state.saved.add(id); toast(state.saved.has(id) ? "已收藏这条信号" : "已取消收藏"); }
  if (action === "read") { state.read.has(id) ? state.read.delete(id) : state.read.add(id); toast(state.read.has(id) ? "已标记为已读" : "已恢复为未读"); }
  if (action === "mute") { state.muted.add(id); toast("已隐藏这条信号，可在偏好中调整"); }
  if (action === "open") openDetail(id);
  saveState(); render();
}

function openDetail(id) {
  const item = NEWS.find(n => n.id === id); if (!item) return;
  $("#modalBody").innerHTML = `<span class="detail-kicker">${item.type} · ${item.time} · ${item.sources} 个来源</span><h2>${item.title}</h2><p class="detail-summary">${item.detail}</p><div class="detail-block"><h4>关键事实</h4><ul>${item.facts.map(f => `<li>${f}</li>`).join("")}</ul></div><div class="detail-block"><h4>为什么值得关注</h4><p class="detail-summary">${item.why}</p></div><div class="detail-block"><h4>来源与核实</h4><div class="detail-source"><span>${item.source} · 信息不确定性：${item.uncertainty}</span><a href="${item.link}" target="_blank" rel="noreferrer">查看原文 ↗</a></div></div>`;
  $("#detailModal").classList.remove("hidden");
}

function toast(message) { const el = $("#toast"); el.textContent = message; el.classList.add("show"); clearTimeout(window.__toastTimer); window.__toastTimer = setTimeout(() => el.classList.remove("show"), 2200); }

function openFilter() { $$("[data-keyword]").forEach(chip => chip.classList.toggle("active", state.keywords.has(chip.dataset.keyword))); $$("[data-source]").forEach(chip => chip.classList.toggle("active", state.sourceMutes.has(chip.dataset.source))); $("#filterModal").classList.remove("hidden"); }
function closeModals() { $$(".modal-backdrop").forEach(modal => modal.classList.add("hidden")); }

$("#searchInput").addEventListener("input", event => { state.search = event.target.value; render(); });
$("#sortSelect").addEventListener("change", event => { state.sort = event.target.value; render(); });
$("#filterButton").addEventListener("click", openFilter);
$("#filterClose").addEventListener("click", closeModals); $("#modalClose").addEventListener("click", closeModals);
$(".modal-backdrop").addEventListener("click", event => { if (event.target === event.currentTarget) closeModals(); });
$("#applyFilters").addEventListener("click", () => { state.keywords = new Set($$("[data-keyword].active").map(chip => chip.dataset.keyword)); state.sourceMutes = new Set($$("[data-source].active").map(chip => chip.dataset.source)); saveState(); closeModals(); toast("偏好已保存，雷达已更新"); render(); });
$("#keywordChips").addEventListener("click", event => { const chip = event.target.closest(".pref-chip"); if (chip) chip.classList.toggle("active"); });
$$('[data-source]').forEach(chip => chip.addEventListener("click", () => chip.classList.toggle("active")));
$$('.trend-item').forEach(item => item.addEventListener("click", () => { $("#searchInput").value = item.dataset.query; state.search = item.dataset.query; render(); window.scrollTo({ top: 490, behavior: "smooth" }); toast(`正在查看：${item.dataset.query}`); }));
$("#clearFilters").addEventListener("click", () => { state.domain = "AI"; state.channel = "全部"; state.search = ""; $("#searchInput").value = ""; render(); });
$("#viewSaved").addEventListener("click", () => { const saved = NEWS.filter(item => state.saved.has(item.id)); if (!saved.length) { toast("还没有收藏，先收藏几条感兴趣的信号吧"); return; } $("#searchInput").value = ""; state.search = ""; $("#newsFeed").innerHTML = saved.map(cardTemplate).join(""); $$(".card-action").forEach(btn => btn.addEventListener("click", handleAction)); window.scrollTo({ top: 490, behavior: "smooth" }); toast(`正在查看 ${saved.length} 条收藏`); });
$("#resetLibrary").addEventListener("click", () => { state.saved.clear(); state.read.clear(); state.muted.clear(); state.sourceMutes.clear(); saveState(); render(); toast("本地记录已清空"); });
$("#profileButton").addEventListener("click", openFilter);
$("#themeToggle").addEventListener("click", () => { document.body.classList.toggle("dark"); $("#themeToggle").textContent = document.body.classList.contains("dark") ? "☾" : "☼"; });
$("#loadMore").addEventListener("click", () => toast("这是 Demo 版本，更多信号将在接入数据源后持续更新"));
document.addEventListener("keydown", event => { if (event.key === "Escape") closeModals(); });

render();
