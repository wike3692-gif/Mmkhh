import { useState, useCallback, useRef, useEffect } from 'react'
import './App.css'

// ---------------------------------------------------------------------------
// Simulated analysis engine (runs entirely in-browser)
// ---------------------------------------------------------------------------

const GENRE_DB = {
  "ASMR":       { base: 85, sales: 720, price: 880, rating: 4.3, competition: "high" },
  "音声":       { base: 82, sales: 650, price: 770, rating: 4.2, competition: "high" },
  "催眠":       { base: 78, sales: 580, price: 990, rating: 4.1, competition: "high" },
  "NTR":        { base: 75, sales: 510, price: 880, rating: 3.9, competition: "high" },
  "純愛":       { base: 72, sales: 480, price: 770, rating: 4.4, competition: "mid" },
  "百合":       { base: 68, sales: 420, price: 660, rating: 4.3, competition: "mid" },
  "異世界":     { base: 74, sales: 490, price: 990, rating: 4.0, competition: "high" },
  "ファンタジー": { base: 70, sales: 450, price: 880, rating: 4.1, competition: "mid" },
  "触手":       { base: 65, sales: 380, price: 770, rating: 3.8, competition: "mid" },
  "ロリ":       { base: 62, sales: 350, price: 660, rating: 3.7, competition: "mid" },
  "熟女":       { base: 55, sales: 280, price: 770, rating: 3.9, competition: "low" },
  "人妻":       { base: 64, sales: 400, price: 880, rating: 4.0, competition: "mid" },
  "メイド":     { base: 58, sales: 310, price: 770, rating: 4.1, competition: "low" },
  "女騎士":     { base: 60, sales: 340, price: 880, rating: 4.0, competition: "low" },
  "エルフ":     { base: 57, sales: 300, price: 770, rating: 4.2, competition: "low" },
  "魔法少女":   { base: 56, sales: 290, price: 880, rating: 3.9, competition: "low" },
  "ツンデレ":   { base: 52, sales: 260, price: 660, rating: 4.3, competition: "low" },
  "ヤンデレ":   { base: 54, sales: 270, price: 770, rating: 4.0, competition: "low" },
  "BL":         { base: 70, sales: 440, price: 770, rating: 4.2, competition: "mid" },
  "RPG":        { base: 76, sales: 520, price: 1320, rating: 4.1, competition: "high" },
  "CG集":       { base: 60, sales: 350, price: 550, rating: 3.8, competition: "mid" },
  "同人誌":     { base: 65, sales: 380, price: 440, rating: 4.0, competition: "high" },
  "漫画":       { base: 63, sales: 360, price: 550, rating: 4.0, competition: "mid" },
  "動画":       { base: 58, sales: 300, price: 990, rating: 3.7, competition: "low" },
  "男の娘":     { base: 50, sales: 240, price: 660, rating: 4.1, competition: "low" },
  "ふたなり":   { base: 48, sales: 220, price: 770, rating: 3.8, competition: "low" },
  "獣耳":       { base: 55, sales: 280, price: 660, rating: 4.2, competition: "low" },
  "ケモノ":     { base: 45, sales: 200, price: 770, rating: 4.0, competition: "niche" },
  "ギャル":     { base: 58, sales: 310, price: 660, rating: 4.1, competition: "low" },
  "幼馴染":     { base: 50, sales: 250, price: 660, rating: 4.3, competition: "low" },
  "ボイスドラマ": { base: 72, sales: 460, price: 990, rating: 4.2, competition: "mid" },
  "アイドル":   { base: 55, sales: 280, price: 770, rating: 4.0, competition: "low" },
  "学園":       { base: 62, sales: 370, price: 770, rating: 4.1, competition: "mid" },
  "ホラー":     { base: 42, sales: 180, price: 880, rating: 3.9, competition: "niche" },
  "バトル":     { base: 50, sales: 250, price: 1100, rating: 3.8, competition: "low" },
  "シミュレーション": { base: 68, sales: 420, price: 1540, rating: 4.0, competition: "mid" },
  "ノベル":     { base: 55, sales: 280, price: 1100, rating: 4.1, competition: "low" },
  "妹":         { base: 53, sales: 265, price: 660, rating: 4.2, competition: "low" },
  "ナース":     { base: 46, sales: 210, price: 660, rating: 3.9, competition: "niche" },
  "巨乳":       { base: 60, sales: 350, price: 660, rating: 3.8, competition: "mid" },
  "モンスター娘": { base: 52, sales: 260, price: 880, rating: 4.1, competition: "low" },
}

