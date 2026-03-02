#!/usr/bin/env python3
"""DL同人 需要検索キーワード分析ツール

DLsiteなどの同人販売サイトからキーワードの需要を分析し、
トレンドや人気ジャンルを可視化するツール。

使い方:
    python doujinshi_keyword_analyzer.py suggest <キーワード>
    python doujinshi_keyword_analyzer.py analyze <キーワード> [--pages N]
    python doujinshi_keyword_analyzer.py ranking [--category maniax|comic|books]
    python doujinshi_keyword_analyzer.py trend <キーワード1> <キーワード2> ...
    python doujinshi_keyword_analyzer.py report <キーワード> [--output report.csv]
    python doujinshi_keyword_analyzer.py fromfile <input.csv> [--output result.csv]
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

DLSITE_SUGGEST_URL = "https://www.dlsite.com/suggest"
DLSITE_SEARCH_URL = "https://www.dlsite.com/maniax/fsr/=/language/jp/keyword/{keyword}/order/trend/per_page/30/page/{page}"
DLSITE_RANKING_URL = "https://www.dlsite.com/maniax/ranking/day"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

REQUEST_DELAY = 1.5  # リクエスト間の待機秒数(サーバー負荷軽減)

# 同人関連の主要ジャンルタグ
GENRE_TAGS = [
    "異世界", "ファンタジー", "SF", "現代", "学園", "ホラー",
    "催眠", "NTR", "純愛", "ラブコメ", "百合", "BL",
    "触手", "ロボット", "バトル", "冒険", "日常", "ミステリー",
    "RPG", "シミュレーション", "アクション", "ノベル", "CG集", "動画",
    "音声", "ASMR", "ボイスドラマ", "漫画", "同人誌",
    "巨乳", "貧乳", "ロリ", "熟女", "人妻", "妹",
    "メイド", "ナース", "女騎士", "エルフ", "魔法少女", "アイドル",
    "ツンデレ", "ヤンデレ", "クーデレ", "ギャル", "幼馴染",
    "男の娘", "ふたなり", "モンスター娘", "獣耳", "ケモノ",
]


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class WorkInfo:
    """作品情報"""
    title: str = ""
    circle: str = ""
    price: int = 0
    sales_count: int = 0
    rating: float = 0.0
    tags: list = field(default_factory=list)
    url: str = ""
    release_date: str = ""


@dataclass
class KeywordResult:
    """キーワード分析結果"""
    keyword: str = ""
    work_count: int = 0
    avg_price: int = 0
    avg_sales: int = 0
    avg_rating: float = 0.0
    top_tags: list = field(default_factory=list)
    demand_score: float = 0.0
    competition_level: str = ""


# ---------------------------------------------------------------------------
# HTMLパーサー
# ---------------------------------------------------------------------------

class DLsiteSearchParser(HTMLParser):
    """DLsite検索結果ページのHTMLパーサー"""

    def __init__(self):
        super().__init__()
        self.works = []
        self._current_work = None
        self._in_title = False
        self._in_circle = False
        self._in_price = False
        self._in_sales = False
        self._in_rating = False
        self._in_tag = False
        self._capture_text = ""
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        if "search_result_img_box" in cls or "multiline_truncate" in cls:
            if self._current_work:
                self.works.append(self._current_work)
            self._current_work = WorkInfo()

        if tag == "a" and self._current_work:
            href = attrs_dict.get("href", "")
            if "/product_id/" in href and not self._current_work.url:
                self._current_work.url = href

        if "work_name" in cls:
            self._in_title = True
            self._capture_text = ""
        elif "maker_name" in cls:
            self._in_circle = True
            self._capture_text = ""
        elif "work_price" in cls or "strike" in cls:
            self._in_price = True
            self._capture_text = ""
        elif "dl_count" in cls:
            self._in_sales = True
            self._capture_text = ""
        elif "star_rating" in cls:
            self._in_rating = True
            self._capture_text = ""
        elif "search_tag" in cls or "genre" in cls:
            self._in_tag = True
            self._capture_text = ""

    def handle_data(self, data):
        if any([self._in_title, self._in_circle, self._in_price,
                self._in_sales, self._in_rating, self._in_tag]):
            self._capture_text += data.strip()

    def handle_endtag(self, tag):
        if self._in_title and tag in ("a", "dd", "span", "div"):
            if self._current_work and self._capture_text:
                self._current_work.title = self._capture_text
            self._in_title = False
        elif self._in_circle and tag in ("a", "dd", "span", "div"):
            if self._current_work and self._capture_text:
                self._current_work.circle = self._capture_text
            self._in_circle = False
        elif self._in_price and tag in ("span", "dd", "div", "em"):
            if self._current_work and self._capture_text:
                price_text = re.sub(r"[^\d]", "", self._capture_text)
                if price_text:
                    self._current_work.price = int(price_text)
            self._in_price = False
        elif self._in_sales and tag in ("span", "dd", "div"):
            if self._current_work and self._capture_text:
                sales_text = re.sub(r"[^\d]", "", self._capture_text)
                if sales_text:
                    self._current_work.sales_count = int(sales_text)
            self._in_sales = False
        elif self._in_rating and tag in ("span", "dd", "div"):
            if self._current_work and self._capture_text:
                try:
                    self._current_work.rating = float(self._capture_text)
                except ValueError:
                    pass
            self._in_rating = False
        elif self._in_tag and tag in ("a", "span", "div"):
            if self._current_work and self._capture_text:
                self._current_work.tags.append(self._capture_text)
            self._in_tag = False

    def finalize(self):
        if self._current_work:
            self.works.append(self._current_work)
            self._current_work = None
        return [w for w in self.works if w.title]


# ---------------------------------------------------------------------------
# HTTP取得ユーティリティ
# ---------------------------------------------------------------------------

def fetch_url(url: str, retry: int = 3) -> Optional[str]:
    """URLからHTMLを取得する(リトライ付き)"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except Exception as e:
            if attempt < retry - 1:
                wait = 2 ** (attempt + 1)
                print(f"  リトライ中 ({attempt+1}/{retry}): {e}", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  取得失敗: {url} - {e}", file=sys.stderr)
                return None


def fetch_json(url: str) -> Optional[dict]:
    """URLからJSONを取得する"""
    html = fetch_url(url)
    if html is None:
        return None
    try:
        return json.loads(html)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# DLsite API 関連
# ---------------------------------------------------------------------------

def get_suggestions(keyword: str) -> list[str]:
    """DLsiteのサジェストAPIからキーワード候補を取得する"""
    encoded = urllib.parse.quote(keyword)
    url = f"{DLSITE_SUGGEST_URL}?term={encoded}&site=adult-jp&time={int(time.time()*1000)}"

    data = fetch_json(url)
    if data and isinstance(data, list):
        return [item if isinstance(item, str) else item.get("label", str(item))
                for item in data]
    return []


def search_works(keyword: str, page: int = 1) -> list[WorkInfo]:
    """DLsiteでキーワード検索し作品一覧を取得する"""
    encoded = urllib.parse.quote(keyword)
    url = DLSITE_SEARCH_URL.format(keyword=encoded, page=page)

    html = fetch_url(url)
    if html is None:
        return []

    parser = DLsiteSearchParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    return parser.finalize()


# ---------------------------------------------------------------------------
# 分析ロジック
# ---------------------------------------------------------------------------

def analyze_keyword(keyword: str, max_pages: int = 2) -> KeywordResult:
    """キーワードの需要を分析する"""
    print(f"\n  キーワード「{keyword}」を分析中...")
    all_works = []

    for page in range(1, max_pages + 1):
        print(f"    ページ {page}/{max_pages} 取得中...")
        works = search_works(keyword, page)
        if not works:
            break
        all_works.extend(works)
        if page < max_pages:
            time.sleep(REQUEST_DELAY)

    if not all_works:
        return KeywordResult(
            keyword=keyword,
            work_count=0,
            demand_score=0.0,
            competition_level="データなし",
        )

    # 基本統計
    prices = [w.price for w in all_works if w.price > 0]
    sales = [w.sales_count for w in all_works if w.sales_count > 0]
    ratings = [w.rating for w in all_works if w.rating > 0]

    avg_price = int(sum(prices) / len(prices)) if prices else 0
    avg_sales = int(sum(sales) / len(sales)) if sales else 0
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    # タグ頻度分析
    tag_counter = Counter()
    for w in all_works:
        tag_counter.update(w.tags)
    top_tags = [tag for tag, _ in tag_counter.most_common(10)]

    # 需要スコア計算
    demand_score = calculate_demand_score(
        work_count=len(all_works),
        avg_sales=avg_sales,
        avg_rating=avg_rating,
        avg_price=avg_price,
    )

    # 競争レベル判定
    competition = classify_competition(len(all_works), avg_sales)

    return KeywordResult(
        keyword=keyword,
        work_count=len(all_works),
        avg_price=avg_price,
        avg_sales=avg_sales,
        avg_rating=avg_rating,
        top_tags=top_tags,
        demand_score=round(demand_score, 2),
        competition_level=competition,
    )


def calculate_demand_score(
    work_count: int,
    avg_sales: int,
    avg_rating: float,
    avg_price: int,
) -> float:
    """需要スコアを算出する (0-100)

    スコアは以下の要素から計算:
    - 平均販売数 (重み: 40%) ... 売れている = 需要が高い
    - 平均評価   (重み: 20%) ... 高評価 = 満足度が高い
    - 作品数     (重み: 25%) ... 多い = 市場がある(ただし飽和リスク)
    - 平均価格   (重み: 15%) ... 高い = 購買意欲が高い
    """
    # 各指標を 0-100 に正規化
    sales_score = min(avg_sales / 500, 1.0) * 100  # 500DL以上で満点
    rating_score = (avg_rating / 5.0) * 100 if avg_rating > 0 else 50
    # 作品数: 少なすぎても多すぎてもスコアが下がる(20-100作品が理想)
    if work_count < 5:
        count_score = work_count * 10
    elif work_count <= 100:
        count_score = 50 + (work_count / 100) * 50
    else:
        count_score = max(100 - (work_count - 100) * 0.2, 40)
    price_score = min(avg_price / 1500, 1.0) * 100  # 1500円以上で満点

    score = (
        sales_score * 0.40
        + rating_score * 0.20
        + count_score * 0.25
        + price_score * 0.15
    )
    return min(max(score, 0), 100)


def classify_competition(work_count: int, avg_sales: int) -> str:
    """競争レベルを判定する"""
    if work_count < 10:
        return "低 (ニッチ市場)"
    elif work_count < 50:
        if avg_sales > 200:
            return "中 (成長市場)"
        return "低〜中"
    elif work_count < 200:
        if avg_sales > 500:
            return "高 (人気市場)"
        return "中 (標準的)"
    else:
        return "非常に高 (レッドオーシャン)"


def analyze_tag_cooccurrence(works: list[WorkInfo]) -> dict[str, list[str]]:
    """タグの共起関係を分析する"""
    cooccurrence = defaultdict(Counter)
    for work in works:
        tags = work.tags
        for i, tag1 in enumerate(tags):
            for tag2 in tags[i + 1:]:
                cooccurrence[tag1][tag2] += 1
                cooccurrence[tag2][tag1] += 1

    result = {}
    for tag, related in cooccurrence.items():
        result[tag] = [t for t, _ in related.most_common(5)]
    return result


def compare_keywords(keywords: list[str], max_pages: int = 1) -> list[KeywordResult]:
    """複数キーワードを比較分析する"""
    results = []
    for i, kw in enumerate(keywords):
        result = analyze_keyword(kw, max_pages=max_pages)
        results.append(result)
        if i < len(keywords) - 1:
            time.sleep(REQUEST_DELAY)
    return results


# ---------------------------------------------------------------------------
# 出力フォーマット
# ---------------------------------------------------------------------------

def print_suggestions(keyword: str, suggestions: list[str]):
    """サジェスト結果を表示する"""
    print(f"\n{'='*60}")
    print(f"  サジェスト結果: 「{keyword}」")
    print(f"{'='*60}")
    if not suggestions:
        print("  サジェストが見つかりませんでした。")
        return
    for i, s in enumerate(suggestions, 1):
        print(f"  {i:3d}. {s}")
    print(f"{'='*60}")
    print(f"  合計: {len(suggestions)} 件")


def print_analysis(result: KeywordResult):
    """分析結果を見やすく表示する"""
    print(f"\n{'='*60}")
    print(f"  キーワード分析結果: 「{result.keyword}」")
    print(f"{'='*60}")
    print(f"  作品数       : {result.work_count} 件")
    print(f"  平均価格     : ¥{result.avg_price:,}")
    print(f"  平均販売数   : {result.avg_sales:,} DL")
    print(f"  平均評価     : {'★' * int(result.avg_rating)}{' ' * (5 - int(result.avg_rating))} ({result.avg_rating})")
    print(f"  需要スコア   : {result.demand_score}/100 {demand_bar(result.demand_score)}")
    print(f"  競争レベル   : {result.competition_level}")
    if result.top_tags:
        print(f"  関連タグ     : {', '.join(result.top_tags[:10])}")
    print(f"{'='*60}")

    # 需要判定コメント
    if result.demand_score >= 70:
        print("  >> 需要が高いキーワードです。競争状況に注意して参入を検討しましょう。")
    elif result.demand_score >= 40:
        print("  >> 中程度の需要があります。差別化がポイントになります。")
    elif result.demand_score > 0:
        print("  >> 需要は限定的です。ニッチ戦略が有効かもしれません。")
    else:
        print("  >> データが不足しています。別のキーワードを試してください。")


def print_comparison(results: list[KeywordResult]):
    """キーワード比較結果を表示する"""
    print(f"\n{'='*80}")
    print("  キーワード比較分析")
    print(f"{'='*80}")

    # ヘッダー
    header = f"  {'キーワード':<16} {'作品数':>8} {'平均価格':>10} {'平均DL':>10} {'評価':>6} {'需要スコア':>10} {'競争'}"
    print(header)
    print(f"  {'-'*76}")

    # ソート (需要スコア降順)
    sorted_results = sorted(results, key=lambda r: r.demand_score, reverse=True)

    for r in sorted_results:
        line = (
            f"  {r.keyword:<16} "
            f"{r.work_count:>8} "
            f"¥{r.avg_price:>8,} "
            f"{r.avg_sales:>9,} "
            f"{r.avg_rating:>5.1f} "
            f"{r.demand_score:>9.1f} "
            f"{r.competition_level}"
        )
        print(line)

    print(f"{'='*80}")

    # 推奨キーワード
    if sorted_results:
        best = sorted_results[0]
        print(f"\n  推奨: 「{best.keyword}」(需要スコア: {best.demand_score})")


def demand_bar(score: float, width: int = 20) -> str:
    """需要スコアをバーチャートで表示する"""
    filled = int(score / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"


# ---------------------------------------------------------------------------
# CSV入出力
# ---------------------------------------------------------------------------

def export_results_csv(results: list[KeywordResult], filepath: str):
    """分析結果をCSVに出力する"""
    fieldnames = [
        "keyword", "work_count", "avg_price", "avg_sales",
        "avg_rating", "demand_score", "competition_level", "top_tags",
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = asdict(r)
            row["top_tags"] = "|".join(row["top_tags"])
            writer.writerow(row)

    print(f"\n  CSVに保存しました: {filepath}")


def import_keywords_csv(filepath: str) -> list[str]:
    """CSVファイルからキーワード一覧を読み込む"""
    keywords = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                kw = row[0].strip()
                if kw and kw != "keyword":
                    keywords.append(kw)
    return keywords


def export_results_json(results: list[KeywordResult], filepath: str):
    """分析結果をJSONに出力する"""
    data = {
        "generated_at": datetime.now().isoformat(),
        "results": [asdict(r) for r in results],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  JSONに保存しました: {filepath}")


# ---------------------------------------------------------------------------
# レポート生成
# ---------------------------------------------------------------------------

def generate_report(keyword: str, max_pages: int = 3, output: str = None):
    """詳細なキーワード需要レポートを生成する"""
    print(f"\n{'='*60}")
    print(f"  DL同人 需要分析レポート")
    print(f"  キーワード: 「{keyword}」")
    print(f"  生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # 1. サジェスト分析
    print("\n  [1] 関連キーワード (サジェスト)")
    print(f"  {'-'*50}")
    suggestions = get_suggestions(keyword)
    if suggestions:
        for i, s in enumerate(suggestions[:15], 1):
            print(f"      {i:2d}. {s}")
    else:
        print("      (サジェスト取得不可)")
    time.sleep(REQUEST_DELAY)

    # 2. メイン分析
    print(f"\n  [2] キーワード需要分析")
    print(f"  {'-'*50}")
    result = analyze_keyword(keyword, max_pages=max_pages)
    print(f"      作品数     : {result.work_count} 件")
    print(f"      平均価格   : ¥{result.avg_price:,}")
    print(f"      平均販売数 : {result.avg_sales:,} DL")
    print(f"      平均評価   : {result.avg_rating}")
    print(f"      需要スコア : {result.demand_score}/100 {demand_bar(result.demand_score)}")
    print(f"      競争レベル : {result.competition_level}")

    # 3. 関連タグ分析
    print(f"\n  [3] 関連タグ分析")
    print(f"  {'-'*50}")
    if result.top_tags:
        for i, tag in enumerate(result.top_tags, 1):
            print(f"      {i:2d}. {tag}")
    else:
        print("      (タグデータなし)")

    # 4. ジャンルマッチング
    print(f"\n  [4] ジャンルカテゴリ推定")
    print(f"  {'-'*50}")
    matched_genres = [g for g in GENRE_TAGS if g in keyword or keyword in g]
    related_genres = [g for g in GENRE_TAGS
                      if any(g in tag for tag in result.top_tags)]
    all_genres = list(dict.fromkeys(matched_genres + related_genres))
    if all_genres:
        print(f"      関連ジャンル: {', '.join(all_genres[:10])}")
    else:
        print("      (ジャンル推定不可)")

    # 5. 推奨事項
    print(f"\n  [5] 推奨事項")
    print(f"  {'-'*50}")
    recommendations = generate_recommendations(result)
    for i, rec in enumerate(recommendations, 1):
        print(f"      {i}. {rec}")

    print(f"\n{'='*60}")

    # CSV出力
    if output:
        export_results_csv([result], output)

    return result


def generate_recommendations(result: KeywordResult) -> list[str]:
    """分析結果に基づく推奨事項を生成する"""
    recs = []

    if result.work_count == 0:
        recs.append("このキーワードでの作品がほぼ見つかりません。別のキーワードを検討してください。")
        return recs

    if result.demand_score >= 70:
        recs.append("需要が高いキーワードです。品質で差別化を図りましょう。")
    elif result.demand_score >= 40:
        recs.append("中程度の需要です。ニッチな切り口で勝負できます。")
    else:
        recs.append("需要は限定的です。複合キーワードで訴求範囲を広げましょう。")

    if result.avg_sales > 300:
        recs.append("平均販売数が高く、市場が活発です。")
    elif result.avg_sales > 0:
        recs.append("販売数が控えめです。プロモーション戦略が重要になります。")

    if result.avg_price > 1000:
        recs.append(f"平均価格¥{result.avg_price:,}。ボリュームのある作品が求められています。")
    elif result.avg_price > 0:
        recs.append(f"平均価格¥{result.avg_price:,}。手軽な作品にもチャンスがあります。")

    if "非常に高" in result.competition_level:
        recs.append("競争が激しいため、独自性・クオリティが勝敗を分けます。")
    elif "低" in result.competition_level:
        recs.append("競争が少ない市場です。先行者利益を狙えます。")

    if result.top_tags:
        recs.append(f"よく使われるタグ: {', '.join(result.top_tags[:5])}")

    return recs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """CLIパーサーを構築する"""
    parser = argparse.ArgumentParser(
        description="DL同人 需要検索キーワード分析ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python doujinshi_keyword_analyzer.py suggest 催眠
  python doujinshi_keyword_analyzer.py analyze 異世界 --pages 3
  python doujinshi_keyword_analyzer.py trend 催眠 NTR 純愛 百合
  python doujinshi_keyword_analyzer.py report ASMR --output report.csv
  python doujinshi_keyword_analyzer.py fromfile keywords.csv --output results.csv
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # suggest
    sp_suggest = subparsers.add_parser("suggest", help="キーワードサジェストを取得")
    sp_suggest.add_argument("keyword", help="検索キーワード")

    # analyze
    sp_analyze = subparsers.add_parser("analyze", help="キーワード需要を分析")
    sp_analyze.add_argument("keyword", help="検索キーワード")
    sp_analyze.add_argument("--pages", type=int, default=2, help="取得ページ数 (デフォルト: 2)")

    # trend (比較)
    sp_trend = subparsers.add_parser("trend", help="複数キーワードを比較分析")
    sp_trend.add_argument("keywords", nargs="+", help="比較するキーワード (スペース区切り)")
    sp_trend.add_argument("--pages", type=int, default=1, help="各キーワードの取得ページ数")
    sp_trend.add_argument("--output", help="結果をCSVに出力")

    # report
    sp_report = subparsers.add_parser("report", help="詳細な需要レポートを生成")
    sp_report.add_argument("keyword", help="検索キーワード")
    sp_report.add_argument("--pages", type=int, default=3, help="取得ページ数 (デフォルト: 3)")
    sp_report.add_argument("--output", help="結果をCSVに出力")

    # fromfile
    sp_file = subparsers.add_parser("fromfile", help="CSVファイルからキーワード一括分析")
    sp_file.add_argument("input", help="入力CSVファイル (1列目にキーワード)")
    sp_file.add_argument("--output", default="results.csv", help="出力CSVファイル")
    sp_file.add_argument("--pages", type=int, default=1, help="各キーワードの取得ページ数")
    sp_file.add_argument("--json", dest="json_output", help="JSON形式でも出力")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    print("\n  DL同人 需要検索キーワード分析ツール")
    print(f"  実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.command == "suggest":
        suggestions = get_suggestions(args.keyword)
        print_suggestions(args.keyword, suggestions)

    elif args.command == "analyze":
        result = analyze_keyword(args.keyword, max_pages=args.pages)
        print_analysis(result)

    elif args.command == "trend":
        results = compare_keywords(args.keywords, max_pages=args.pages)
        print_comparison(results)
        if hasattr(args, "output") and args.output:
            export_results_csv(results, args.output)

    elif args.command == "report":
        generate_report(args.keyword, max_pages=args.pages, output=args.output)

    elif args.command == "fromfile":
        keywords = import_keywords_csv(args.input)
        if not keywords:
            print("  キーワードが見つかりませんでした。", file=sys.stderr)
            sys.exit(1)
        print(f"  {len(keywords)} 件のキーワードを読み込みました。")
        results = compare_keywords(keywords, max_pages=args.pages)
        print_comparison(results)
        export_results_csv(results, args.output)
        if hasattr(args, "json_output") and args.json_output:
            export_results_json(results, args.json_output)

    print()


if __name__ == "__main__":
    main()
