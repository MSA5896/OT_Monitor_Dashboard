"""
serial_source.py – Serial / USB-CDC data source.
Reads newline-delimited JSON TelemetryPacket frames from a UART port
(e.g. STM32 / ESP32 connected via USB CDC-ACM on /dev/ttyUSB0 or COMx).
Uses pyserial-asyncio for non-blocking I/O.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from pydantic import ValidationError

from data_model import TelemetryPacket
from data_sources import DataSource

logger = logging.getLogger(__name__)


class SerialSource(DataSource):
    def __init__(self, config):
        self.cfg      = config
        self._running = False
        self._queue: asyncio.Queue[TelemetryPacket] = asyncio.Queue(maxsize=10)
        self._transport = None
        self._protocol  = None

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._connect_loop())
        logger.info("SerialSource started on %s @ %d baud",
                    self.cfg.data_source.serial_port, self.cfg.data_source.serial_baud)

    async def stop(self) -> None:
        self._running = False
        if self._transport:
            self._transport.close()

    async def packets(self) -> AsyncIterator[TelemetryPacket]:
        while self._running:
            try:
                pkt = await asyncio.wait_for(self._queue.get(), timeout=2.0)
                yield pkt
            except asyncio.TimeoutError:
                continue

    async def _connect_loop(self) -> None:
        import serial_asyncio  # pyserial-asyncio
        ds    = self.cfg.data_source
        delay = ds.reconnect_initial_delay_s

        while self._running:
            try:
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=ds.serial_port,
                    baudrate=ds.serial_baud,
                )
                delay = ds.reconnect_initial_delay_s
                logger.info("Serial port %s opened", ds.serial_port)
                self._transport = writer.transport

                while self._running:
                    try:
                        line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                        raw = line.decode("utf-8", errors="replace").strip()
                        if not raw:
                            continue
                        pkt = TelemetryPacket.model_validate_json(raw)
                        try:
                            self._queue.put_nowait(pkt)
                        except asyncio.QueueFull:
                            pass
                    except asyncio.TimeoutError:
                        logger.debug("Serial read timeout – waiting for data")
                    except (ValidationError, json.JSONDecodeError) as e:
                        logger.warning("Serial parse error: %s", e)

            except Exception as e:
                if self._running:
                    logger.warning("Serial error (%s). Retrying in %.1f s …", e, delay)
                    await asyncio.sleep(delay)
                    delay = min(delay * ds.reconnect_multiplier, ds.reconnect_max_delay_s)
