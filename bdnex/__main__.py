"""The __main__ module lets you run the bdnex CLI interface by typing
`python -m bdnex`.
"""


import sys
import os


def _configure_stdio_utf8() -> None:
    """Best-effort UTF-8 configuration for Windows consoles.

    This prevents logging/printing from crashing when Unicode characters are
    present and the console is using a legacy code page (e.g. cp1252).
    """

    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            # 65001 = UTF-8
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception:
            pass

    for stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                # If reconfigure fails (rare), keep default behavior.
                pass


from .ui import main

if __name__ == "__main__":
    _configure_stdio_utf8()
    main()
