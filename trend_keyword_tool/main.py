"""
トレンドブログ分析 キーワード選定ツール — エントリーポイント

使用例:
  python -m trend_keyword_tool.main --mode full --export csv
  python -m trend_keyword_tool.main --mode collect
  python -m trend_keyword_tool.main --mode predict --export json
  python -m trend_keyword_tool.main --keyword "AIエージェント"
"""

import argparse
import logging
import sys
from typing import Dict, List, Tuple

from trend_keyword_tool import config
from trend_keyword_tool.analyzers.keyword_generator import KeywordCandidate, generate_longtail_keywords
from trend_keyword_tool.analyzers.pv_estimator import PVEstimator
from trend_keyword_tool.analyzers.spike_scorer import get_rising_keywords, score_all_keywords
from trend_keyword_tool.collectors.yahoo_rss import fetch_yahoo_rss
from trend_keyword_tool.collectors.x_trends import fetch_x_trends
from trend_keyword_tool.outputs.exporter import export_json, export_longtail_csv, export_spike_csv
from trend_keyword_tool.outputs.reporter import (
    generate_markdown_report,
    print_longtail_report,
    print_spike_report,
)
from trend_keyword_tool.processors.keyword_extractor import count_keywords
from trend_keyword_tool.storage.keyword_store import (
    init_db,
    record_keywords,
    save_generated_keywords,
    save_prediction,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── ステップ別処理 ──────────────────────────────────────────────────

def step_collect() -> Dict[str, int]:
    """データ収集 → キーワード抽出 → DB 記録。抽出したキーワード頻度 dict を返す。"""
    logger.info("--- [Step 1] データ収集開始 ---")

    yahoo_items = fetch_yahoo_rss()
    x_items = fetch_x_trends()

    all_texts = (
        [f"{item.title} {item.summary}" for item in yahoo_items]
        + [item.keyword for item in x_items]
    )

    logger.info("収集テキスト数: %d", len(all_texts))
    keyword_counts = count_keywords(all_texts)
    logger.info("抽出キーワード種数: %d", len(keyword_counts))

    record_keywords(dict(keyword_counts))
    return dict(keyword_counts)


def step_predict_spike() -> List[Tuple[str, float]]:
    """Spike Score を算出して急上昇キーワードを返す。"""
    logger.info("--- [Step 2] 急上昇スコア算出 ---")
    rising = get_rising_keywords()
    logger.info("急上昇キーワード（閾値以上）: %d 件", len(rising))
    return rising


def step_generate_longtail(
    rising_keywords: List[Tuple[str, float]],
    use_pv_estimator: bool = True,
    top_n_base: int = 10,
) -> Dict[str, List[KeywordCandidate]]:
    """
    各急上昇ワードに対して "急上昇ワード+◯◯" キーワードを生成する。

    Args:
        rising_keywords : [(keyword, spike_score), ...]
        use_pv_estimator: True の場合 pytrends で PV 見込みを推定する
        top_n_base      : 処理対象とする急上昇ワードの上位 N 件

    Returns:
        {base_keyword: [KeywordCandidate, ...]} の dict
    """
    logger.info("--- [Step 3] 急上昇ワード+◯◯ キーワード生成 ---")
    pv_est = PVEstimator() if use_pv_estimator else None
    longtail_map: Dict[str, List[KeywordCandidate]] = {}

    for keyword, spike_score in rising_keywords[:top_n_base]:
        logger.info("処理中: [%s] (Spike=%.2f)", keyword, spike_score)
        candidates = generate_longtail_keywords(keyword, pv_estimator=pv_est)
        longtail_map[keyword] = candidates
        save_generated_keywords(keyword, [c.to_dict() for c in candidates])
        save_prediction(keyword, spike_score, 0, 0.0)

    return longtail_map


# ─── モード別実行 ────────────────────────────────────────────────────

def run_full(args: argparse.Namespace) -> None:
    """全ステップを順に実行する。"""
    init_db()
    step_collect()
    rising = step_predict_spike()
    longtail_map = step_generate_longtail(rising, use_pv_estimator=not args.no_pv)

    # レポート出力
    all_scored = score_all_keywords()
    print_spike_report(all_scored)
    for base_kw, candidates in longtail_map.items():
        print_longtail_report(base_kw, candidates)

    # エクスポート
    if args.export in ("csv", "all"):
        export_spike_csv(all_scored)
        export_longtail_csv(longtail_map)
    if args.export in ("json", "all"):
        export_json(all_scored, longtail_map)
    if args.export == "markdown":
        md = generate_markdown_report(all_scored, longtail_map)
        path = f"exports/report_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        __import__('os').makedirs("exports", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        logger.info("Markdown report: %s", path)


def run_collect(args: argparse.Namespace) -> None:
    init_db()
    counts = step_collect()
    print(f"\n抽出キーワード上位 20:\n")
    for kw, cnt in sorted(counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {kw}: {cnt}")


def run_predict(args: argparse.Namespace) -> None:
    init_db()
    rising = step_predict_spike()
    longtail_map = step_generate_longtail(rising, use_pv_estimator=not args.no_pv)

    all_scored = score_all_keywords()
    print_spike_report(all_scored)
    for base_kw, candidates in longtail_map.items():
        print_longtail_report(base_kw, candidates)

    if args.export in ("csv", "all"):
        export_spike_csv(all_scored)
        export_longtail_csv(longtail_map)
    if args.export in ("json", "all"):
        export_json(all_scored, longtail_map)


def run_single_keyword(args: argparse.Namespace) -> None:
    """単一キーワードに対して急上昇ワード+◯◯ を生成する（デバッグ用）。"""
    init_db()
    pv_est = PVEstimator() if not args.no_pv else None
    candidates = generate_longtail_keywords(args.keyword, pv_estimator=pv_est)
    print_longtail_report(args.keyword, candidates)
    if args.export in ("csv", "all"):
        export_longtail_csv({args.keyword: candidates})
    if args.export in ("json", "all"):
        export_json([], {args.keyword: candidates})


# ─── CLI ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="トレンドブログ分析 キーワード選定ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--mode",
        choices=["full", "collect", "predict"],
        default="full",
        help="実行モード: full（全ステップ）/ collect（収集のみ）/ predict（予測のみ）",
    )
    p.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="単一キーワードに対して急上昇ワード+◯◯ を生成する（--mode を上書き）",
    )
    p.add_argument(
        "--export",
        choices=["none", "csv", "json", "markdown", "all"],
        default="none",
        help="出力形式（csv / json / markdown / all）",
    )
    p.add_argument(
        "--no-pv",
        action="store_true",
        help="PV 見込み推定をスキップする（pytrends 無効化・高速化）",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="DEBUG レベルのログを出力する",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.keyword:
        run_single_keyword(args)
        return

    runners = {
        "full": run_full,
        "collect": run_collect,
        "predict": run_predict,
    }
    runners[args.mode](args)


if __name__ == "__main__":
    main()
