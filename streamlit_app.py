from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

from backend.app.database_store import persistent_store
from backend.app.streamlit_service import (
    PUBLIC_DOMAINS,
    PUBLIC_SORTS,
    PublicDatabaseConfigurationError,
    active_action_ids,
    event_source_links,
    latest_update_at,
    latest_ingestion_run,
    list_public_events,
    manual_update_wait_seconds,
    refresh_public_news,
    resolve_public_database_url,
    toggle_action,
)
from backend.app.store import IngestionBusyError
from backend.app.workflow import IngestionCooldownError


VISITOR_PATTERN = re.compile(r"^web-[a-z0-9]{8,40}$")


@st.cache_resource(show_spinner=False)
def load_public_store(database_url: str):
    return persistent_store(database_url=database_url)


def streamlit_database_url() -> str:
    try:
        secret_value = st.secrets.get("DATABASE_URL", "")
    except Exception:
        secret_value = ""
    return resolve_public_database_url(os.environ, {"DATABASE_URL": secret_value})


def anonymous_user_id() -> str:
    candidate = str(st.query_params.get("visitor", ""))
    if VISITOR_PATTERN.fullmatch(candidate):
        return candidate
    candidate = f"web-{uuid4().hex[:16]}"
    st.query_params["visitor"] = candidate
    return candidate


def format_update_time(value: datetime | None) -> str:
    if value is None:
        return "暂无数据"
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def format_wait_time(seconds: int) -> str:
    minutes, remainder = divmod(max(0, seconds), 60)
    return f"{minutes} 分 {remainder} 秒" if minutes else f"{remainder} 秒"


def render_event(store, event, user_id: str, saved_ids: set[str], read_ids: set[str]) -> None:
    summary = event.enrichment.summary if event.enrichment else event.title
    facts = event.enrichment.key_facts if event.enrichment else [event.title]
    why = event.enrichment.why_it_matters if event.enrichment else "请通过来源原文核实。"
    source_links = event_source_links(store, event)

    with st.container(border=True):
        st.caption(f"{event.domain} · {event.channel} · {len(event.source_ids)} 个来源 · 热度 {round(event.global_heat_score)}")
        st.subheader(event.title)
        st.write(summary)
        action_columns = st.columns([1, 1, 4])
        saved = event.id in saved_ids
        read = event.id in read_ids
        if action_columns[0].button("★ 已收藏" if saved else "☆ 收藏", key=f"save-{event.id}", use_container_width=True):
            toggle_action(store, user_id, event.id, "saved")
            st.rerun()
        if action_columns[1].button("✓ 已读" if read else "○ 标记已读", key=f"read-{event.id}", use_container_width=True):
            toggle_action(store, user_id, event.id, "read")
            st.rerun()
        with st.expander("查看新闻详情"):
            st.markdown("**关键事实**")
            for fact in facts:
                st.write(f"• {fact}")
            st.markdown("**为什么值得关注**")
            st.write(why)
            st.markdown("**来源与核实**")
            if not source_links:
                st.info("当前事件没有可用的公开来源链接。")
            for index, (source_name, source_url) in enumerate(source_links, start=1):
                st.link_button(f"{source_name} · 查看原文 ↗", source_url, key=f"source-{event.id}-{index}")


