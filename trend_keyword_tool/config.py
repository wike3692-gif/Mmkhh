"""
設定値・閾値・API キー管理
"""

# ─── RSS エンドポイント ───────────────────────────────────────────────
YAHOO_RSS_FEEDS = [
    "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    "https://news.yahoo.co.jp/rss/topics/it.xml",
    "https://news.yahoo.co.jp/rss/topics/entertainment.xml",
    "https://news.yahoo.co.jp/rss/topics/sports.xml",
    "https://news.yahoo.co.jp/rss/topics/world.xml",
]

# Nitter パブリックインスタンス（不安定な場合は順にフォールバック）
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]
NITTER_SEARCH_QUERY = "トレンド OR 速報 OR 話題"
NITTER_LANG = "ja"

# ─── API キー（オプション） ──────────────────────────────────────────
YAHOO_APP_ID = ""          # Yahoo Developer Network App ID（任意）
TWITTER_BEARER_TOKEN = ""  # Twitter API v2 Bearer Token（任意）

# ─── 急上昇スコア（Spike Score）閾値 ───────────────────────────────
SPIKE_RECENT_HOURS = 6     # 直近 N 時間の頻度を使用
SPIKE_BASELINE_HOURS = 48  # ベースライン計算期間
SPIKE_EPSILON = 0.1        # ゼロ除算防止
SPIKE_ALERT_THRESHOLD = 10.0    # 急上昇確定
SPIKE_RISING_THRESHOLD = 5.0    # 上昇傾向（新規キーワード生成対象）

# ─── PV 見込み閾値 ──────────────────────────────────────────────────
PV_MIN_THRESHOLD = 10_000   # 1万PV 以上のみ選定
COMPETITION_MAX = 0.7       # 競合度上限
KEYWORD_FRESHNESS_DAYS = 7  # 初出現から N 日以内

# ─── 急上昇ワード+◯◯ キーワード生成 ────────────────────────────────
AUTOCOMPLETE_URL = (
    "https://suggestqueries.google.com/complete/search"
    "?q={query}&hl=ja&gl=jp&client=firefox"
)
YAHOO_SUGGEST_URL = (
    "https://assist-search.yahooapis.jp/SuggestService/V4/assist"
    "?query={query}&output=json"
)
AUTOCOMPLETE_MAX_RESULTS = 10  # Google が返す候補数上限
SUGGEST_REQUEST_DELAY = 1.2    # API レート制限（秒）

# カテゴリ別サフィックステンプレート
SUFFIX_TEMPLATES = {
    "汎用": ["とは", "意味", "読み方", "まとめ", "最新", "2026", "いつ", "なぜ", "どこ"],
    "入門系": ["使い方", "始め方", "初心者", "入門", "やり方", "方法"],
    "比較系": ["おすすめ", "ランキング", "比較", "違い", "どっちがいい", "選び方"],
    "問題系": ["原因", "対策", "影響", "リスク", "デメリット", "危険", "問題"],
    "購入系": ["値段", "価格", "無料", "安い", "費用", "料金"],
    "評判系": ["口コミ", "評判", "レビュー", "感想"],
    "時事系": ["速報", "今後", "予測", "将来"],
    "テック系": ["API", "Python", "自動化", "ツール", "ビジネス活用"],
}

# ─── pytrends 設定 ──────────────────────────────────────────────────
PYTRENDS_HL = "ja-JP"
PYTRENDS_TZ = 540       # JST
PYTRENDS_GEO = "JP"
PYTRENDS_TIMEFRAME = "now 7-d"
PYTRENDS_REQUEST_DELAY = 1.5  # レート制限（秒）

# ─── SQLite ─────────────────────────────────────────────────────────
DB_PATH = "trend_keywords.db"

# ─── HTTP リクエスト共通設定 ─────────────────────────────────────────
REQUEST_TIMEOUT = 10   # 秒
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── 出力設定 ─────────────────────────────────────────────────────────
TOP_N_KEYWORDS = 20       # レポート表示件数
EXPORT_DIR = "exports"    # CSV / JSON 出力先ディレクトリ
