"""
Data sources package.
Each source implements the abstract DataSource interface.
The factory function `create_source` reads config and returns
the correct concrete class.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator
from data_model import TelemetryPacket


class DataSource(ABC):
    """Abstract base for all data sources."""

    @abstractmethod
    async def start(self) -> None:
        """Open comms / connect."""

    @abstractmethod
    async def stop(self) -> None:
        """Graceful shutdown."""

    @abstractmethod
    def packets(self) -> AsyncIterator[TelemetryPacket]:
        """Async generator yielding parsed TelemetryPackets."""


def create_source(config) -> DataSource:
    """Factory: instantiates the correct DataSource from config."""
    src_type = config.data_source.type.lower()
    if src_type == "simulator":
        from data_sources.simulator_source import SimulatorSource
        return SimulatorSource(config)
    elif src_type == "websocket":
        from data_sources.websocket_source import WebSocketSource
        return WebSocketSource(config)
    elif src_type == "serial":
        from data_sources.serial_source import SerialSource
        return SerialSource(config)
    elif src_type == "hardware":
        from data_sources.hardware_source import HardwareSource
        return HardwareSource(config)
    else:
        raise ValueError(f"Unknown data_source.type: {src_type!r}")
