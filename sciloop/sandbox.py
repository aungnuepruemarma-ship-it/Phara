"""Execution Engine — isolated Python subprocess (the proven code_sandbox design).

Safety: scrubbed environment (no API keys / secrets visible inside), CPU /
memory / file-size rlimits, hard wall-clock timeout, throwaway working dir.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile


def run_code(code: str, timeout: int = 10) -> dict:
    """Execute a self-contained Python snippet. Returns
    {stdout, stderr, exit_code, timed_out}."""
    timeout = max(1, min(int(timeout or 10), 60))
    code = (code or "").strip()
    if not code:
        return {"stdout": "", "stderr": "No code provided.", "exit_code": -1, "timed_out": False}

    workdir = tempfile.mkdtemp(prefix="sciloop_sbx_")
    script = os.path.join(workdir, "main.py")
    try:
        with open(script, "w") as fh:
            fh.write(code)

        safe_env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "PYTHONUNBUFFERED": "1",
            "HOME": workdir,
            "TMPDIR": workdir,
            "LANG": "C.UTF-8",
        }

        def _limits():  # pragma: no cover — child process (POSIX)
            try:
                import resource
                cpu = timeout + 1
                resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
                mem = 512 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
                fsize = 10 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
            except Exception:
                pass

        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-E", "-B", script],
                capture_output=True,
                cwd=workdir,
                env=safe_env,
                timeout=timeout,
                preexec_fn=_limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"Execution timed out after {timeout}s.",
                    "exit_code": -1, "timed_out": True}

        return {
            "stdout": proc.stdout.decode("utf-8", "replace")[:8000],
            "stderr": proc.stderr.decode("utf-8", "replace")[:3000],
            "exit_code": proc.returncode,
            "timed_out": False,
        }
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc)[:500], "exit_code": -1, "timed_out": False}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
