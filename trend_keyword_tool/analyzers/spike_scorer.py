"""
急上昇スコア（Spike Score）算出モジュール

Spike Score(w) = freq_recent(w) / (freq_baseline(w) + ε)

freq_recent  : 直近 SPIKE_RECENT_HOURS 時間の出現頻度合計
freq_baseline: 過去 SPIKE_BASELINE_HOURS 時間の 1h あたり平均頻度
ε            : SPIKE_EPSILON（ゼロ除算防止）
"""

import logging
from typing import Dict, List, Tuple

from trend_keyword_tool import config
from trend_keyword_tool.storage import keyword_store

logger = logging.getLogger(__name__)


def _calc_spike_score(keyword: str) -> float:
    freq_recent = keyword_store.get_recent_frequency(keyword, config.SPIKE_RECENT_HOURS)
    freq_baseline_total = keyword_store.get_recent_frequency(keyword, config.SPIKE_BASELINE_HOURS)

    # 1h あたり平均（直近期間分を除外した厳密計算は近似で対応）
    baseline_hours = config.SPIKE_BASELINE_HOURS - config.SPIKE_RECENT_HOURS
    if baseline_hours <= 0:
        baseline_hours = config.SPIKE_BASELINE_HOURS
    freq_baseline_per_hour = max(
        (freq_baseline_total - freq_recent) / baseline_hours,
        0,
    )
    freq_baseline = freq_baseline_per_hour * config.SPIKE_RECENT_HOURS

    score = freq_recent / (freq_baseline + config.SPIKE_EPSILON)
    return round(score, 2)


def score_all_keywords() -> List[Tuple[str, float]]:
    """
    直近ウィンドウ内の全キーワードに Spike Score を付与してリストで返す。
    スコア降順でソート済み。
    """
    keywords = keyword_store.get_all_keywords_in_window(config.SPIKE_BASELINE_HOURS)
    scored = []
    for kw in keywords:
        score = _calc_spike_score(kw)
        scored.append((kw, score))
        logger.debug("Spike Score [%s] = %.2f", kw, score)

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def get_rising_keywords(min_score: float = None) -> List[Tuple[str, float]]:
    """
    Spike Score が閾値以上のキーワードのみを返す。
    min_score 未指定の場合は config.SPIKE_RISING_THRESHOLD を使用。
    """
    if min_score is None:
        min_score = config.SPIKE_RISING_THRESHOLD
    return [(kw, sc) for kw, sc in score_all_keywords() if sc >= min_score]


def classify_spike(score: float) -> str:
    if score >= config.SPIKE_ALERT_THRESHOLD:
        return "急上昇確定"
    elif score >= config.SPIKE_RISING_THRESHOLD:
        return "上昇傾向"
    elif score >= 1.5:
        return "微上昇"
    else:
        return "通常"