const TAG_RELATIONS = {
  "ASMR":     ["音声", "催眠", "バイノーラル", "耳かき", "添い寝", "囁き", "癒し"],
  "音声":     ["ASMR", "ボイスドラマ", "催眠", "バイノーラル", "囁き"],
  "催眠":     ["ASMR", "音声", "洗脳", "調教", "支配"],
  "NTR":      ["寝取られ", "人妻", "浮気", "堕ち", "純愛"],
  "純愛":     ["ラブコメ", "甘々", "いちゃいちゃ", "初恋", "幼馴染"],
  "百合":     ["GL", "女の子同士", "レズ", "純愛", "学園"],
  "異世界":   ["ファンタジー", "転生", "チート", "冒険", "RPG"],
  "RPG":      ["ファンタジー", "冒険", "バトル", "育成", "ダンジョン"],
  "BL":       ["男性同士", "腐向け", "ショタ", "イケメン"],
  "触手":     ["モンスター", "拘束", "異種姦", "ファンタジー"],
  "CG集":     ["イラスト", "差分", "高解像度", "フルカラー"],
  "同人誌":   ["漫画", "フルカラー", "モノクロ", "短編"],
}

const SUGGESTIONS_DB = {
  "ASMR":   ["ASMR 耳かき", "ASMR 添い寝", "ASMR 催眠", "ASMR 癒し", "ASMR バイノーラル", "ASMR 囁き", "ASMR シチュボ", "ASMR 甘やかし"],
  "催眠":   ["催眠音声", "催眠 調教", "催眠 堕ち", "催眠術", "催眠 ASMR", "催眠 洗脳", "催眠 快楽"],
  "NTR":    ["NTR 人妻", "寝取られ", "NTR 報告", "NTR 堕ち", "NTR 純愛", "逆NTR", "NTR 彼女"],
  "異世界": ["異世界転生", "異世界 ハーレム", "異世界 チート", "異世界ファンタジー", "異世界 冒険", "異世界 勇者"],
  "RPG":    ["RPG ファンタジー", "RPG 探索", "RPG 育成", "RPG ダンジョン", "RPG バトル", "RPG 18禁"],
  "百合":   ["百合 学園", "百合 純愛", "百合 社会人", "百合 ファンタジー", "百合 漫画", "GL"],
  "純愛":   ["純愛 ラブコメ", "純愛 甘々", "純愛 初恋", "純愛 幼馴染", "純愛 学園", "純愛 同棲"],
}

function jitter(value, range) {
  return value + (Math.random() - 0.5) * 2 * range
}

