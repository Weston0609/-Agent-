"""静态自检 Web 面板模板：JS 语法 + DOM id 引用 + onclick 函数已定义。

没有浏览器/JS DOM 可依赖，所以用这三项确定性检查兜住「改了模板却漏了接线」。
用法：python -X utf8 scripts/check_web_ui.py
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "src/pyai/ui/web/templates/index.html"


def check(html: str) -> list[str]:
    script = re.search(r"<script>(.*)</script>", html, re.S)
    problems: list[str] = []
    if not script:
        return ["模板里找不到 <script> 块"]
    js = script.group(1)

    ids_html = set(re.findall(r'id="([^"]+)"', html))
    ids_js = set(re.findall(r"getElementById\('([^']+)'\)", js))
    for missing in sorted(ids_js - ids_html):
        problems.append(f"JS 引用了不存在的 id：{missing}")

    funcs = set(re.findall(r"function\s+(\w+)", js))
    for called in sorted(set(re.findall(r'on(?:click|change)="(\w+)\(', html))):
        if called not in funcs:
            problems.append(f"HTML 调用了未定义的函数：{called}")

    # 打 BOSS 门禁：讲义读过 45% 才放行。三处必须同时在：按钮态、跳转拦截、入口守卫。
    if "BOSS_READ_GATE" not in js:
        problems.append("模板里找不到 BOSS_READ_GATE，打 BOSS 的阅读门禁可能被删了")
    else:
        gate = re.search(r"const\s+BOSS_READ_GATE\s*=\s*([\d.]+)", js)
        if not gate or float(gate.group(1)) != 0.45:
            problems.append(f"BOSS_READ_GATE 应为 0.45，实际 {gate.group(1) if gate else '未定义'}")
        for need, why in (
            ("function syncBossGate", "syncBossGate 缺失：按钮不会随阅读进度禁用"),
            ("REACHED = Math.max(REACHED, done)", "renderStep 没有累计阅读进度 REACHED"),
            ("readProgress() < BOSS_READ_GATE", "moveStep/startBoss 没有拦截未读满的情况"),
        ):
            if need not in js:
                problems.append(f"{why}（找不到 {need!r}）")

    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as fh:
        fh.write(js)
        path = Path(fh.name)
    try:
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
        if result.returncode != 0:
            problems.append("JS 语法错误：\n" + (result.stderr or result.stdout).strip())
    finally:
        path.unlink(missing_ok=True)
    return problems


def main() -> int:
    problems = check(TEMPLATE.read_text(encoding="utf-8"))
    for p in problems:
        print("❌", p)
    print("✅ Web 面板模板自检通过" if not problems else f"共 {len(problems)} 个问题")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
