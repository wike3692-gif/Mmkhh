"""
SQLite による時系列キーワードデータ蓄積モジュール
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from trend_keyword_tool import config

logger = logging.getLogger(__name__)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """データベースとテーブルを初期化する。"""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS keyword_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword     TEXT NOT NULL,
                frequency   INTEGER NOT NULL DEFAULT 1,
                source      TEXT,
                category    TEXT,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS prediction_results (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword            TEXT NOT NULL,
                spike_score        REAL,
                pv_estimate        INTEGER,
                competition_factor REAL,
                predicted_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS generated_keywords (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                base_keyword   TEXT NOT NULL,
                suffix         TEXT NOT NULL,
                full_keyword   TEXT NOT NULL,
                source         TEXT,
                pv_estimate    INTEGER,
                combined_score REAL,
                generated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_kh_keyword  ON keyword_history(keyword);
            CREATE INDEX IF NOT EXISTS idx_kh_recorded ON keyword_history(recorded_at);
            CREATE INDEX IF NOT EXISTS idx_gk_base     ON generated_keywords(base_keyword);
        """)
    logger.info("DB initialized: %s", config.DB_PATH)


def record_keywords(keyword_counts: Dict[str, int], source: str = "combined") -> None:
    """キーワード出現回数を keyword_history に記録する。"""
    now = datetime.now().isoformat()
    rows = [
        (keyword, count, source, now)
        for keyword, count in keyword_counts.items()
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO keyword_history (keyword, frequency, source, recorded_at) VALUES (?, ?, ?, ?)",
            rows,
        )
    logger.info("Recorded %d keywords to DB", len(rows))


def get_keyword_history(
    keyword: str,
    hours: int = 48,
) -> List[sqlite3.Row]:
    """指定キーワードの過去 N 時間の履歴を取得する。"""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM keyword_history
            WHERE keyword = ?
              AND recorded_at >= datetime('now', ?)
            ORDER BY recorded_at ASC
            """,
            (keyword, f"-{hours} hours"),
        ).fetchall()
    return rows


def get_recent_frequency(keyword: str, hours: int) -> int:
    """直近 N 時間の出現合計頻度を返す。"""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(frequency), 0) as total
            FROM keyword_history
            WHERE keyword = ?
              AND recorded_at >= datetime('now', ?)
            """,
            (keyword, f"-{hours} hours"),
        ).fetchone()
    return int(row["total"]) if row else 0


def get_all_keywords_in_window(hours: int = 48) -> List[str]:
    """直近 N 時間に出現した全キーワードを返す。"""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT keyword FROM keyword_history
            WHERE recorded_at >= datetime('now', ?)
            """,
            (f"-{hours} hours",),
        ).fetchall()
    return [r["keyword"] for r in rows]


def save_prediction(keyword: str, spike_score: float, pv_estimate: int, competition_factor: float) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO prediction_results
                (keyword, spike_score, pv_estimate, competition_factor)
            VALUES (?, ?, ?, ?)
            """,
            (keyword, spike_score, pv_estimate, competition_factor),
        )


def save_generated_keywords(
    base_keyword: str,
    candidates: List[Dict],
) -> None:
    """生成キーワード（急上昇ワード+◯◯）を保存する。"""
    rows = [
        (
            base_keyword,
            c.get("suffix", ""),
            c.get("full_keyword", ""),
            c.get("source", ""),
            c.get("pv_estimate", 0),
            c.get("combined_score", 0.0),
        )
        for c in candidates
    ]
    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO generated_keywords
                (base_keyword, suffix, full_keyword, source, pv_estimate, combined_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    logger.info("Saved %d generated keywords for '%s'", len(rows), base_keyword)
