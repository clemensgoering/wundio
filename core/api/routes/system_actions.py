"""
Wundio – /api/system/actions routes

Whitelisted script execution with live SSE output streaming.
Replaces SSH access for common maintenance operations.

Script path resolution order:
  1. /usr/local/bin/<name>   (installed by install.sh as symlink)
  2. /opt/wundio/scripts/<name>.sh  (raw repo path with .sh suffix)
  3. /opt/wundio/scripts/<name>     (raw repo path without suffix)
"""
import asyncio
import logging
import os
import shlex
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import log_event

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system-actions"])


def _resolve_script(name: str) -> str | None:
    """
    Find an installed script by logical name.
    Returns the full path or None if not found.
    """
    candidates = [
        f"/usr/local/bin/{name}",           # installed by install.sh (no .sh)
        f"/opt/wundio/scripts/{name}.sh",   # repo path with suffix
        f"/opt/wundio/scripts/{name}",      # repo path without suffix
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


# ── Whitelist ─────────────────────────────────────────────────────────────────
# key → (label, argv_builder, is_destructive, estimated_seconds)
# argv_builder is a callable so we can resolve paths at request time
ACTIONS: dict[str, tuple[str, list[str], bool, int]] = {
    "pull-quick": (
        "Code-Update (schnell)",
        ["wundio-pull"],
        False,
        30,
    ),
    "pull-full": (
        "Vollständiges Update (Code + Frontend)",
        ["wundio-pull", "--full"],
        False,
        900,
    ),
    "system-update": (
        "System-Update (OS + Python-Libs)",
        ["update.sh"],
        False,
        300,
    ),
    "restart-service": (
        "Wundio-Dienst neu starten",
        ["systemctl", "restart", "wundio-core"],
        False,
        5,
    ),
    "reboot": (
        "Raspberry Pi neu starten",
        ["reboot"],
        True,
        10,
    ),
}

# Commands that are system binaries (not scripts to resolve)
_SYSTEM_CMDS = {"systemctl", "reboot"}


def _build_cmd(argv: list[str]) -> list[str] | None:
    """
    Resolve the first element to a full path if it's a script name.
    Returns None if the script cannot be found.
    """
    cmd0 = argv[0]
    if cmd0 in _SYSTEM_CMDS:
        return argv  # system binary, use as-is

    resolved = _resolve_script(cmd0)
    if resolved is None:
        return None
    return [resolved] + argv[1:]


class ActionInfo(BaseModel):
    key:               str
    label:             str
    destructive:       bool
    estimated_seconds: int
    available:         bool
    resolved_path:     str


@router.get("/actions")
async def list_actions() -> list[ActionInfo]:
    result = []
    for key, (label, argv, destructive, est) in ACTIONS.items():
        cmd0 = argv[0]
        if cmd0 in _SYSTEM_CMDS:
            resolved = cmd0
            available = True
        else:
            resolved = _resolve_script(cmd0) or "nicht gefunden"
            available = _resolve_script(cmd0) is not None
        result.append(ActionInfo(
            key=key,
            label=label,
            destructive=destructive,
            estimated_seconds=est,
            available=available,
            resolved_path=resolved,
        ))
    return result


@router.post("/actions/{action_key}/run")
async def run_action(
    action_key: str,
    confirm: bool = Query(False),
):
    if action_key not in ACTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_key}")

    label, argv, destructive, _ = ACTIONS[action_key]

    if destructive and not confirm:
        raise HTTPException(
            status_code=400,
            detail=f"'{label}' ist destruktiv. confirm=true erforderlich.",
        )

    cmd = _build_cmd(argv)
    if cmd is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Script '{argv[0]}' nicht gefunden. "
                f"Gesucht in: /usr/local/bin/, /opt/wundio/scripts/"
            ),
        )

    log_event("system", f"Aktion gestartet: {label}")
    logger.info("Running system action: %s → %s", action_key, shlex.join(cmd))

    return StreamingResponse(
        _stream_action(label, cmd),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_action(label: str, cmd: list[str]) -> AsyncGenerator[str, None]:
    def sse(event: str, data: str) -> str:
        safe = data.replace("\n", "\\n").replace("\r", "")
        return f"event: {event}\ndata: {safe}\n\n"

    yield sse("start", label)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
        )

        assert proc.stdout is not None

        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if line:
                yield sse("output", line)
            await asyncio.sleep(0)

        await proc.wait()
        exit_code = proc.returncode

        if exit_code == 0:
            log_event("system", f"Aktion erfolgreich: {label}")
            yield sse("done", "exit_code=0")
        else:
            log_event("system", f"Aktion fehlgeschlagen ({exit_code}): {label}", level="ERROR")
            yield sse("error", f"Prozess beendet mit Code {exit_code}")

    except FileNotFoundError as exc:
        msg = f"Befehl nicht gefunden: {exc}"
        log_event("system", msg, level="ERROR")
        yield sse("error", msg)
    except Exception as exc:
        msg = f"Fehler: {exc}"
        log_event("system", msg, level="ERROR")
        yield sse("error", msg)