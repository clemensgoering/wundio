#!/usr/bin/env python3
"""Wundio – RFID daemon entry point. Called by wundio-rfid.service."""
import asyncio
from services.rfid import get_rfid_service


async def main() -> None:
    svc = get_rfid_service()
    svc.setup()
    await svc.run()


if __name__ == "__main__":
    asyncio.run(main())