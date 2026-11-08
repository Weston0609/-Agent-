"""判分 —— 纯函数，零依赖。

测验/考试都是选择题：每道题有正确选项 index 或正确答案字符串。
score 返回 0..1 的正确率（分数 = 答对题数 / 总题数）。
"""
from __future__ import annotations


def grade(questions: list[dict], submitted: list) -> float:
    """questions: [{answer: <正确项>}, ...]，submitted: 与 questions 等长的用户作答。

    返回正确率 0..1。submitted 长度不足按答错处理，多余忽略。
    """
    if not questions:
        return 0.0
    correct = 0
    for i, q in enumerate(questions):
        if i < len(submitted) and submitted[i] == q["answer"]:
            correct += 1
    return correct / len(questions)


def passed(score: float, threshold: float) -> bool:
    return score >= threshold


def grade_and_record(store, exam_id: str, kind: str, questions: list[dict], submitted: list, threshold: float) -> dict:
    """判分并写入 store.exam_progress / 或返回结果（不直接写课，考试用）。"""
    score = grade(questions, submitted)
    ok = passed(score, threshold)
    store.record_exam(exam_id, kind, score, ok)
    return {"score": score, "passed": ok, "total": len(questions)}


def grade_lesson_quiz(store, lesson_id: str, questions: list[dict], submitted: list, threshold: float) -> dict:
    """判一课测验，通过则标记该课 passed。"""
    score = grade(questions, submitted)
    ok = passed(score, threshold)
    status = "passed" if ok else "in_progress"
    store.mark_lesson(lesson_id, status, score)
    return {"score": score, "passed": ok, "total": len(questions)}
