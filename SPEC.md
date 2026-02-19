# トレンドブログ分析 キーワード選定ツール 計画仕様書

**バージョン**: 1.0
**作成日**: 2026-02-19
**ブランチ**: claude/trend-keyword-prediction-tool-EReLg

---

## 1. 概要

X（旧Twitter）と Yahoo ニュースの RSS データを収集し、**トレンド化する前に急上昇ワードを先読み予測**する Python ツール。
予測した急上昇ワードから、**月間 1 万 PV 以上が見込める新規ブログキーワード**を自動選定する。

---

## 2. システムフロー

```
[ データ収集 ]
      │
      ├─ X トレンド RSS / Nitter RSS
      └─ Yahoo Japan ニュース RSS
            │
            ▼
[ テキスト前処理 ]
      │  形態素解析（MeCab / janome）でキーワード抽出
      │  ストップワード除去 / 正規化
            │
            ▼
[ 時系列スコアリング ]
      │  過去 24h・48h・72h の出現頻度を時系列集計
      │  急上昇スコア（Spike Score）算出
      │  = (直近 6h 頻度) / (過去 48h 平均頻度 + ε)
            │
            ▼
[ 急上昇ワード予測エンジン ]
      │  Spike Score 閾値超過ワードを抽出
      │  カテゴリ分類（エンタメ / テクノロジー / 社会 / スポーツ等）
      │  拡散速度トレンド予測（線形外挿 / 指数平滑法）
            │
            ▼
[ 1万PV見込みキーワード選定 ]
      │  検索ボリューム推定（PyTrends / Google Trends API）
      │  競合度評価（検索結果件数 / ドメインスコア推定）
      │  PV 見込みスコア = 検索需要 × CTR推定 × 競合係数
      │  閾値: PV 見込み ≥ 10,000
            │
            ▼
[ 出力 / レポート ]
      │  CSV / JSON エクスポート
      │  コンソール表示（優先度順ランキング）
      └─ （任意）Markdown ブログ記事アイデア生成
```

---

## 3. モジュール構成

```
trend_keyword_tool/
│
├── main.py                  # エントリーポイント・CLI
├── config.py                # 設定値・閾値・API キー管理
│
├── collectors/              # データ収集層
│   ├── __init__.py
│   ├── yahoo_rss.py         # Yahoo Japan ニュース RSS 取得
│   └── x_trends.py         # X トレンド / Nitter RSS 取得
│
├── processors/              # テキスト処理層
│   ├── __init__.py
│   ├── text_cleaner.py      # テキスト正規化・クリーニング
│   └── keyword_extractor.py # 形態素解析・キーワード抽出
│
├── analyzers/               # 分析・予測層
│   ├── __init__.py
│   ├── spike_scorer.py      # 急上昇スコア算出
│   ├── trend_predictor.py   # トレンド予測（時系列外挿）
│   └── pv_estimator.py      # PV 見込みスコア算出
│
├── outputs/                 # 出力層
│   ├── __init__.py
│   ├── reporter.py          # コンソール / Markdown レポート
│   └── exporter.py          # CSV / JSON エクスポート
│
├── storage/                 # 永続化
│   └── keyword_store.py     # SQLite による時系列データ蓄積
│
├── requirements.txt
└── README.md
```

---

## 4. データソース詳細

### 4-1. Yahoo Japan ニュース RSS

| 項目 | 詳細 |
|------|------|
| URL | `https://news.yahoo.co.jp/rss/topics/top-picks.xml` 他カテゴリ別 |
| 取得間隔 | 30 分ごと（スケジューラ or cron） |
| 取得データ | タイトル、概要、配信日時、リンク |
| カテゴリ | トップ / 国内 / 国際 / IT / エンタメ / スポーツ |

Yahoo News RSS エンドポイント例:
```
https://news.yahoo.co.jp/rss/topics/top-picks.xml
https://news.yahoo.co.jp/rss/topics/domestic.xml
https://news.yahoo.co.jp/rss/topics/it.xml
https://news.yahoo.co.jp/rss/topics/entertainment.xml
https://news.yahoo.co.jp/rss/topics/sports.xml
```

### 4-2. X（旧Twitter）トレンドデータ

X 公式 API はレート制限が厳しいため、以下の段階的アプローチを採用:

| 優先度 | 方法 | 補足 |
|--------|------|------|
| 1 | **Nitter パブリックインスタンス RSS** | 無料・API 不要 |
| 2 | **Twitter API v2（Bearer Token）** | 基本無料枠あり |
| 3 | **Google Trends 急上昇ワード（pytrends）** | X の代替補完 |

Nitter RSS 例（日本トレンド相当の検索クエリ）:
```
https://nitter.net/search/rss?q=%E3%83%88%E3%83%AC%E3%83%B3%E3%83%89&lang=ja
```

---

## 5. キーワード抽出仕様

### 5-1. 形態素解析

- ライブラリ: **janome**（インストール不要・Pure Python）または **MeCab + ipadic**
- 対象品詞: 名詞（一般・固有名詞・サ変接続）、複合名詞
- 除外: 助詞・助動詞・記号・1 文字語・ストップワード

### 5-2. キーワード正規化

- 全角→半角変換
- 大文字→小文字統一
- Unicode 正規化（NFKC）
- ハッシュタグ `#` 除去・保持オプション

### 5-3. n-gram 複合キーワード