function simulateAnalysis(keyword) {
  const kw = keyword.trim()
  const entry = GENRE_DB[kw]

  if (entry) {
    const score = Math.min(100, Math.max(0, Math.round(jitter(entry.base, 5))))
    const sales = Math.max(0, Math.round(jitter(entry.sales, entry.sales * 0.15)))
    const price = Math.max(100, Math.round(jitter(entry.price, entry.price * 0.1) / 10) * 10)
    const rating = Math.min(5, Math.max(1, parseFloat(jitter(entry.rating, 0.2).toFixed(1))))
    const workCount = Math.round(jitter(score * 2.5, 30))

    const tags = (TAG_RELATIONS[kw] || []).slice()
    // add some from GENRE_DB keys
    const allKeys = Object.keys(GENRE_DB).filter(k => k !== kw)
    while (tags.length < 8) {
      const pick = allKeys[Math.floor(Math.random() * allKeys.length)]
      if (!tags.includes(pick)) tags.push(pick)
    }

    const suggestions = SUGGESTIONS_DB[kw]
      || [`${kw} 人気`, `${kw} おすすめ`, `${kw} 新作`, `${kw} ランキング`, `${kw} 無料`]

    const competitionMap = {
      "high": "高 (人気市場)",
      "mid": "中 (成長市場)",
      "low": "低〜中 (チャンスあり)",
      "niche": "低 (ニッチ市場)",
    }

    return {
      keyword: kw,
      demandScore: score,
      workCount: Math.max(1, workCount),
      avgSales: sales,
      avgPrice: price,
      avgRating: rating,
      competition: competitionMap[entry.competition] || "中",
      tags: tags.slice(0, 10),
      suggestions,
      recommendations: generateRecommendations(score, sales, price, entry.competition, tags),
    }
  }

  // Unknown keyword — generate plausible data
  const hash = [...kw].reduce((a, c) => a + c.charCodeAt(0), 0)
  const score = Math.min(100, Math.max(5, (hash % 60) + 15 + Math.round(jitter(0, 10))))
  const sales = Math.max(10, Math.round(score * jitter(5.5, 2)))
  const price = Math.round(jitter(770, 300) / 10) * 10
  const rating = Math.min(5, Math.max(2, parseFloat(jitter(3.8, 0.5).toFixed(1))))

  const allTags = Object.keys(GENRE_DB)
  const tags = []
  for (let i = 0; i < 8; i++) {
    const pick = allTags[(hash + i * 7) % allTags.length]
    if (!tags.includes(pick)) tags.push(pick)
  }

  const comp = score > 70 ? "高 (人気市場)" : score > 45 ? "中 (成長市場)" : score > 25 ? "低〜中" : "低 (ニッチ市場)"

  return {
    keyword: kw,
    demandScore: score,
    workCount: Math.max(1, Math.round(score * jitter(2, 1))),
    avgSales: sales,
    avgPrice: Math.max(100, price),
    avgRating: rating,
    competition: comp,
    tags,
    suggestions: [`${kw} 人気`, `${kw} おすすめ`, `${kw} 新作`, `${kw} ランキング`, `${kw} 同人`],
    recommendations: generateRecommendations(score, sales, price, score > 60 ? "high" : "low", tags),
  }
}

function generateRecommendations(score, sales, price, competition, tags) {
  const recs = []

  if (score >= 70) {
    recs.push({ icon: "\u{1F525}", text: "需要が高いキーワードです。品質で差別化を図り、上位作品との差を明確にしましょう。" })
  } else if (score >= 40) {
    recs.push({ icon: "\u{1F4A1}", text: "中程度の需要があります。ニッチな切り口やユニークな要素で勝負できます。" })
  } else {
    recs.push({ icon: "\u{1F50D}", text: "需要は限定的です。複合キーワードで訴求範囲を広げることを検討してください。" })
  }

  if (sales > 400) {
    recs.push({ icon: "\u{1F4C8}", text: `平均${sales}DLと市場が活発です。定期的な新作投入で認知度を高めましょう。` })
  } else {
    recs.push({ icon: "\u{1F4E3}", text: "販売数は控えめです。SNSやサンプルの充実でプロモーション強化を。" })
  }

  if (price > 1000) {
    recs.push({ icon: "\u{1F4B0}", text: `平均価格¥${price.toLocaleString()}。ボリュームや付加価値のある作品が求められています。` })
  } else {
    recs.push({ icon: "\u{1F381}", text: `平均価格¥${price.toLocaleString()}。手軽な価格帯でもチャンスがあります。` })
  }

  if (competition === "high") {
    recs.push({ icon: "\u{26A0}\u{FE0F}", text: "競争が激しいため、独自性・クオリティ・タグ戦略が勝敗を分けます。" })
  } else {
    recs.push({ icon: "\u{2728}", text: "競争が少ない市場です。先行者利益を狙える可能性があります。" })
  }

  if (tags.length > 0) {
    recs.push({ icon: "\u{1F3F7}\u{FE0F}", text: `関連タグ「${tags.slice(0, 4).join("・")}」との組み合わせが効果的です。` })
  }

  return recs
}

