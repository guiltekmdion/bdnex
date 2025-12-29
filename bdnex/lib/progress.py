"""Console progress UI helpers.

Uses Rich when available, with a small text fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import sys
from typing import Optional


def _isatty() -> bool:
    stream = getattr(sys, "stdout", None)
    try:
        return bool(stream) and stream.isatty()
    except Exception:
        return False


@dataclass
class ProgressConfig:
    enabled: bool = True
    total: Optional[int] = None
    description: str = "Traitement"


class ProgressReporter:
    """A small wrapper around Rich progress with a safe fallback."""

    def __init__(self, config: ProgressConfig):
        self._config = config
        self._enabled = bool(config.enabled) and _isatty()
        self._progress = None
        self._task_id = None
        self._count = 0

    def __enter__(self) -> "ProgressReporter":
        if not self._enabled:
            return self

        try:
            rich_progress = importlib.import_module("rich.progress")

            BarColumn = getattr(rich_progress, "BarColumn")
            Progress = getattr(rich_progress, "Progress")
            SpinnerColumn = getattr(rich_progress, "SpinnerColumn")
            TaskProgressColumn = getattr(rich_progress, "TaskProgressColumn")
            TextColumn = getattr(rich_progress, "TextColumn")
            TimeElapsedColumn = getattr(rich_progress, "TimeElapsedColumn")
            TimeRemainingColumn = getattr(rich_progress, "TimeRemainingColumn")

            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                transient=True,
            )
            self._progress.start()
            self._task_id = self._progress.add_task(
                self._config.description,
                total=self._config.total,
            )
        except Exception:
            # Rich missing or failed: disable fancy UI.
            self._enabled = False

        return self

    def update(self, *, advance: int = 1, message: Optional[str] = None) -> None:
        self._count += advance

        if not self._enabled:
            # Minimal fallback: print every 10 steps and on completion.
            total = self._config.total
            should_print = (total is not None and self._count >= total) or (self._count % 10 == 0)
            if should_print:
                if total:
                    print(f"[{self._count}/{total}] {message or ''}".rstrip())
                else:
                    print(f"[{self._count}] {message or ''}".rstrip())
            return

        if self._progress is None or self._task_id is None:
            return

        desc = self._config.description
        if message:
            desc = f"{self._config.description}: {message}"

        self._progress.update(self._task_id, advance=advance, description=desc)

    def close(self) -> None:
        if self._progress is not None:
            try:
                self._progress.stop()
            except Exception:
                pass
            self._progress = None
            self._task_id = None

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def progress_for(total: Optional[int], *, enabled: bool = True, description: str = "Traitement") -> ProgressReporter:
    return ProgressReporter(ProgressConfig(enabled=enabled, total=total, description=description))