- ユニグラム（単語単体）
- バイグラム（2 語連結）：「AI 規制」「円安 影響」など

---

## 6. 急上昇スコア（Spike Score）算出

```
Spike Score(w) = freq_recent(w) / (freq_baseline(w) + ε)

freq_recent  : 直近 6 時間の出現頻度
freq_baseline: 過去 48 時間の 1 時間あたり平均出現頻度
ε            : 0.1（ゼロ除算防止）
```

### 閾値

| スコア | 判定 |
|--------|------|
| ≥ 10.0 | 急上昇確定（アラート） |
| 5.0〜9.9 | 上昇傾向（要観測） |
| 1.5〜4.9 | 微上昇 |
| < 1.5 | 通常 |

---

## 7. PV 見込みスコア算出

```
PV_estimate(w) = search_volume(w) × CTR(rank) × (1 / competition_factor(w))

search_volume    : Google Trends 相対値 → 実数値換算（推定）
CTR(rank)        : 検索順位 1 位 ≈ 28%、3 位 ≈ 11%、10 位 ≈ 2.5%
competition_factor: Google 検索結果件数を正規化した競合度スコア
```

### 1 万 PV 条件の選定基準

1. `Spike Score ≥ 5.0`（急上昇中）
2. `PV_estimate ≥ 10,000`（月間想定）
3. 既存大手サイトの上位独占でない（競合度 ≤ 0.7）
4. 鮮度: 過去 7 日以内に初出現または急増

---

## 8. 出力フォーマット

### 8-1. コンソール出力（ランキング表示）

```
======================================
  トレンドキーワード予測レポート
  生成日時: 2026-02-19 12:00:00
======================================

【急上昇予測 TOP 10】
rank | キーワード       | Spike | PV見込み | カテゴリ
-----|-----------------|-------|---------|--------
   1 | ○○○ ×××       |  18.5 |  42,000 | テクノロジー
   2 | △△△           |  12.3 |  28,500 | 社会
  ...

【1万PV見込みキーワード】
  → "○○○ ×××" / "△△△" / ...
```

### 8-2. CSV エクスポート

```csv
rank,keyword,spike_score,pv_estimate,category,source,detected_at
1,AIエージェント,18.5,42000,テクノロジー,Yahoo+X,2026-02-19T12:00:00
```

### 8-3. JSON エクスポート

```json
{
  "generated_at": "2026-02-19T12:00:00",
  "keywords": [
    {
      "rank": 1,
      "keyword": "AIエージェント",
      "spike_score": 18.5,
      "pv_estimate": 42000,
      "category": "テクノロジー",
      "sources": ["Yahoo", "X"],
      "detected_at": "2026-02-19T12:00:00"
    }
  ]
}
```

---

## 9. 永続化（SQLite）

```sql
-- キーワード時系列テーブル
CREATE TABLE keyword_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword     TEXT NOT NULL,
    frequency   INTEGER NOT NULL,
    source      TEXT,           -- 'yahoo' | 'x' | 'combined'
    category    TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 予測結果テーブル
CREATE TABLE prediction_results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword          TEXT NOT NULL,
    spike_score      REAL,
    pv_estimate      INTEGER,
    competition_factor REAL,
    predicted_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. 技術スタック

| 用途 | ライブラリ |
|------|-----------|
| RSS 取得 | `feedparser` |
| HTTP クライアント | `requests`, `httpx` |
| 形態素解析 | `janome` |
| テキスト正規化 | `unicodedata`, `re` |
| 時系列・数値計算 | `pandas`, `numpy` |
| Google Trends | `pytrends` |
| データ永続化 | `sqlite3`（標準ライブラリ） |
| スケジューリング | `schedule` |
| CLI | `argparse` |
| テスト | `pytest` |

---

## 11. 実装フェーズ

| フェーズ | 内容 | 優先度 |
|---------|------|--------|
| Phase 1 | データ収集（Yahoo RSS + Nitter RSS） | 高 |
| Phase 2 | テキスト処理・キーワード抽出 | 高 |
| Phase 3 | 急上昇スコア算出・SQLite 蓄積 | 高 |
| Phase 4 | PV 見込みスコア（pytrends 連携） | 中 |
| Phase 5 | レポート・CSV/JSON 出力 | 中 |
| Phase 6 | CLI インターフェース・スケジューラ | 低 |

---

## 12. 制約・注意事項

- Yahoo News RSS は公開エンドポイントのため利用規約遵守（スクレイピング禁止・RSS のみ）
- X API は利用規約によりデータの再配布禁止。本ツールは個人利用・分析目的に限定
- Nitter インスタンスは不安定な場合あり → フォールバック実装必須
- Google Trends (`pytrends`) はレート制限あり → 1 リクエスト/秒 以下で実行
- 形態素解析精度向上のため、ドメイン固有辞書（IT / ニュース系）追加を推奨

---

## 13. ディレクトリ初期化コマンド

```bash
# プロジェクトセットアップ
python -m venv venv
source venv/bin/activate
pip install feedparser requests httpx janome pandas numpy pytrends schedule pytest

# 実行
python main.py --mode collect   # データ収集のみ
python main.py --mode predict   # 予測・レポート生成
python main.py --mode full      # 全処理実行（デフォルト）
python main.py --export csv     # CSV 出力付きで実行
```

---

*本仕様書は実装前の設計書です。実装過程で変更が生じる場合があります。*
