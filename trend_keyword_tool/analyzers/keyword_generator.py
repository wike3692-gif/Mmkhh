"""
急上昇ワード+◯◯ 新規キーワード生成モジュール

急上昇ワード（base_keyword）を受け取り、以下 4 ソースから候補を生成する:
  ① Google Autocomplete API（無料・API キー不要）
  ② Yahoo Japan Search Suggest API
  ③ pytrends related_queries（急上昇クエリ）
  ④ カテゴリ別サフィックステンプレート

各候補に combined_score を付与し、1 万 PV 見込みでフィルタリングして返す。
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

from trend_keyword_tool import config

logger = logging.getLogger(__name__)


@dataclass
class KeywordCandidate:
    base_keyword: str
    suffix: str
    full_keyword: str
    source: str          # "autocomplete" | "yahoo_suggest" | "pytrends" | "template"
    autocomplete_rank: int = 0   # Google 提案リスト内の順位（1-indexed、0=非該当）
    trends_rising_value: float = 0.0
    pv_estimate: int = 0
    combined_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "base_keyword": self.base_keyword,
            "suffix": self.suffix,
            "full_keyword": self.full_keyword,
            "source": self.source,
            "pv_estimate": self.pv_estimate,
            "combined_score": round(self.combined_score, 4),
        }


# ─── ① Google Autocomplete API ────────────────────────────────────────

def _fetch_google_autocomplete(keyword: str) -> List[KeywordCandidate]:
    """
    Google Autocomplete API から "keyword + ◯◯" 候補を取得する。
    """
    url = config.AUTOCOMPLETE_URL.format(query=quote(keyword + " "))
    candidates = []
    try:
        resp = requests.get(
            url,
            headers=config.REQUEST_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = json.loads(resp.text)
        suggestions = data[1] if len(data) > 1 else []

        for rank, suggestion in enumerate(suggestions[: config.AUTOCOMPLETE_MAX_RESULTS], start=1):
            suggestion = str(suggestion).strip()
            if suggestion.lower() == keyword.lower():
                continue
            suffix = suggestion[len(keyword):].strip()
            if not suffix:
                continue
            candidates.append(
                KeywordCandidate(
                    base_keyword=keyword,
                    suffix=suffix,
                    full_keyword=suggestion,
                    source="autocomplete",
                    autocomplete_rank=rank,
                )
            )
    except Exception as exc:
        logger.warning("Google Autocomplete 取得失敗 [%s]: %s", keyword, exc)

    logger.info("Google Autocomplete [%s]: %d 候補", keyword, len(candidates))
    return candidates


# ─── ② Yahoo Japan Search Suggest ────────────────────────────────────

def _fetch_yahoo_suggest(keyword: str) -> List[KeywordCandidate]:
    """
    Yahoo Japan サジェスト API から候補を取得する。
    """
    url = config.YAHOO_SUGGEST_URL.format(query=quote(keyword))
    candidates = []
    try:
        resp = requests.get(
            url,
            headers=config.REQUEST_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        # Yahoo Suggest V4 の返値: {"Result": [{"Suggest": "..."}, ...]}
        results = data.get("Result", [])
        for item in results:
            suggestion = item.get("Suggest", "").strip()
            if not suggestion or suggestion.lower() == keyword.lower():
                continue
            suffix = suggestion[len(keyword):].strip()
            if not suffix:
                continue
            candidates.append(
                KeywordCandidate(
                    base_keyword=keyword,
                    suffix=suffix,
                    full_keyword=suggestion,
                    source="yahoo_suggest",
                )
            )
    except Exception as exc:
        logger.warning("Yahoo Suggest 取得失敗 [%s]: %s", keyword, exc)

    logger.info("Yahoo Suggest [%s]: %d 候補", keyword, len(candidates))
    return candidates


# ─── ③ pytrends related_queries ──────────────────────────────────────

def _fetch_pytrends_related(keyword: str) -> List[KeywordCandidate]:
    """
    pytrends の related_queries（急上昇クエリ）から候補を取得する。
    """
    candidates = []
    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl=config.PYTRENDS_HL, tz=config.PYTRENDS_TZ)
        pt.build_payload([keyword], geo=config.PYTRENDS_GEO, timeframe=config.PYTRENDS_TIMEFRAME)
        related = pt.related_queries()
        rising_df = related.get(keyword, {}).get("rising")

        if rising_df is not None and not rising_df.empty:
            for _, row in rising_df.iterrows():
                suggestion = str(row.get("query", "")).strip()
                if not suggestion or suggestion.lower() == keyword.lower():
                    continue
                suffix = suggestion[len(keyword):].strip() if suggestion.startswith(keyword) else suggestion
                rising_val = float(row.get("value", 0))
                candidates.append(
                    KeywordCandidate(
                        base_keyword=keyword,
                        suffix=suffix,
                        full_keyword=suggestion,
                        source="pytrends",
                        trends_rising_value=min(rising_val / 100.0, 1.0),
                    )
                )
        time.sleep(config.PYTRENDS_REQUEST_DELAY)
    except Exception as exc:
        logger.warning("pytrends related_queries 取得失敗 [%s]: %s", keyword, exc)

    logger.info("pytrends related [%s]: %d 候補", keyword, len(candidates))
    return candidates


# ─── ④ カテゴリ別サフィックステンプレート ──────────────────────────────

def _generate_template_candidates(keyword: str) -> List[KeywordCandidate]:
    """
    config.SUFFIX_TEMPLATES から "keyword + suffix" の候補を生成する。
    """
    candidates = []
    for category, suffixes in config.SUFFIX_TEMPLATES.items():
        for suffix in suffixes:
            full = f"{keyword} {suffix}"
            candidates.append(
                KeywordCandidate(
                    base_keyword=keyword,
                    suffix=suffix,
                    full_keyword=full,
                    source="template",
                )
            )
    logger.info("Template [%s]: %d 候補", keyword, len(candidates))
    return candidates


# ─── スコアリング ─────────────────────────────────────────────────────

def _calc_combined_score(c: KeywordCandidate) -> float:
    """
    combined_score を算出する。

    = (autocomplete_weight × rank_score)
    + (trends_weight    × trends_rising_value)
    + (template_weight  × template_score)
    """
    # Google 順位スコア: 1位→1.0、10位→0.1
    rank_score = (1.0 / c.autocomplete_rank) if c.autocomplete_rank > 0 else 0.0

    # テンプレート補完スコア
    template_score = 0.5 if c.source == "template" else 0.0

    combined = (
        0.40 * rank_score
        + 0.35 * c.trends_rising_value
        + 0.25 * template_score
    )
    return round(combined, 4)


def _deduplicate(candidates: List[KeywordCandidate]) -> List[KeywordCandidate]:
    """full_keyword の重複を排除し、同一キーワードはスコア最大のものを残す。"""
    seen: Dict[str, KeywordCandidate] = {}
    for c in candidates:
        key = c.full_keyword.lower().strip()
        if key not in seen or c.combined_score > seen[key].combined_score:
            seen[key] = c
    return list(seen.values())


# ─── メイン関数 ───────────────────────────────────────────────────────

def generate_longtail_keywords(
    base_keyword: str,
    pv_estimator=None,
) -> List[KeywordCandidate]:
    """
    急上昇ワード（base_keyword）から "急上昇ワード+◯◯" 候補を生成・スコアリングして返す。

    Args:
        base_keyword: 急上昇ワード（例: "AIエージェント"）
        pv_estimator: PV 見込みを計算する callable(full_keyword) -> int（省略可）

    Returns:
        PV 見込み ≥ 1 万 の候補リスト（combined_score 降順）
    """
    logger.info("=== [%s] 急上昇ワード+◯◯ 生成開始 ===", base_keyword)

    # 全ソースから候補収集
    all_candidates: List[KeywordCandidate] = []
    all_candidates.extend(_fetch_google_autocomplete(base_keyword))
    time.sleep(config.SUGGEST_REQUEST_DELAY)

    all_candidates.extend(_fetch_yahoo_suggest(base_keyword))
    time.sleep(config.SUGGEST_REQUEST_DELAY)

    all_candidates.extend(_fetch_pytrends_related(base_keyword))

    all_candidates.extend(_generate_template_candidates(base_keyword))

    # combined_score 算出
    for c in all_candidates:
        c.combined_score = _calc_combined_score(c)

    # 重複排除
    candidates = _deduplicate(all_candidates)

    # PV 見込み推定（estimator が提供されている場合）
    if pv_estimator is not None:
        for c in candidates:
            try:
                c.pv_estimate = pv_estimator(c.full_keyword)
            except Exception as exc:
                logger.debug("PV 推定失敗 [%s]: %s", c.full_keyword, exc)
                c.pv_estimate = 0

    # 1 万 PV フィルタリング（estimator が None の場合はスコアのみでソート）
    if pv_estimator is not None:
        filtered = [c for c in candidates if c.pv_estimate >= config.PV_MIN_THRESHOLD]
    else:
        filtered = candidates

    # combined_score → pv_estimate の優先でソート
    filtered.sort(key=lambda c: (c.pv_estimate, c.combined_score), reverse=True)

    logger.info(
        "[%s] 生成完了: 総候補 %d → PV1万超 %d 件",
        base_keyword, len(candidates), len(filtered),
    )
    return filtered