// ---------------------------------------------------------------------------
// Quick-access tags
// ---------------------------------------------------------------------------

const QUICK_TAGS = [
  "ASMR", "催眠", "NTR", "純愛", "百合", "異世界",
  "RPG", "BL", "触手", "CG集", "ボイスドラマ", "同人誌",
]

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function DemandBar({ score }) {
  const cls = score >= 65 ? 'score-high' : score >= 35 ? 'score-mid' : 'score-low'
  const color = score >= 65 ? 'var(--neon-green)' : score >= 35 ? 'var(--neon-yellow)' : 'var(--neon-red)'

  return (
    <div className="demand-score">
      <div className="demand-score-header">
        <span className="demand-score-label">DEMAND SCORE</span>
        <span className="demand-score-value" style={{ color, textShadow: `0 0 15px ${color}` }}>
          {score}
        </span>
      </div>
      <div className="demand-bar-track">
        <div className={`demand-bar-fill ${cls}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}

function StatsPanel({ result }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="icon">{"\u{1F4CA}"}</span> STATISTICS
      </div>
      <div className="panel-body">
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-value">{result.workCount}</div>
            <div className="stat-label">WORKS</div>
          </div>
          <div className="stat-item">
            <div className="stat-value magenta">{"\u00A5"}{result.avgPrice.toLocaleString()}</div>
            <div className="stat-label">AVG PRICE</div>
          </div>
          <div className="stat-item">
            <div className="stat-value green">{result.avgSales.toLocaleString()}</div>
            <div className="stat-label">AVG DOWNLOADS</div>
          </div>
          <div className="stat-item">
            <div className="stat-value yellow">{"\u2605"}{result.avgRating}</div>
            <div className="stat-label">AVG RATING</div>
          </div>
        </div>
        <DemandBar score={result.demandScore} />
      </div>
    </div>
  )
}

function CompetitionPanel({ result }) {
  const compColor =
    result.competition.startsWith("高") ? 'var(--neon-red)' :
    result.competition.startsWith("中") ? 'var(--neon-yellow)' :
    'var(--neon-green)'

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="icon">{"\u{1F3AF}"}</span> COMPETITION
      </div>
      <div className="panel-body">
        <div style={{ textAlign: 'center', padding: '1rem 0' }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: '0.9rem',
            fontWeight: 700,
            color: compColor,
            textShadow: `0 0 10px ${compColor}`,
            letterSpacing: '1px',
          }}>
            {result.competition}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            marginTop: '0.75rem',
            lineHeight: 1.6,
          }}>
            {`KEYWORD: "${result.keyword}"`}<br />
            {`WORKS: ${result.workCount} | DL: ${result.avgSales.toLocaleString()}`}
          </div>
        </div>

        <div className="tag-cloud" style={{ marginTop: '1rem' }}>
          {result.tags.map((tag, i) => (
            <span
              key={tag}
              className={`tag-item ${i < 2 ? 'hot' : i < 5 ? 'warm' : 'normal'}`}
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function SuggestionsPanel({ result }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="icon">{"\u{1F50D}"}</span> SUGGESTIONS
      </div>
      <div className="panel-body">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {result.suggestions.map((s, i) => (
            <div key={i} style={{
              padding: '0.4rem 0.6rem',
              background: 'rgba(255, 0, 222, 0.05)',
              borderLeft: '2px solid var(--neon-magenta)',
              borderRadius: '0 3px 3px 0',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              color: 'var(--text-primary)',
              animation: `slideIn 0.3s ease-out ${i * 0.05}s both`,
            }}>
              <span style={{ color: 'var(--neon-magenta)', marginRight: '0.5rem' }}>{`0${i + 1}`}</span>
              {s}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function RecommendationsPanel({ result }) {
  return (
    <div className="panel full-width">
      <div className="panel-header">
        <span className="icon">{"\u{1F4DD}"}</span> RECOMMENDATIONS
      </div>
      <div className="panel-body">
        <div className="rec-list">
          {result.recommendations.map((rec, i) => (
            <div key={i} className="rec-item" style={{ animationDelay: `${i * 0.1}s` }}>
              <span className="rec-icon">{rec.icon}</span>
              <span>{rec.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function ComparisonPanel({ history }) {
  if (history.length < 2) return null

  const sorted = [...history].sort((a, b) => b.demandScore - a.demandScore)
  const maxScore = Math.max(...sorted.map(r => r.demandScore))

  return (
    <div className="panel full-width">
      <div className="panel-header">
        <span className="icon">{"\u{1F4CA}"}</span> KEYWORD COMPARISON
      </div>
      <div className="panel-body" style={{ overflowX: 'auto' }}>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>KEYWORD</th>
              <th>SCORE</th>
              <th>WORKS</th>
              <th>AVG DL</th>
              <th>AVG PRICE</th>
              <th>RATING</th>
              <th>COMPETITION</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const barColor = r.demandScore >= 65 ? 'var(--neon-green)' : r.demandScore >= 35 ? 'var(--neon-yellow)' : 'var(--neon-red)'
              return (
                <tr key={r.keyword}>
                  <td className="kw-name">{r.keyword}</td>
                  <td>
                    {r.demandScore}
                    <span
                      className="mini-bar"
                      style={{
                        width: `${(r.demandScore / maxScore) * 60}px`,
                        background: barColor,
                        boxShadow: `0 0 4px ${barColor}`,
                      }}
                    />
                  </td>
                  <td>{r.workCount}</td>
                  <td>{r.avgSales.toLocaleString()}</td>
                  <td>{"\u00A5"}{r.avgPrice.toLocaleString()}</td>
                  <td>{"\u2605"}{r.avgRating}</td>
                  <td>{r.competition}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

function App() {
  const [keyword, setKeyword] = useState('')
  const [mode, setMode] = useState('analyze')  // analyze | compare
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const runAnalysis = useCallback((kw) => {
    const target = kw || keyword
    if (!target.trim()) return

    setLoading(true)
    setResult(null)

    // Simulate network delay for realistic feel
    const delay = 800 + Math.random() * 1200
    setTimeout(() => {
      const res = simulateAnalysis(target.trim())
      setResult(res)
      setHistory(prev => {
        const filtered = prev.filter(h => h.keyword !== res.keyword)
        return [res, ...filtered].slice(0, 20)
      })
      setLoading(false)
    }, delay)
  }, [keyword])

  const handleSubmit = (e) => {
    e.preventDefault()
    runAnalysis()
  }

  const handleQuickTag = (tag) => {
    setKeyword(tag)
    runAnalysis(tag)
  }

  const handleHistoryClick = (kw) => {
    setKeyword(kw)
    runAnalysis(kw)
  }

  return (
    <div className="app">
      {/* ---- Header ---- */}
      <header className="header">
        <div className="header-content">
          <div className="header-title">
            <h1>DL{"\u540C\u4EBA"} ANALYZER</h1>
            <span className="version">v2.0</span>
          </div>
          <div className="header-status">
            <span className="status-dot" />
            SYSTEM ONLINE
          </div>
        </div>
      </header>

      {/* ---- Main ---- */}
      <main className="main">

        {/* Search */}
        <section className="search-section">
          <div className="section-label">// keyword input</div>
          <form className="search-box" onSubmit={handleSubmit}>
            <div className="search-input-wrapper">
              <span className="search-icon">{"\u25B6"}</span>
              <input
                ref={inputRef}
                type="text"
                className="search-input"
                placeholder={"\u30AD\u30FC\u30EF\u30FC\u30C9\u3092\u5165\u529B... (ASMR, \u50AC\u7720, NTR, RPG ...)"}
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className={`search-btn ${loading ? 'analyzing' : ''}`}
              disabled={loading || !keyword.trim()}
            >
              {loading ? 'SCANNING...' : 'ANALYZE'}
            </button>
          </form>

          <div className="quick-tags">
            {QUICK_TAGS.map(tag => (
              <button
                key={tag}
                className="quick-tag"
                onClick={() => handleQuickTag(tag)}
                disabled={loading}
              >
                {tag}
              </button>
            ))}
          </div>
        </section>

        {/* Mode Tabs */}
        {(result || history.length > 0) && (
          <div className="mode-tabs">
            <button
              className={`mode-tab ${mode === 'analyze' ? 'active' : ''}`}
              onClick={() => setMode('analyze')}
            >
              ANALYZE
            </button>
            <button
              className={`mode-tab ${mode === 'compare' ? 'active' : ''}`}
              onClick={() => setMode('compare')}
              disabled={history.length < 2}
            >
              COMPARE ({history.length})
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="loading-container">
            <div className="loading-spinner" />
            <div className="loading-text">ANALYZING DEMAND DATA...</div>
          </div>
        )}

        {/* Results */}
        {!loading && result && mode === 'analyze' && (
          <div className="results-grid">
            <StatsPanel result={result} />
            <CompetitionPanel result={result} />
            <SuggestionsPanel result={result} />
            <RecommendationsPanel result={result} />
          </div>
        )}

        {/* Compare mode */}
        {!loading && mode === 'compare' && history.length >= 2 && (
          <div className="results-grid">
            <ComparisonPanel history={history} />
          </div>
        )}

        {/* Welcome */}
        {!loading && !result && (
          <div className="welcome">
            <div className="welcome-icon">{"\u{1F50E}"}</div>
            <h2>DEMAND SCANNER READY</h2>
            <p>
              {"\u540C\u4EBA\u4F5C\u54C1\u306E\u30AD\u30FC\u30EF\u30FC\u30C9\u9700\u8981\u3092\u5206\u6790\u3057\u307E\u3059\u3002"}
              {"\u30AD\u30FC\u30EF\u30FC\u30C9\u3092\u5165\u529B\u3059\u308B\u304B\u3001\u4E0B\u306E\u30BF\u30B0\u3092\u30AF\u30EA\u30C3\u30AF\u3057\u3066\u958B\u59CB\u3057\u3066\u304F\u3060\u3055\u3044\u3002"}
            </p>
            <p className="mono">// {"\u9700\u8981\u30B9\u30B3\u30A2"} | {"\u7AF6\u4E89\u30EC\u30D9\u30EB"} | {"\u30BF\u30B0\u5206\u6790"} | {"\u63A8\u5968\u4E8B\u9805"}</p>
          </div>
        )}

        {/* History sidebar */}
        {history.length > 0 && !loading && (
          <div className="panel">
            <div className="panel-header">
              <span className="icon">{"\u{1F552}"}</span> SCAN HISTORY
            </div>
            <div className="panel-body">
              <div className="history-list">
                {history.map((h) => {
                  const color = h.demandScore >= 65 ? 'var(--neon-green)' : h.demandScore >= 35 ? 'var(--neon-yellow)' : 'var(--neon-red)'
                  return (
                    <div
                      key={h.keyword}
                      className="history-item"
                      onClick={() => handleHistoryClick(h.keyword)}
                    >
                      <span className="kw">{h.keyword}</span>
                      <span className="score" style={{ color }}>{h.demandScore}/100</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

      </main>

      {/* ---- Footer ---- */}
      <footer className="footer">
        DL{"\u540C\u4EBA"} KEYWORD ANALYZER // CYBERPUNK EDITION // 2026
      </footer>
    </div>
  )
}

export default App
