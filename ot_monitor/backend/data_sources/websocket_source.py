"""
websocket_source.py – WebSocket client data source.
Connects to the MCU gateway (or any source exposing the TelemetryPacket JSON schema
over WebSocket). Auto-reconnects with configurable exponential backoff.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import websockets
from pydantic import ValidationError

from data_model import TelemetryPacket
from data_sources import DataSource

logger = logging.getLogger(__name__)


class WebSocketSource(DataSource):
    def __init__(self, config):
        self.cfg      = config
        self._running = False
        self._queue: asyncio.Queue[TelemetryPacket] = asyncio.Queue(maxsize=10)

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._connect_loop())
        logger.info("WebSocketSource started → %s", self.cfg.data_source.ws_url)

    async def stop(self) -> None:
        self._running = False

    async def packets(self) -> AsyncIterator[TelemetryPacket]:
        while self._running:
            try:
                pkt = await asyncio.wait_for(self._queue.get(), timeout=2.0)
                yield pkt
            except asyncio.TimeoutError:
                continue

    async def _connect_loop(self) -> None:
        ds  = self.cfg.data_source
        url = ds.ws_url
        delay = ds.reconnect_initial_delay_s

        while self._running:
            try:
                logger.info("Connecting to %s …", url)
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    delay = ds.reconnect_initial_delay_s  # reset on success
                    logger.info("Connected to %s", url)
                    async for raw in ws:
                        if not self._running:
                            return
                        try:
                            pkt = TelemetryPacket.model_validate_json(raw)
                            try:
                                self._queue.put_nowait(pkt)
                            except asyncio.QueueFull:
                                pass
                        except ValidationError as e:
                            logger.warning("Validation error – packet dropped: %s", e)
                        except json.JSONDecodeError as e:
                            logger.warning("JSON decode error: %s", e)
            except Exception as e:
                if self._running:
                    logger.warning("WS disconnected (%s). Retrying in %.1f s …", e, delay)
                    await asyncio.sleep(delay)
                    delay = min(delay * ds.reconnect_multiplier, ds.reconnect_max_delay_s)
