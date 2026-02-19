"""
コンソール / Markdown レポート生成モジュール
"""

from datetime import datetime
from typing import List, Tuple

from trend_keyword_tool.analyzers.keyword_generator import KeywordCandidate
from trend_keyword_tool.analyzers.spike_scorer import classify_spike
from trend_keyword_tool import config


def print_spike_report(scored_keywords: List[Tuple[str, float]], top_n: int = None) -> None:
    """急上昇ワードランキングをコンソールに出力する。"""
    if top_n is None:
        top_n = config.TOP_N_KEYWORDS

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "=" * 60
    print(f"\n{line}")
    print(f"  トレンドキーワード予測レポート")
    print(f"  生成日時: {now}")
    print(f"{line}")

    print(f"\n【急上昇予測 TOP {top_n}】\n")
    header = f"{'rank':>4} | {'キーワード':<25} | {'Spike':>6} | {'判定':<10}"
    print(header)
    print("-" * len(header))

    for rank, (keyword, score) in enumerate(scored_keywords[:top_n], start=1):
        label = classify_spike(score)
        print(f"{rank:>4} | {keyword:<25} | {score:>6.2f} | {label:<10}")

    print()


def print_longtail_report(
    base_keyword: str,
    candidates: List[KeywordCandidate],
    top_n: int = 10,
) -> None:
    """急上昇ワード+◯◯ 新規キーワード予測をコンソールに出力する。"""
    line = "=" * 60
    print(f"\n{line}")
    print(f"  急上昇ワード+◯◯ 新規キーワード予測")
    print(f"  ベースワード: 【{base_keyword}】")
    print(f"{line}")
    print()

    if not candidates:
        print("  候補なし（PV 見込み 1 万以上のキーワードが見つかりませんでした）")
        return

    header = f"  {'予測キーワード':<35} {'PV見込み':>8}  {'スコア':>6}  {'出典'}"
    print(header)
    print("  " + "─" * (len(header) - 2))

    for c in candidates[:top_n]:
        pv_str = f"{c.pv_estimate:,}" if c.pv_estimate > 0 else "推定中"
        print(f"  {c.full_keyword:<35} {pv_str:>8}  {c.combined_score:>6.4f}  {c.source}")

    pv_ok = [c for c in candidates if c.pv_estimate >= config.PV_MIN_THRESHOLD]
    print(f"\n  ✓ 1万PV超え候補: {len(pv_ok)} 件 / 総候補: {len(candidates)} 件")
    print()


def generate_markdown_report(
    spike_keywords: List[Tuple[str, float]],
    longtail_map: dict,
) -> str:
    """
    Markdown 形式のレポート文字列を生成する。

    Args:
        spike_keywords: [(keyword, spike_score), ...]
        longtail_map  : {base_keyword: [KeywordCandidate, ...]}
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# トレンドキーワード予測レポート",
        f"",
        f"**生成日時**: {now}",
        f"",
        f"---",
        f"",
        f"## 急上昇ワード TOP {config.TOP_N_KEYWORDS}",
        f"",
        f"| rank | キーワード | Spike Score | 判定 |",
        f"|------|-----------|-------------|------|",
    ]
    for rank, (kw, score) in enumerate(spike_keywords[: config.TOP_N_KEYWORDS], start=1):
        label = classify_spike(score)
        lines.append(f"| {rank} | {kw} | {score:.2f} | {label} |")

    lines += ["", "---", "", "## 急上昇ワード+◯◯ 新規キーワード予測", ""]
    for base_kw, candidates in longtail_map.items():
        lines.append(f"### {base_kw}")
        lines.append("")
        lines.append("| キーワード | PV見込み | スコア | 出典 |")
        lines.append("|-----------|---------|-------|------|")
        for c in candidates[:10]:
            pv_str = f"{c.pv_estimate:,}" if c.pv_estimate > 0 else "-"
            lines.append(f"| {c.full_keyword} | {pv_str} | {c.combined_score:.4f} | {c.source} |")
        lines.append("")

    return "\n".join(lines)
