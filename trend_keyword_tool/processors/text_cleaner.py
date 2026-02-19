"""
テキスト正規化・クリーニングモジュール
"""

import re
import unicodedata


def normalize(text: str) -> str:
    """Unicode NFKC 正規化 + 全角英数を半角に統一。"""
    return unicodedata.normalize("NFKC", text)


def remove_noise(text: str) -> str:
    """URL・メンション・ハッシュタグ・HTML タグ・記号を除去。"""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)   # #tag → tag（# のみ除去）
    text = re.sub(r"<[^>]+>", "", text)      # HTML タグ
    text = re.sub(r"[！-／：-＠［-｀｛-～、-〜「」『』【】〔〕…‥]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean(text: str) -> str:
    """正規化 → ノイズ除去を一括実行。"""
    return remove_noise(normalize(text))
