"""打 Boss —— 把一节课的随堂测变成一场聊天对战。

规则（对齐用户要求）：
- 每节课学完，Boss 关卡解锁，通过「聊天」逐题交手，答对一题 = 打掉 Boss 一截血。
- **正确率必须 ≥ 85% 才算合格**（BOSS_PASS，比单元考线 75% 严），否则 Boss 回血、重来。
- 重来时**换一批没打过的题**（卷子落库在 quiz_papers，消费账在 quiz_history）。
- 血量、回合、连击都落在 ActiveSession.state，刷新页面不丢；全程读本地题库，0 token。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..db.session import BOSS_PASS

# Boss 血量 = 题数 × 每击伤害。用整数血量画血条，避免浮点误差让「最后一击」看起来没打完。
HIT_DAMAGE = 10


@dataclass
class BossState:
    """一局对战的战况（存在 ActiveSession.state，可直接 JSON 序列化）。"""

    lesson_id: str
    question_ids: list[str]
    hp: int                 # 剩余血量
    max_hp: int
    round: int              # 已交手回合数
    hits: int               # 答对次数
    combo: int              # 当前连击
    best_combo: int
    answers: list           # 历史作答（与 question_ids 对齐，逐题交手用）
    scores: list            # 每题得分

    @property
    def total(self) -> int:
        return len(self.question_ids)

    @property
    def next_index(self) -> int:
        return len(self.scores)

    @property
    def finished(self) -> bool:
        return self.next_index >= self.total or self.hp <= 0

    @property
    def barrage(self) -> float:
        """当前正确率（已交手部分）。"""
        return sum(self.scores) / len(self.scores) if self.scores else 0.0

    def passed(self) -> bool:
        """打光了所有题，且正确率 ≥ Boss 线。"""
        return self.finished and self.barrage >= BOSS_PASS

    def to_dict(self) -> dict:
        return {
            "lesson_id": self.lesson_id,
            "question_ids": self.question_ids,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "round": self.round,
            "hits": self.hits,
            "combo": self.combo,
            "best_combo": self.best_combo,
            "answers": self.answers,
            "scores": self.scores,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BossState:
        return cls(**d)


def start_boss(lesson_id: str, question_ids: list[str]) -> BossState:
    """开一局：满血，题序即战斗顺序。"""
    total = len(question_ids)
    return BossState(
        lesson_id=lesson_id, question_ids=list(question_ids),
        hp=total * HIT_DAMAGE, max_hp=total * HIT_DAMAGE,
        round=0, hits=0, combo=0, best_combo=0, answers=[], scores=[],
    )


def take_hit(state: BossState, score: float, answer) -> dict:
    """交手一回合：score 为该题得分（0..1），答对按伤害扣血，答错断连击。

    多选/场景题有部分分：只要拿到分就算「擦到」，按得分比例扣血但不算命中，
    连击只在满分层（1.0）时累积——这样「85% 正确率」的语义仍是「答对几道」。
    """
    perfect = score >= 1.0
    damage = round(state.max_hp / max(1, state.total) * score) if score > 0 else 0
    state.hp = max(0, state.hp - damage)
    state.round += 1
    state.hits += 1 if perfect else 0
    state.combo = state.combo + 1 if perfect else 0
    state.best_combo = max(state.best_combo, state.combo)
    state.scores.append(score)
    state.answers.append(answer)
    return {"damage": damage, "perfect": perfect, "hp": state.hp}


def verdict(state: BossState) -> dict:
    """结算：通关需要打完全部题且正确率 ≥ 85%。"""
    ok = state.passed()
    return {
        "passed": ok,
        "score": state.barrage,
        "need": BOSS_PASS,
        "hits": state.hits,
        "total": state.total,
        "best_combo": state.best_combo,
        "hp": state.hp,
    }


from_dict = BossState.from_dict
