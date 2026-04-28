"""
Wundio – Device Feedback System

Central event bus for device actions (RFID scan, playback start, volume change, etc.).
Consumers:
  - Web UI via SSE (/api/feedback/stream)
  - Hardware handlers (LEDs, display) – subscribe via add_hardware_listener()

Event types and their LED/UI semantics:
  rfid_scan       → scanning pulse (amber, 1s)
  rfid_unknown    → error flash (red, 0.5s)
  playback_start  → success pulse (teal, 1.5s)
  playback_pause  → dim pulse (white, 0.5s)
  playback_stop   → off
  volume_change   → brief blue pulse
  track_next      → forward sweep
  track_prev      → backward sweep
  error           → red flash (1s)
  system_ready    → green pulse (1s, on boot)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEvent:
    type:    str                    # see event types above
    label:   str = ""               # human-readable message for UI toast
    data:    dict = field(default_factory=dict)  # extra payload (e.g. track name)
    color:   str = "amber"          # hint for LED: amber | teal | red | blue | white | off
    duration_ms: int = 1500         # hint for LED animation duration


# ── Event Bus ─────────────────────────────────────────────────────────────────

class FeedbackBus:
    """
    Async pub/sub bus for device feedback events.
    All UI clients and hardware listeners receive every event.
    """

    def __init__(self) -> None:
        self._sse_queues:   list[asyncio.Queue] = []
        self._hw_listeners: list[Callable[[FeedbackEvent], Any]] = []

    def add_hardware_listener(self, fn: Callable[[FeedbackEvent], Any]) -> None:
        """Register a callback for hardware feedback (LEDs, display, etc.)."""
        self._hw_listeners.append(fn)

    async def publish(self, event: FeedbackEvent) -> None:
        """Publish an event to all SSE clients and hardware listeners."""
        logger.debug("Feedback: %s – %s", event.type, event.label)

        payload = json.dumps({
            "type":        event.type,
            "label":       event.label,
            "color":       event.color,
            "duration_ms": event.duration_ms,
            "data":        event.data,
        })

        # Push to all SSE client queues
        dead = []
        for q in self._sse_queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._sse_queues.remove(q)

        # Call hardware listeners
        for fn in self._hw_listeners:
            try:
                result = fn(event)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as exc:
                logger.warning("Hardware listener error: %s", exc)

    async def stream(self) -> AsyncGenerator[str, None]:
        """SSE generator – yields events as they arrive."""
        q: asyncio.Queue = asyncio.Queue(maxsize=20)
        self._sse_queues.append(q)
        try:
            # Send a heartbeat immediately so the connection is confirmed
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: feedback\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            try:
                self._sse_queues.remove(q)
            except ValueError:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────

_bus: FeedbackBus | None = None


def get_feedback_bus() -> FeedbackBus:
    global _bus
    if _bus is None:
        _bus = FeedbackBus()
    return _bus


async def feedback(
    event_type: str,
    label: str = "",
    color: str = "amber",
    duration_ms: int = 1500,
    data: dict | None = None,
) -> None:
    """Convenience wrapper – fire and forget from anywhere in the codebase."""
    bus = get_feedback_bus()
    await bus.publish(FeedbackEvent(
        type=event_type,
        label=label,
        color=color,
        duration_ms=duration_ms,
        data=data or {},
    ))