"""
トレンド予測モジュール（時系列外挿）

Spike Score の時系列から線形外挿または指数平滑法で
今後 6〜24 時間の急上昇度合いを予測する。
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _linear_extrapolate(values: List[float], steps: int = 3) -> float:
    """
    値の列を線形外挿して steps 先の推定値を返す。
    """
    if len(values) < 2:
        return values[-1] if values else 0.0
    # 最小二乗法（簡易版）
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0.0
    intercept = y_mean - slope * x_mean
    extrapolated = intercept + slope * (n - 1 + steps)
    return max(extrapolated, 0.0)


def _exponential_smoothing(values: List[float], alpha: float = 0.4) -> float:
    """
    単純指数平滑法で次期値を予測する。
    alpha: 平滑化係数（大きいほど直近に重みを置く）
    """
    if not values:
        return 0.0
    smoothed = values[0]
    for v in values[1:]:
        smoothed = alpha * v + (1 - alpha) * smoothed
    return round(smoothed, 4)


def predict_future_spike(
    spike_history: List[Tuple[str, float]],
    method: str = "exp_smoothing",
) -> float:
    """
    Spike Score の時系列履歴から近未来のスコアを予測する。

    Args:
        spike_history: [(timestamp_str, spike_score), ...] のリスト（時刻昇順）
        method: "linear" | "exp_smoothing"

    Returns:
        予測 Spike Score
    """
    values = [sc for _, sc in spike_history]
    if method == "linear":
        return _linear_extrapolate(values)
    return _exponential_smoothing(values)


def is_likely_to_trend(predicted_spike: float, current_spike: float) -> bool:
    """
    予測スコアが現在スコアより高く、かつ急上昇閾値を超えるか判定する。
    """
    from trend_keyword_tool import config
    return predicted_spike > current_spike and predicted_spike >= config.SPIKE_RISING_THRESHOLD
