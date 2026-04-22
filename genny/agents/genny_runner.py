"""
Genny Agent — smolagents ToolCallingAgent backed by local Ollama (Qwen2.5-Coder).

Provides Genny with "hands":
  - run_bash:       execute shell commands (git, kubectl, docker, python, etc.)
  - read_file:      read any file on the filesystem
  - write_file:     create or overwrite a file
  - list_directory: list contents of a directory

The agent runs in a background thread; callers subscribe via a callback that
receives incremental step updates and the final answer.
"""
import os
import subprocess
import threading
import traceback
from pathlib import Path
from typing import Callable

from smolagents import ToolCallingAgent, LiteLLMModel, tool

OLLAMA_BASE   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = "qwen2.5-coder:14b"
WORK_DIR      = str(Path.home() / "projects" / "platformgen")

# ─── Tools ───────────────────────────────────────────────────────────────────

@tool
def run_bash(command: str) -> str:
    """Run a shell command and return its stdout + stderr combined.

    Args:
        command: The shell command to execute (bash syntax).
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=60, cwd=WORK_DIR,
        )
        out = result.stdout
        if result.stderr:
            out += "\n[stderr]\n" + result.stderr
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[error] Command timed out after 60s"
    except Exception as exc:
        return f"[error] {exc}"


@tool
def read_file(path: str) -> str:
    """Read and return the contents of a file.

    Args:
        path: Absolute or relative path to the file to read.
    """
    try:
        p = Path(path)
        if not p.is_absolute():
            p = Path(WORK_DIR) / p
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[error] {exc}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating it (and parent dirs) if needed.

    Args:
        path: Absolute or relative path of the file to write.
        content: The full text content to write.
    """
    try:
        p = Path(path)
        if not p.is_absolute():
            p = Path(WORK_DIR) / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {p} ({len(content)} chars)"
    except Exception as exc:
        return f"[error] {exc}"


@tool
def list_directory(path: str) -> str:
    """List files and directories at the given path.

    Args:
        path: Absolute or relative path of the directory to list.
    """
    try:
        p = Path(path)
        if not p.is_absolute():
            p = Path(WORK_DIR) / p
        entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name))
        lines = []
        for e in entries:
            tag = "📁" if e.is_dir() else "📄"
            lines.append(f"{tag} {e.name}")
        return "\n".join(lines) or "(empty)"
    except Exception as exc:
        return f"[error] {exc}"


ALL_TOOLS = [run_bash, read_file, write_file, list_directory]

# ─── Agent builder ────────────────────────────────────────────────────────────

def build_agent(model_name: str = DEFAULT_MODEL, step_callbacks=None, ollama_base: str = OLLAMA_BASE) -> ToolCallingAgent:
    model = LiteLLMModel(
        model_id=f"ollama/{model_name}",
        api_base=ollama_base,
    )
    return ToolCallingAgent(
        tools=ALL_TOOLS,
        model=model,
        verbosity_level=0,
        max_steps=10,
        step_callbacks=step_callbacks or [],
    )


# ─── Threaded runner ─────────────────────────────────────────────────────────

class GennyRunner:
    """
    Runs the smolagents agent in a background thread.
    Emits step-by-step updates and final answer via callbacks.

    on_step(text)  — called for each intermediate tool call / observation
    on_done(text)  — called with the final answer
    on_error(text) — called if an exception occurs
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, ollama_base: str = OLLAMA_BASE):
        self._model_name = model_name
        self._ollama_base = ollama_base
        self._agent: ToolCallingAgent | None = None
        self._stop = False

    def _ensure_agent(self, cb):
        if self._agent is None:
            self._agent = build_agent(self._model_name, step_callbacks=[cb], ollama_base=self._ollama_base)
        else:
            # Re-register callback using the CallbackRegistry API (smolagents >= 1.14)
            self._agent._setup_step_callbacks([cb])

    def reset_model(self, model_name: str):
        self._model_name = model_name
        self._agent = None   # rebuilt on next run

    def run(
        self,
        prompt: str,
        on_step: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ):
        self._stop = False

        def _work():
            try:
                class _StepCallback:
                    def __init__(self_cb):
                        pass

                    def __call__(self_cb, memory_step, agent=None):
                        if self._stop:
                            raise InterruptedError("stopped")
                        parts = []
                        if hasattr(memory_step, "tool_calls") and memory_step.tool_calls:
                            for tc in memory_step.tool_calls:
                                parts.append(f"🔧 **{tc.name}**(`{_truncate(str(tc.arguments), 120)}`)")
                        if hasattr(memory_step, "observations") and memory_step.observations:
                            obs = _truncate(str(memory_step.observations), 300)
                            parts.append(f"```\n{obs}\n```")
                        if parts:
                            on_step("\n".join(parts))

                cb = _StepCallback()
                self._ensure_agent(cb)
                answer = self._agent.run(prompt)
                on_done(str(answer))

            except InterruptedError:
                on_done("*(stopped)*")
            except Exception as exc:
                on_error(f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")

        threading.Thread(target=_work, daemon=True).start()

    def stop(self):
        self._stop = True


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[:max_len] + "…"
