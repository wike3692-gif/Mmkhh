"""
形態素解析・キーワード抽出モジュール（janome ベース）
"""

import logging
from collections import Counter
from typing import List, Tuple

from trend_keyword_tool.processors.text_cleaner import clean

logger = logging.getLogger(__name__)

# 抽出対象品詞（janome の part-of-speech 形式）
_TARGET_POS = {"名詞"}
_TARGET_POS_DETAIL = {"一般", "固有名詞", "サ変接続", "複合"}
_MIN_WORD_LEN = 2  # 1 文字語を除外

# 基本的なストップワード
_STOP_WORDS = {
    "こと", "もの", "ため", "これ", "それ", "あれ", "ここ", "そこ", "あそこ",
    "よう", "ため", "際", "場合", "関係", "問題", "必要", "可能", "状況",
    "today", "news", "new", "the", "of", "in", "to", "a", "an",
    "について", "に関して", "など", "等", "及び",
}


def _get_tokenizer():
    """janome Tokenizer をシングルトンで返す。"""
    try:
        from janome.tokenizer import Tokenizer
        return Tokenizer()
    except ImportError:
        logger.error("janome がインストールされていません: pip install janome")
        raise


_tokenizer = None


def _tokenize(text: str) -> List[Tuple[str, str, str]]:
    """
    テキストを形態素解析して (surface, pos, pos_detail) のリストを返す。
    janome が使えない場合は簡易スペース分割にフォールバック。
    """
    global _tokenizer
    results = []
    try:
        if _tokenizer is None:
            _tokenizer = _get_tokenizer()
        for token in _tokenizer.tokenize(text):
            pos_parts = token.part_of_speech.split(",")
            pos = pos_parts[0] if pos_parts else ""
            pos_detail = pos_parts[1] if len(pos_parts) > 1 else ""
            results.append((token.surface, pos, pos_detail))
    except Exception as exc:
        logger.warning("形態素解析失敗、スペース分割にフォールバック: %s", exc)
        for word in text.split():
            results.append((word, "名詞", "一般"))
    return results


def extract_keywords(text: str) -> List[str]:
    """
    テキストからキーワード（名詞）リストを抽出する。
    """
    cleaned = clean(text)
    tokens = _tokenize(cleaned)
    keywords = []
    for surface, pos, pos_detail in tokens:
        if pos not in _TARGET_POS:
            continue
        if len(surface) < _MIN_WORD_LEN:
            continue
        if surface.lower() in _STOP_WORDS:
            continue
        keywords.append(surface)

    # バイグラム（隣接名詞の連結）
    bigrams = [
        f"{keywords[i]} {keywords[i+1]}"
        for i in range(len(keywords) - 1)
        if len(keywords[i]) >= _MIN_WORD_LEN and len(keywords[i+1]) >= _MIN_WORD_LEN
    ]
    return keywords + bigrams


def count_keywords(texts: List[str]) -> Counter:
    """
    テキストリスト全体のキーワード出現回数を集計する。
    """
    counter: Counter = Counter()
    for text in texts:
        for kw in extract_keywords(text):
            counter[kw] += 1
    return counter
