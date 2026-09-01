from __future__ import annotations

from .models import Source


DEMO_SOURCE_IDS = frozenset(
    {
        "openai",
        "deepmind",
        "mit-tech-review",
        "huggingface",
        "microsoft-ai",
        "the-information",
        "bloomberg",
        "stanford-hai",
        "techcrunch",
        "anthropic",
        "aws-ml",
        "meta-ai",
    }
)


PUBLIC_SOURCE_CATALOG = (
    Source("google-news-ai", "Google 新闻·AI", domain="AI", source_type="aggregator", trust_tier=2, feed_url="https://news.google.com/rss/search?q=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD%20OR%20AI&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", robots_status="allowed", compliance_status="approved", default_channel="AI 热点"),
    Source("openai-news", "OpenAI News", domain="AI", trust_tier=3, feed_url="https://openai.com/news/rss.xml", robots_status="allowed", compliance_status="approved", default_channel="模型与产品"),
    Source("google-ai-blog", "Google AI Blog", domain="AI", trust_tier=3, feed_url="https://blog.google/technology/ai/rss/", robots_status="allowed", compliance_status="approved", default_channel="模型与产品"),
    Source("microsoft-ai-blog", "Microsoft AI Blog", domain="AI", trust_tier=3, feed_url="https://blogs.microsoft.com/ai/feed/", robots_status="allowed", compliance_status="approved", default_channel="企业应用"),
    Source("mit-tech-review-ai", "MIT Technology Review AI", domain="AI", trust_tier=2, feed_url="https://www.technologyreview.com/topic/artificial-intelligence/feed", robots_status="allowed", compliance_status="approved", default_channel="研究与趋势"),
    Source("bbc-technology", "BBC Technology", domain="科技", trust_tier=3, feed_url="https://feeds.bbci.co.uk/news/technology/rss.xml", robots_status="allowed", compliance_status="approved", default_channel="科技动态"),
    Source("guardian-technology", "The Guardian Technology", domain="科技", trust_tier=2, feed_url="https://www.theguardian.com/technology/rss", robots_status="allowed", compliance_status="approved", default_channel="科技动态"),
    Source(
        "hacker-news",
        "Hacker News",
        domain="科技",
        source_type="community",
        trust_tier=2,
        feed_url="https://news.ycombinator.com/",
        robots_status="allowed",
        compliance_status="approved",
        fetch_mode="html",
        article_selector="tr.athing",
        title_selector="span.titleline",
        link_selector="span.titleline > a",
        default_channel="开发者社区",
    ),
    Source("google-news-technology", "Google 新闻·科技", domain="科技", source_type="aggregator", trust_tier=2, feed_url="https://news.google.com/rss/search?q=%E7%A7%91%E6%8A%80&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", robots_status="allowed", compliance_status="approved", default_channel="科技动态"),
    Source("bbc-business", "BBC Business", domain="财经", trust_tier=3, feed_url="https://feeds.bbci.co.uk/news/business/rss.xml", robots_status="allowed", compliance_status="approved", default_channel="商业财经"),
    Source("guardian-business", "The Guardian Business", domain="财经", trust_tier=2, feed_url="https://www.theguardian.com/uk/business/rss", robots_status="allowed", compliance_status="approved", default_channel="商业财经"),
    Source("coindesk", "CoinDesk", domain="财经", trust_tier=2, feed_url="https://www.coindesk.com/arc/outboundfeeds/rss/", robots_status="allowed", compliance_status="approved", default_channel="数字资产"),
    Source("google-news-finance", "Google 新闻·财经", domain="财经", source_type="aggregator", trust_tier=2, feed_url="https://news.google.com/rss/search?q=%E8%B4%A2%E7%BB%8F%20OR%20%E8%82%A1%E7%A5%A8&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", robots_status="allowed", compliance_status="approved", default_channel="财经热点"),
    Source("bbc-entertainment", "BBC Entertainment & Arts", domain="娱乐", trust_tier=3, feed_url="https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", robots_status="allowed", compliance_status="approved", default_channel="影视娱乐"),
    Source("guardian-culture", "The Guardian Culture", domain="娱乐", trust_tier=2, feed_url="https://www.theguardian.com/culture/rss", robots_status="allowed", compliance_status="approved", default_channel="文化娱乐"),
    Source("google-news-entertainment", "Google 新闻·娱乐", domain="娱乐", source_type="aggregator", trust_tier=2, feed_url="https://news.google.com/rss/search?q=%E5%A8%B1%E4%B9%90%20OR%20%E7%94%B5%E5%BD%B1&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", robots_status="allowed", compliance_status="approved", default_channel="娱乐热点"),
    Source("bbc-sport", "BBC Sport", domain="体育", trust_tier=3, feed_url="https://feeds.bbci.co.uk/sport/rss.xml", robots_status="allowed", compliance_status="approved", default_channel="综合体育"),
    Source("guardian-sport", "The Guardian Sport", domain="体育", trust_tier=2, feed_url="https://www.theguardian.com/uk/sport/rss", robots_status="allowed", compliance_status="approved", default_channel="综合体育"),
    Source("espn-top", "ESPN Top Headlines", domain="体育", trust_tier=2, feed_url="https://www.espn.com/espn/rss/news", robots_status="allowed", compliance_status="approved", default_channel="综合体育"),
    Source("google-news-sports", "Google 新闻·体育", domain="体育", source_type="aggregator", trust_tier=2, feed_url="https://news.google.com/rss/search?q=%E4%BD%93%E8%82%B2%20OR%20%E8%B6%B3%E7%90%83%20OR%20%E7%AF%AE%E7%90%83&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", robots_status="allowed", compliance_status="approved", default_channel="体育热点"),
    Source("eurogamer", "Eurogamer", domain="游戏", trust_tier=2, feed_url="https://www.eurogamer.net/?format=rss", robots_status="allowed", compliance_status="approved", default_channel="游戏资讯"),
    Source("gamespot", "GameSpot", domain="游戏", trust_tier=2, feed_url="https://www.gamespot.com/feeds/mashup/", robots_status="allowed", compliance_status="approved", default_channel="游戏资讯"),
    Source("pc-gamer", "PC Gamer", domain="游戏", trust_tier=2, feed_url="https://www.pcgamer.com/news/", robots_status="allowed", compliance_status="approved", fetch_mode="html", default_channel="PC 游戏"),
    Source("google-news-games", "Google 新闻·游戏", domain="游戏", source_type="aggregator", trust_tier=2, feed_url="https://news.google.com/rss/search?q=%E6%B8%B8%E6%88%8F%20OR%20%E7%94%B5%E7%AB%9E&hl=zh-CN&gl=CN&ceid=CN:zh-Hans", robots_status="allowed", compliance_status="approved", default_channel="游戏热点"),
)


def ensure_public_sources(store) -> int:
    """Insert or refresh the built-in multi-domain public source registry."""

    return store.upsert_sources(list(PUBLIC_SOURCE_CATALOG))
