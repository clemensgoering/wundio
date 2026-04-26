"""
Wundio – /api/system/actions routes

Whitelisted, authenticated script execution with live SSE output streaming.
Replaces the need for SSH access for common maintenance operations.

Security model:
- Explicit whitelist: only known scripts/commands can be triggered
- Each action maps to a fixed command — no user-supplied arguments reach the shell
- FastAPI runs as root (required for systemctl/wundio-pull), so no sudo needed
- Destructive actions (uninstall, reboot) require an explicit confirm=true param
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

SCRIPTS_DIR = "/opt/wundio/scripts"

# ── Whitelist ─────────────────────────────────────────────────────────────────
# key → (label, command_list, is_destructive, estimated_seconds)
ACTIONS: dict[str, tuple[str, list[str], bool, int]] = {
    "pull-quick": (
        "Code-Update (schnell)",
        ["/opt/wundio/scripts/wundio-pull"],
        False,
        30,
    ),
    "pull-full": (
        "Vollständiges Update (Code + Frontend)",
        ["/opt/wundio/scripts/wundio-pull", "--full"],
        False,
        900,   # up to 15 min on Pi 3
    ),
    "system-update": (
        "System-Update (OS + Python-Libs)",
        ["/opt/wundio/scripts/update.sh"],
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
    "uninstall": (
        "Wundio deinstallieren",
        ["/opt/wundio/scripts/uninstall.sh", "--yes"],
        True,
        120,
    ),
}


class ActionInfo(BaseModel):
    key: str
    label: str
    destructive: bool
    estimated_seconds: int
    available: bool


@router.get("/actions")
async def list_actions() -> list[ActionInfo]:
    """List all available system actions."""
    result = []
    for key, (label, cmd, destructive, est) in ACTIONS.items():
        script_path = cmd[0]
        available = (
            script_path.startswith("systemctl") or
            script_path == "reboot" or
            os.path.isfile(script_path)
        )
        result.append(ActionInfo(
            key=key,
            label=label,
            destructive=destructive,
            estimated_seconds=est,
            available=available,
        ))
    return result


@router.post("/actions/{action_key}/run")
async def run_action(
    action_key: str,
    confirm: bool = Query(False),
):
    """
    Execute a whitelisted system action.
    Streams output as Server-Sent Events (text/event-stream).
    Destructive actions require confirm=true.
    """
    if action_key not in ACTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown action: {action_key}")

    label, cmd, destructive, _ = ACTIONS[action_key]

    if destructive and not confirm:
        raise HTTPException(
            status_code=400,
            detail=f"Action '{label}' is destructive. Pass confirm=true to proceed.",
        )

    log_event("system", f"Aktion gestartet: {label}")
    logger.info(f"Running system action: {action_key} → {shlex.join(cmd)}")

    return StreamingResponse(
        _stream_action(action_key, label, cmd),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


async def _stream_action(
    action_key: str,
    label: str,
    cmd: list[str],
) -> AsyncGenerator[str, None]:
    """Run command and yield SSE lines."""

    def sse(event: str, data: str) -> str:
        # Escape newlines in data for SSE protocol
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
            await asyncio.sleep(0)   # yield control so FastAPI can flush

        await proc.wait()
        exit_code = proc.returncode

        if exit_code == 0:
            log_event("system", f"Aktion erfolgreich: {label}")
            yield sse("done", f"exit_code=0")
        else:
            log_event("system", f"Aktion fehlgeschlagen ({exit_code}): {label}", level="ERROR")
            yield sse("error", f"Prozess beendet mit Code {exit_code}")

    except FileNotFoundError:
        msg = f"Script nicht gefunden: {cmd[0]}"
        log_event("system", msg, level="ERROR")
        yield sse("error", msg)
    except Exception as exc:
        msg = f"Fehler: {exc}"
        log_event("system", msg, level="ERROR")
        yield sse("error", msg)