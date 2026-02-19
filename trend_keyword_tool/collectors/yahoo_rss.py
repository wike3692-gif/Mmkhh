"""
Yahoo Japan ニュース RSS 取得モジュール
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List

import feedparser
import requests

from trend_keyword_tool import config

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    summary: str
    link: str
    published: datetime
    source: str = "yahoo"


def _parse_entry(entry, feed_url: str) -> NewsItem:
    published = datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") and entry.published_parsed else datetime.now()
    return NewsItem(
        title=entry.get("title", ""),
        summary=entry.get("summary", ""),
        link=entry.get("link", ""),
        published=published,
        source="yahoo",
    )


def fetch_yahoo_rss(feeds: List[str] = None) -> List[NewsItem]:
    """
    Yahoo News RSS フィードを全カテゴリから取得して NewsItem リストを返す。
    """
    if feeds is None:
        feeds = config.YAHOO_RSS_FEEDS

    items: List[NewsItem] = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and feed.bozo_exception:
                logger.warning("RSS parse warning for %s: %s", url, feed.bozo_exception)
            for entry in feed.entries:
                items.append(_parse_entry(entry, url))
            logger.info("Fetched %d items from %s", len(feed.entries), url)
        except Exception as exc:
            logger.error("Failed to fetch RSS %s: %s", url, exc)
        time.sleep(0.5)

    return items
