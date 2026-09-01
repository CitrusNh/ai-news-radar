from backend.app.models import Source
from backend.app.source_catalog import PUBLIC_SOURCE_CATALOG, ensure_public_sources
from backend.app.store import InMemoryStore


def test_public_catalog_covers_every_visible_domain_with_multiple_sources():
    domains = {"AI", "科技", "财经", "娱乐", "体育", "游戏"}
    assert {source.domain for source in PUBLIC_SOURCE_CATALOG} == domains
    assert all(sum(source.domain == domain for source in PUBLIC_SOURCE_CATALOG) >= 3 for domain in domains)
    assert any(source.fetch_mode == "html" for source in PUBLIC_SOURCE_CATALOG)
    assert all(source.feed_url.startswith("https://") for source in PUBLIC_SOURCE_CATALOG)


def test_ensure_public_sources_is_idempotent_and_refreshes_configuration():
    store = InMemoryStore()
    assert ensure_public_sources(store) == len(PUBLIC_SOURCE_CATALOG)
    assert ensure_public_sources(store) == 0
    first = PUBLIC_SOURCE_CATALOG[0]
    store.sources[first.id] = Source(first.id, "过期名称")
    assert ensure_public_sources(store) == 1
    assert store.sources[first.id] == first
