"""
CSV / JSON エクスポートモジュール
"""

import csv
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

from trend_keyword_tool import config
from trend_keyword_tool.analyzers.keyword_generator import KeywordCandidate

logger = logging.getLogger(__name__)


def _ensure_export_dir() -> str:
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    return config.EXPORT_DIR


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def export_spike_csv(scored_keywords: List[Tuple[str, float]]) -> str:
    """急上昇スコアランキングを CSV に出力する。"""
    out_dir = _ensure_export_dir()
    filename = os.path.join(out_dir, f"spike_{_timestamp()}.csv")
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "keyword", "spike_score"])
        for rank, (kw, score) in enumerate(scored_keywords, start=1):
            writer.writerow([rank, kw, round(score, 2)])
    logger.info("CSV exported: %s", filename)
    return filename


def export_longtail_csv(longtail_map: Dict[str, List[KeywordCandidate]]) -> str:
    """急上昇ワード+◯◯ キーワードを CSV に出力する。"""
    out_dir = _ensure_export_dir()
    filename = os.path.join(out_dir, f"longtail_{_timestamp()}.csv")
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "base_keyword", "suffix", "full_keyword",
            "source", "pv_estimate", "combined_score",
        ])
        for base_kw, candidates in longtail_map.items():
            for c in candidates:
                writer.writerow([
                    base_kw, c.suffix, c.full_keyword,
                    c.source, c.pv_estimate, round(c.combined_score, 4),
                ])
    logger.info("CSV exported: %s", filename)
    return filename


def export_json(
    spike_keywords: List[Tuple[str, float]],
    longtail_map: Dict[str, List[KeywordCandidate]],
) -> str:
    """全結果を JSON に出力する。"""
    out_dir = _ensure_export_dir()
    filename = os.path.join(out_dir, f"report_{_timestamp()}.json")
    data = {
        "generated_at": datetime.now().isoformat(),
        "spike_keywords": [
            {"rank": i + 1, "keyword": kw, "spike_score": round(sc, 2)}
            for i, (kw, sc) in enumerate(spike_keywords)
        ],
        "longtail_keywords": {
            base_kw: [c.to_dict() for c in candidates]
            for base_kw, candidates in longtail_map.items()
        },
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("JSON exported: %s", filename)
    return filename
