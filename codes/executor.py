"""
executor.py — Sandboxed code execution layer for Paper2Code-Enhanced.

Phase 1 of the meta-harness integration plan.
Selected via EXECUTOR_TYPE in .env (default: subprocess).

Usage:
    from executor import get_executor, ExecutionResult
    executor = get_executor()
    result = executor.run(["python", "main.py"], cwd="/path/to/repo", timeout=120)

TODO(phase-1): Full implementation of SubprocessExecutor resource limits.
TODO(phase-1): DockerExecutor implementation with NVIDIA runtime support.
TODO(phase-1): Wire executor into 4_debugging.py to replace raw subprocess calls.
"""

from __future__ import annotations

import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """Structured output from a sandboxed code execution attempt."""
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool
    elapsed_seconds: float
    cmd: list[str] = field(default_factory=list)
    cwd: str = ""

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "elapsed_seconds": self.elapsed_seconds,
            "success": self.success,
            "cmd": self.cmd,
            "cwd": self.cwd,
        }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseExecutor(ABC):
    """Abstract sandboxed executor. Subclass and implement `run()`."""

    @abstractmethod
    def run(
        self,
        cmd: Sequence[str],
        cwd: str,
        timeout: int = 120,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """
        Execute `cmd` inside `cwd` with a hard `timeout` (seconds).
        Returns a structured ExecutionResult regardless of success/failure.
        Must never raise — capture exceptions into stderr/returncode.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ---------------------------------------------------------------------------
# Subprocess executor (Phase 1 — active implementation)
# ---------------------------------------------------------------------------

class SubprocessExecutor(BaseExecutor):
    """
    Runs code in a child subprocess with timeout and optional resource limits.

    Env vars read from .env:
        EXECUTOR_TIMEOUT_SECS   Hard kill timeout per run (default: 120)
        EXECUTOR_MEMORY_MB      Soft RSS limit in MB (default: unlimited)
                                Requires 'resource' module (Linux only).
    """

    def __init__(self) -> None:
        self.timeout_secs = int(os.environ.get("EXECUTOR_TIMEOUT_SECS", "120"))
        self.memory_mb = int(os.environ.get("EXECUTOR_MEMORY_MB", "0"))  # 0 = unlimited

    def _preexec(self) -> None:
        """Applied in the child process before exec — sets resource limits."""
        if self.memory_mb > 0:
            try:
                import resource
                limit_bytes = self.memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
            except (ImportError, ValueError) as exc:
                import sys
                sys.stderr.write(f"[executor] Failed to set resource limits: {exc}\n")

    def run(
        self,
        cmd: Sequence[str],
        cwd: str,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        effective_timeout = timeout if timeout is not None else self.timeout_secs
        cmd_list = list(cmd)
        t0 = time.monotonic()
        timed_out = False

        try:
            proc = subprocess.run(
                cmd_list,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env={**os.environ, **(env or {})},
                preexec_fn=self._preexec,
            )
            returncode = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            # Check if subprocess was terminated due to memory limits or signals
            if returncode in (-9, -11, 137, 139) or "MemoryError" in stderr:
                if not stderr:
                    stderr = ""
                stderr += f"\n[executor] Process terminated or failed. Resource limits exceeded (OOM/SIGKILL/SIGSEGV) or MemoryError occurred. Exit code: {returncode}."

        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = -1
            stdout = exc.stdout.decode(errors="replace") if exc.stdout else ""
            stderr = (exc.stderr.decode(errors="replace") if exc.stderr else "") + (
                f"\n[executor] Process killed after {effective_timeout}s timeout."
            )

        except Exception as exc:  # noqa: BLE001
            returncode = -1
            stdout = ""
            stderr = f"[executor] Unexpected error launching process: {exc}"

        elapsed = time.monotonic() - t0
        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            timed_out=timed_out,
            elapsed_seconds=round(elapsed, 3),
            cmd=cmd_list,
            cwd=cwd,
        )


# ---------------------------------------------------------------------------
# Docker executor (Phase 1 stub — not yet implemented)
# ---------------------------------------------------------------------------

class DockerExecutor(BaseExecutor):
    """
    Executes code inside a Docker container with optional NVIDIA GPU support.

    Env vars (all optional):
        DOCKER_IMAGE            Image to use (default: paper2code-sandbox:latest)
        DOCKER_ENABLE_GPU       "1" to pass --gpus all (requires nvidia-docker)
        DOCKER_EXTRA_FLAGS      Space-separated extra docker run flags

    TODO(phase-1): Implement container lifecycle — pull/build image if missing,
        mount cwd as read-only input + writable /output volume, run cmd,
        capture logs, force-remove container on exit/timeout.
    TODO(phase-1): Add GPU passthrough conditional on DOCKER_ENABLE_GPU and
        nvidia-smi availability at startup.
    TODO(phase-1): Add container resource caps: --memory, --cpus flags from env.
    TODO(phase-1): Handle image build from a Dockerfile in repo root/docker/
        that includes PyTorch + CUDA base image.
    """

    def __init__(self) -> None:
        self.image = os.environ.get("DOCKER_IMAGE", "paper2code-sandbox:latest")
        self.enable_gpu = os.environ.get("DOCKER_ENABLE_GPU", "0") == "1"
        self.timeout_secs = int(os.environ.get("EXECUTOR_TIMEOUT_SECS", "120"))

    def run(
        self,
        cmd: Sequence[str],
        cwd: str,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        # TODO(phase-1): Replace this stub with real Docker implementation.
        raise NotImplementedError(
            "DockerExecutor is not yet implemented. "
            "Set EXECUTOR_TYPE=subprocess in .env to use the subprocess executor."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_EXECUTOR_REGISTRY: dict[str, type[BaseExecutor]] = {
    "subprocess": SubprocessExecutor,
    "docker": DockerExecutor,
}


def get_executor() -> BaseExecutor:
    """
    Return the executor instance specified by EXECUTOR_TYPE in .env.
    Defaults to SubprocessExecutor if unset or unknown.
    """
    executor_type = os.environ.get("EXECUTOR_TYPE", "subprocess").lower()
    cls = _EXECUTOR_REGISTRY.get(executor_type)
    if cls is None:
        print(
            f"[executor] Unknown EXECUTOR_TYPE='{executor_type}'. "
            f"Valid options: {list(_EXECUTOR_REGISTRY)}. Falling back to 'subprocess'."
        )
        cls = SubprocessExecutor
    return cls()
