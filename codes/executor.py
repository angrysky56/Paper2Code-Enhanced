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
        DOCKER_IMAGE            Image to use (default: python:3.11-slim)
        DOCKER_ENABLE_GPU       "1" to pass --gpus all (requires nvidia-docker)
        DOCKER_CPUS             Float value representing max CPU cores (e.g. 2.0)
        EXECUTOR_MEMORY_MB      Memory limit in MB (e.g. 512)
        EXECUTOR_TIMEOUT_SECS   Hard kill timeout per run (default: 120)
    """

    def __init__(self) -> None:
        self.image = os.environ.get("DOCKER_IMAGE", "python:3.11-slim")
        self.enable_gpu = os.environ.get("DOCKER_ENABLE_GPU", "0") == "1"
        self.timeout_secs = int(os.environ.get("EXECUTOR_TIMEOUT_SECS", "120"))
        self.memory_mb = int(os.environ.get("EXECUTOR_MEMORY_MB", "0"))
        self.cpus = float(os.environ.get("DOCKER_CPUS", "0.0"))

    def run(
        self,
        cmd: Sequence[str],
        cwd: str,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        import docker

        effective_timeout = timeout if timeout is not None else self.timeout_secs
        cmd_list = list(cmd)
        t0 = time.monotonic()
        timed_out = False

        # Ensure we have absolute path
        abs_cwd = os.path.abspath(cwd)

        # Get docker client
        try:
            client = docker.from_env()
        except Exception as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"[executor] Failed to connect to Docker daemon: {exc}",
                returncode=-1,
                timed_out=False,
                elapsed_seconds=0.0,
                cmd=cmd_list,
                cwd=cwd,
            )

        # Pull/get image
        try:
            client.images.get(self.image)
        except docker.errors.ImageNotFound:
            try:
                print(f"[executor] Pulling docker image: {self.image}...")
                client.images.pull(self.image)
            except Exception as exc:
                return ExecutionResult(
                    stdout="",
                    stderr=f"[executor] Failed to pull docker image '{self.image}': {exc}",
                    returncode=-1,
                    timed_out=False,
                    elapsed_seconds=0.0,
                    cmd=cmd_list,
                    cwd=cwd,
                )
        except Exception as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"[executor] Error checking docker image '{self.image}': {exc}",
                returncode=-1,
                timed_out=False,
                elapsed_seconds=0.0,
                cmd=cmd_list,
                cwd=cwd,
            )

        # Build run options
        run_kwargs = {
            "image": self.image,
            "command": cmd_list,
            "working_dir": "/workspace",
            "volumes": {abs_cwd: {"bind": "/workspace", "mode": "rw"}},
            "environment": {**os.environ, **(env or {})},
            "detach": True,
        }

        # Resource limits
        if self.memory_mb > 0:
            run_kwargs["mem_limit"] = self.memory_mb * 1024 * 1024
        if self.cpus > 0.0:
            run_kwargs["nano_cpus"] = int(self.cpus * 1e9)

        # GPU request setup
        device_requests = None
        if self.enable_gpu:
            try:
                device_requests = [
                    docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])
                ]
                run_kwargs["device_requests"] = device_requests
            except Exception as exc:
                print(f"[executor] Failed to setup GPU device request: {exc}. Trying without GPU.")

        container = None
        try:
            try:
                container = client.containers.run(**run_kwargs)
            except docker.errors.APIError as exc:
                if device_requests is not None:
                    # Retry without GPU
                    print(f"[executor] Docker GPU run failed: {exc}. Retrying without GPU passthrough...")
                    run_kwargs.pop("device_requests", None)
                    container = client.containers.run(**run_kwargs)
                else:
                    raise

            # Polling wait with timeout
            while True:
                container.reload()
                if container.status == "exited":
                    break
                if time.monotonic() - t0 > effective_timeout:
                    timed_out = True
                    break
                time.sleep(0.2)

            if timed_out:
                try:
                    container.kill()
                except Exception:
                    pass
                returncode = -1
                stdout = ""
                stderr = f"\n[executor] Process killed after {effective_timeout}s timeout."
            else:
                result_dict = container.wait()
                returncode = result_dict.get("StatusCode", -1)
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

        except Exception as exc:
            returncode = -1
            stdout = ""
            stderr = f"[executor] Unexpected error running Docker container: {exc}"

        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

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
