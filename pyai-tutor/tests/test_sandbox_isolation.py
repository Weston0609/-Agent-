"""确认沙箱不会把学员代码写的文件丢进仓库。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.tools.code_sandbox import CodeSandbox

os.chdir(Path(__file__).resolve().parents[1])
before = set(os.listdir("."))

r = CodeSandbox().run("open('leak.txt','w').write('x')\nprint('ok')")

after = set(os.listdir("."))
print("exit  =", r["exit_code"])
print("stdout=", repr(r["stdout"].strip()))
print("新文件:", sorted(after - before) or "无 ✅")
assert not (after - before), "沙箱把文件写到项目根目录了"
assert r["exit_code"] == 0, f"沙箱执行失败: {r['stderr']}"
print("✅ 沙箱隔离正常")