def render_app() -> None:
    st.set_page_config(page_title="SignalScope AI｜热点摘要雷达", page_icon="◉", layout="wide")
    st.markdown(
        """
        <style>
        .stApp { background: #f4f1e9; color: #161b18; }
        [data-testid="stHeader"] { background: rgba(244,241,233,.92); }
        h1, h2, h3 { letter-spacing: -.02em; }
        .signal-kicker { color: #0f6b4f; font-size: .78rem; font-weight: 800; letter-spacing: .14em; }
        .signal-hero { padding: 1.25rem 0 .4rem; }
        .signal-hero h1 { font-size: clamp(2.2rem, 6vw, 4.6rem); line-height: .98; margin: .35rem 0 1rem; }
        .signal-hero p { color: #5d665f; font-size: 1.05rem; max-width: 44rem; }
        [data-testid="stMetric"] { background: rgba(255,255,255,.55); border: 1px solid #d8d4c8; padding: .8rem; border-radius: .8rem; }
        @media (max-width: 640px) { .signal-hero h1 { font-size: 2.45rem; } }
        </style>
        <div class="signal-hero">
          <div class="signal-kicker">LIVE RADAR · PUBLIC BETA</div>
          <h1>今天，什么值得<br><span style="color:#0f6b4f">被看见？</span></h1>
          <p>把分散的 AI、科技、财经、娱乐、体育与游戏新闻，整理成可搜索、可收藏、可核实的热点信号。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        database_url = streamlit_database_url()
        with st.spinner("正在连接 Neon PostgreSQL 并加载热点…"):
            store = load_public_store(database_url)
            store.reload()
    except PublicDatabaseConfigurationError as exc:
        st.error(str(exc))
        st.info("请在 Streamlit Community Cloud 的 App settings → Secrets 中配置 DATABASE_URL。")
        st.stop()
    except Exception:
        st.error("数据库连接失败，当前无法加载新闻。请稍后重试或检查 Streamlit Secrets 中的 DATABASE_URL。")
        st.stop()

    user_id = anonymous_user_id()
    latest = latest_update_at(store)
    latest_run = latest_ingestion_run(store)
    update_wait_seconds = manual_update_wait_seconds(store)
    metric_columns = st.columns(3)
    metric_columns[0].metric("精选事件", len(store.events))
    metric_columns[1].metric("活跃来源", len([source for source in store.sources.values() if source.active]))
    metric_columns[2].metric("最近数据时间", format_update_time(latest))

    with st.sidebar:
        st.header("SignalScope AI")
        st.success("Neon PostgreSQL 已连接")
        st.caption("服务端持久化：事件、来源、抓取记录、收藏与已读")
        if st.button(
            "↻ 立即更新新闻" if not update_wait_seconds else "更新冷却中",
            type="primary",
            use_container_width=True,
            disabled=bool(update_wait_seconds),
        ):
            try:
                with st.spinner("正在获取公开新闻并更新热点…"):
                    run = refresh_public_news(store)
                st.session_state["update_notice"] = (
                    f"更新完成：检查 {run.source_count} 个来源，新增 {run.article_count} 条，"
                    f"{run.error_count} 个来源失败。"
                )
                st.rerun()
            except IngestionCooldownError as exc:
                st.warning(f"刚刚已经更新过，请在 {format_wait_time(exc.retry_after_seconds)} 后再试。")
            except IngestionBusyError:
                st.warning("另一项新闻更新正在进行，请稍后重新读取数据库。")
            except Exception:
                st.error("新闻更新失败，现有数据未受影响，请稍后重试。")
        if update_wait_seconds:
            st.caption(f"为避免重复抓取，{format_wait_time(update_wait_seconds)} 后可再次手动更新。")
        if st.button("↻ 重新读取数据库", use_container_width=True):
            try:
                store.reload()
                st.session_state["last_manual_refresh"] = datetime.now(timezone.utc).isoformat()
                st.rerun()
            except Exception:
                st.error("刷新失败，已保留当前页面数据。")
        st.divider()
        if notice := st.session_state.pop("update_notice", None):
            st.success(notice)
        st.divider()
        st.caption("自动更新：每天 08:00、22:00（北京时间）")
        if latest_run:
            st.caption(
                f"最近任务：{format_update_time(latest_run.finished_at or latest_run.started_at)} · "
                f"新增 {latest_run.article_count} 条 · 失败 {latest_run.error_count} 个来源"
            )
        else:
            st.caption("最近任务：尚未执行")
        st.caption("来源包括公开 RSS/Atom 与可直接访问的公开新闻列表页。")

    controls = st.columns([1.25, 1.25, 2, 1.15])
    collection = controls[0].selectbox("浏览内容", ["热点雷达", "我的收藏", "已读"])
    domain = controls[1].selectbox("主题分类", PUBLIC_DOMAINS)
    keyword = controls[2].text_input("关键词搜索", placeholder="搜索公司、模型、产品或事件")
    sort_label = controls[3].selectbox("排序", list(PUBLIC_SORTS))

    try:
        events = list_public_events(
            store,
            user_id,
            domain=domain,
            keyword=keyword.strip(),
            sort=PUBLIC_SORTS[sort_label],
            collection=collection,
        )
        saved_ids = active_action_ids(store, user_id, "saved")
        read_ids = active_action_ids(store, user_id, "read")
    except Exception:
        st.error("读取新闻状态失败，请点击侧边栏的“重新读取数据库”后重试。")
        return

    st.divider()
    st.subheader(f"{collection} · {len(events)} 条")
    if not events:
        if domain != "全部":
            st.info(f"{domain}频道当前没有匹配数据，可以点击侧边栏的“立即更新新闻”。")
        elif keyword:
            st.info("没有匹配该关键词的热点，试试公司名、模型名或更短的关键词。")
        elif collection == "我的收藏":
            st.info("还没有收藏新闻，先在热点列表中收藏几条感兴趣的信号。")
        elif collection == "已读":
            st.info("还没有已读记录。")
        else:
            st.info("当前暂无热点新闻，请稍后刷新。")
    else:
        for event in events:
            render_event(store, event, user_id, saved_ids, read_ids)
        if len(events) == 60:
            st.caption("当前展示排序后的前 60 条热点，可通过分类或关键词缩小范围。")

    st.divider()
    st.caption("自动整理摘要仅用于信息索引，请通过来源原文核实。公网版本由 Streamlit Community Cloud 托管，正式数据存储在 Neon PostgreSQL。")


if __name__ == "__main__":
    render_app()
