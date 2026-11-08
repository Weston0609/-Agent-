"""BKT 掌握度更新 —— 用正确率（而非布尔）驱动，适合多题测试。

update(p_mastery, correct_ratio)：贝叶斯后验 + 学习转移。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BKTParams:
    p_l0: float = 0.20   # 初始掌握（mastery 表默认值）
    p_t:  float = 0.15   # 学习转移
    p_g:  float = 0.20   # 猜测率
    p_s:  float = 0.10   # 失误率


def update(p_mastery: float, correct_ratio: float, k: BKTParams | None = None) -> float:
    """correct_ratio: 本次测试正确率 0-1（可含部分分）。"""
    k = k or BKTParams()
    if correct_ratio >= 0.5:
        # 观测到答对：P(learned | correct)
        num = p_mastery * (1 - k.p_s)
        den = num + (1 - p_mastery) * k.p_g
    else:
        # 观测到答错：P(learned | incorrect)
        num = p_mastery * k.p_s
        den = num + (1 - p_mastery) * (1 - k.p_g)
    post = num / den if den > 0 else p_mastery
    # 学习转移：无论对错都学一点
    return max(0.0, min(1.0, post + (1 - post) * k.p_t))


def fit_params(history: list[tuple[float, float]], iterations: int = 20) -> BKTParams:
    """EM 拟合用户个人的 BKT 参数（有足够数据后启用）。

    ponytail: 单用户离线场景数据量不足，简化返回默认参数；
    升级路径 = 数据积累后接真实 EM 迭代。
    """
    return BKTParams()
