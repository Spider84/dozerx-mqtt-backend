"""
Pydantic schemas for DozerX Modular Service.

This module defines the data models used for request/response validation
in the FastAPI application.
"""
from typing import Optional
from pydantic import BaseModel, validator
from decorators import validate_mac_address
from logger_config import setup_logger

logger = setup_logger(__name__)


class ClientCreate(BaseModel):
    """Schema for creating a new client."""

    name: str


class ButtonInfo(BaseModel):
    """Schema for button counter information."""

    num: int
    count: int
    global_count: int


class WifiInfo(BaseModel):
    """Schema for WiFi connection information."""

    ip: Optional[str] = None
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    rssi: int = 0


class TelegramInfo(BaseModel):
    """Schema for Telegram bot configuration."""

    allowed: bool = False
    bot_token: Optional[str] = None
    message: Optional[str] = None
    channel_id: Optional[str] = None


class MaxInfo(BaseModel):
    """Schema for MAX bot configuration."""

    allowed: bool = False
    bot_id: Optional[str] = None
    message: Optional[str] = None
    channel_id: Optional[str] = None


class ConsInfo(BaseModel):
    """Schema for console settings."""

    cons_1: int = 0
    cons_2: int = 0
    cons_3: int = 0
    cons_4: int = 0
    cons_5: int = 0
    stop_flags: int = 0


class DeviceUpdate(BaseModel):
    """Schema for updating device information."""

    short_name: Optional[str] = None
    description: Optional[str] = None

    # Grouped telegram settings
    telegram: Optional[TelegramInfo] = None

    # Grouped max settings
    max: Optional[MaxInfo] = None

    # Grouped console settings
    cons: Optional[ConsInfo] = None


class DeviceCreate(BaseModel):
    """Schema for creating a new device."""

    mac: str
    short_name: Optional[str] = None
    description: Optional[str] = None

    # Grouped telegram settings
    telegram: Optional[TelegramInfo] = None

    # Grouped max settings
    max: Optional[MaxInfo] = None

    # Grouped console settings
    cons: Optional[ConsInfo] = None

    @validator('mac')
    def validate_mac(cls, v):
        """
        Validate MAC address format.

        Args:
            v: MAC address string

        Returns:
            Uppercase MAC address if valid

        Raises:
            ValueError: If MAC address format is invalid
        """
        if not validate_mac_address(v):
            raise ValueError('Invalid MAC address format')
        return v.upper()


class TaskCreate(BaseModel):
    """Schema for creating a new scheduled task."""

    cron_expr: str
    tg_flag: bool = False
    max_flag: bool = False
    reset_flag: bool = False


class CountersInfo(BaseModel):
    """Schema for device counter information."""

    total_cnt: int = 0
    long_cnt: int = 0
    total_duration: int = 0
    global_total_cnt: int = 0
    global_long_cnt: int = 0
    global_total_duration: int = 0


class HistoryEntry(BaseModel):
    """Schema for MQTT message history entries."""

    id: int
    timestamp: str
    mac: str
    event_type: str
    event_data: str


class SchedulerTaskInfo(BaseModel):
    """Schema for scheduler task information."""

    task_id: int
    device_mac: str
    cron_expr: str
    tg_flag: bool = False
    max_flag: bool = False
    reset_flag: bool = False
    next_run_time: str  # Human-readable time until next execution
    next_run_seconds: int  # Seconds until next execution
    is_active: bool = True


class DeviceDetail(BaseModel):
    """Schema for detailed device information."""

    mac: str
    client_id: Optional[int] = None
    short_name: Optional[str] = None
    description: Optional[str] = None

    # Device info
    fw_version: Optional[str] = None
    uptime: int = 0

    # Grouped settings
    wifi: WifiInfo
    telegram: TelegramInfo
    max: MaxInfo
    cons: ConsInfo

    # Button counters (grouped)
    buttons: list[ButtonInfo]

    # Counters (grouped)
    counters: CountersInfo
