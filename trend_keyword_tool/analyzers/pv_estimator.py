"""
PV 見込みスコア算出モジュール

PV_estimate = search_volume × CTR(rank=1) × (1 / competition_factor)

search_volume    : pytrends の相対値を実数換算（0〜100 → 実数換算）
CTR(rank=1)      : ≈ 28%（検索 1 位想定）
competition_factor: Google 検索結果件数から算出（0〜1）
"""

import logging
import time
from typing import Optional

import requests

from trend_keyword_tool import config

logger = logging.getLogger(__name__)

# 検索 1 位の CTR（Sistrix 2023 調査基準）
_CTR_RANK1 = 0.28

# pytrends の 100 スコアを換算する基準月間検索数（経験的定数）
_TRENDS_100_BASELINE = 50_000  # 100 = 月間 5 万検索と仮定


def _get_trends_score(keyword: str) -> float:
    """
    pytrends でキーワードの検索需要スコア（0〜100）を取得する。
    失敗時は 0 を返す。
    """
    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl=config.PYTRENDS_HL, tz=config.PYTRENDS_TZ)
        pt.build_payload([keyword], geo=config.PYTRENDS_GEO, timeframe=config.PYTRENDS_TIMEFRAME)
        df = pt.interest_over_time()
        if df is None or df.empty:
            return 0.0
        score = float(df[keyword].mean())
        time.sleep(config.PYTRENDS_REQUEST_DELAY)
        return score
    except Exception as exc:
        logger.debug("pytrends score 取得失敗 [%s]: %s", keyword, exc)
        return 0.0


def _get_competition_factor(keyword: str) -> float:
    """
    Google 検索結果件数から競合度スコア（0〜1）を算出する。
    結果件数が多いほど 1 に近づく。
    """
    try:
        url = f"https://www.google.co.jp/search?q={requests.utils.quote(keyword)}&hl=ja&gl=JP"
        resp = requests.get(
            url,
            headers=config.REQUEST_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        )
        # 検索結果件数は HTML からパースするのが困難なため、
        # 簡易的にレスポンスのサイズを競合指標の代理変数として使用
        size = len(resp.content)
        # 100KB 未満 → 低競合、500KB 以上 → 高競合（経験的）
        factor = min(size / 500_000, 1.0)
        return round(factor, 3)
    except Exception as exc:
        logger.debug("競合度取得失敗 [%s]: %s", keyword, exc)
        return 0.5  # 不明の場合は中程度とみなす


def estimate_pv(keyword: str) -> int:
    """
    キーワードの月間 PV 見込みを推定して返す。

    Args:
        keyword: 推定対象のキーワード（"急上昇ワード + ◯◯" の完成形）

    Returns:
        月間 PV 見込み（整数）
    """
    trends_score = _get_trends_score(keyword)
    competition = _get_competition_factor(keyword)

    search_volume = trends_score / 100.0 * _TRENDS_100_BASELINE
    pv = int(search_volume * _CTR_RANK1 * (1.0 / max(competition, 0.01)))

    logger.debug(
        "PV推定 [%s]: trends=%.1f, competition=%.3f → PV=%d",
        keyword, trends_score, competition, pv,
    )
    return pv


class PVEstimator:
    """
    PV 見込みスコアを計算する callable クラス。
    keyword_generator の pv_estimator 引数に渡して使う。
    """

    def __call__(self, keyword: str) -> int:
        return estimate_pv(keyword)
