"""代码沙箱 —— 验证学员写的 Python 代码。

ponytail: 默认用当前解释器 subprocess 执行（无 Docker 依赖）；
升级路径 = 用 Docker 隔离执行，避免恶意代码影响主机。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class CodeSandbox:
    def __init__(self, use_docker: bool = False, timeout_seconds: int = 10) -> None:
        self.use_docker = use_docker
        self.timeout = timeout_seconds

    def run(self, code: str) -> dict:
        """执行代码，返回 {exit_code, stdout, stderr}。

        在临时目录里执行：学员代码常会写 demo.txt / profile.out / app.log 这类文件，
        用项目根目录当初始工作目录会把这些垃圾丢进仓库。
        """
        if self.use_docker:
            return self._run_docker(code)
        workdir = tempfile.mkdtemp(prefix="pyai_sandbox_")
        try:
            proc = subprocess.run(
                [sys.executable, "-X", "utf8", "-c", code],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=self.timeout, cwd=workdir,
            )
            return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": f"超时（>{self.timeout}s）"}
        finally:
            # 不用 TemporaryDirectory：它的清理只忽略 FileNotFoundError，受限环境里
            # rmtree 会被拒（PermissionError），异常会盖掉学员代码的正常输出，
            # 表现为「跑个 print 也 500」。这里清理失败就算了，最多留个空目录。
            shutil.rmtree(workdir, ignore_errors=True)

    def _run_docker(self, code: str) -> dict:
        try:
            proc = subprocess.run(
                ["docker", "run", "--rm", "-i", "python:3.12-slim", "python", "-c", code],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=self.timeout,
            )
            return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        except FileNotFoundError:
            return {"exit_code": -1, "stdout": "", "stderr": "未安装 Docker，回退本地执行"}
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": f"超时（>{self.timeout}s）"}


def verify_code(code: str, py_version: str = "3.12") -> bool:
    """校验示例代码可运行（0 token）。ponytail: py_version 暂未用于选解释器。"""
    result = CodeSandbox(use_docker=False).run(code)
    return result.get("exit_code") == 0
