"""
X（旧 Twitter）トレンドデータ収集モジュール
Nitter RSS → Twitter API v2 → pytrends の順でフォールバック。
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

import feedparser
import requests

from trend_keyword_tool import config

logger = logging.getLogger(__name__)


@dataclass
class TrendItem:
    keyword: str
    source: str
    fetched_at: datetime


def _fetch_nitter_rss(instance: str, query: str) -> List[TrendItem]:
    """Nitter インスタンスから RSS を取得する。"""
    encoded = quote(query)
    url = f"{instance}/search/rss?q={encoded}&lang={config.NITTER_LANG}"
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries:
            title = entry.get("title", "")
            if title:
                items.append(TrendItem(keyword=title, source="nitter", fetched_at=datetime.now()))
        logger.info("Nitter(%s) fetched %d items", instance, len(items))
        return items
    except Exception as exc:
        logger.warning("Nitter %s failed: %s", instance, exc)
        return []


def _fetch_pytrends_realtime() -> List[TrendItem]:
    """pytrends でリアルタイム急上昇ワードを取得する（フォールバック）。"""
    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl=config.PYTRENDS_HL, tz=config.PYTRENDS_TZ)
        trending = pt.trending_searches(pn="japan")
        items = [
            TrendItem(keyword=str(kw), source="pytrends_realtime", fetched_at=datetime.now())
            for kw in trending[0].tolist()
        ]
        logger.info("pytrends realtime fetched %d keywords", len(items))
        return items
    except Exception as exc:
        logger.error("pytrends realtime failed: %s", exc)
        return []


def fetch_x_trends() -> List[TrendItem]:
    """
    X トレンドデータを取得する。
    Nitter RSS → pytrends の順でフォールバック。
    """
    items: List[TrendItem] = []

    # Nitter インスタンスを順番に試す
    for instance in config.NITTER_INSTANCES:
        result = _fetch_nitter_rss(instance, config.NITTER_SEARCH_QUERY)
        if result:
            items.extend(result)
            break
        time.sleep(1)

    # Nitter が全滅した場合は pytrends にフォールバック
    if not items:
        logger.info("Nitter unavailable, falling back to pytrends realtime")
        items = _fetch_pytrends_realtime()

    return items
