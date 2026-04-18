from pydantic import BaseModel, validator
from typing import Optional
from decorators import validate_mac_address
from logger_config import setup_logger

logger = setup_logger(__name__)

class ClientCreate(BaseModel):
    name: str

class ButtonInfo(BaseModel):
    num: int
    count: int
    global_count: int

class WifiInfo(BaseModel):
    ip: Optional[str] = None
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    rssi: int = 0

class TelegramInfo(BaseModel):
    allowed: bool = False
    bot_token: Optional[str] = None
    message: Optional[str] = None
    channel_id: Optional[str] = None

class MaxInfo(BaseModel):
    allowed: bool = False
    bot_id: Optional[str] = None
    message: Optional[str] = None
    channel_id: Optional[str] = None

class ConsInfo(BaseModel):
    cons_1: int = 0
    cons_2: int = 0
    cons_3: int = 0
    cons_4: int = 0
    cons_5: int = 0
    stop_flags: int = 0

class DeviceUpdate(BaseModel):
    short_name: Optional[str] = None
    description: Optional[str] = None
    
    # Grouped telegram settings
    telegram: Optional[TelegramInfo] = None
    
    # Grouped max settings
    max: Optional[MaxInfo] = None
    
    # Grouped console settings
    cons: Optional[ConsInfo] = None

class DeviceCreate(BaseModel):
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
        if not validate_mac_address(v):
            raise ValueError('Invalid MAC address format')
        return v.upper()

class TaskCreate(BaseModel):
    cron_expr: str
    tg_flag: bool = False
    max_flag: bool = False
    reset_flag: bool = False

class CountersInfo(BaseModel):
    total_cnt: int = 0
    long_cnt: int = 0
    total_duration: int = 0
    global_total_cnt: int = 0
    global_long_cnt: int = 0
    global_total_duration: int = 0

class HistoryEntry(BaseModel):
    id: int
    timestamp: str
    mac: str
    event_type: str
    event_data: str

class SchedulerTaskInfo(BaseModel):
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
