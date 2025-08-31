from __future__ import annotations

import os
import subprocess
from typing import List, Optional, Dict, Any


def spawn_detached_silent(args: List[str], cwd: Optional[str] = None) -> subprocess.Popen:
    """Spawn a child process detached from the parent and without visible console.

    Cross-platform behavior:
    - Windows: hide window (STARTUPINFO + CREATE_NO_WINDOW) and detach (CREATE_NEW_PROCESS_GROUP|DETACHED_PROCESS).
    - POSIX: start new session (start_new_session=True) and redirect stdio to DEVNULL.
    """
    popen_kwargs: Dict[str, Any] = {"cwd": cwd or None}
    if os.name == "nt":
        creationflags = 0x00000008 | 0x00000200 | 0x08000000  # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW | DETACHED_PROCESS
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        si.wShowWindow = 0  # SW_HIDE
        popen_kwargs.update({
            "creationflags": creationflags,
            "startupinfo": si,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        })
    else:
        popen_kwargs.update({
            "start_new_session": True,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        })
    return subprocess.Popen(args, **popen_kwargs)  # nosec - local spawn


