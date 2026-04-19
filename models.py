"""
SQLAlchemy database models.

This module defines all database models for the DozerX Modular Service,
including clients, devices, history, tasks, and API keys.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from logger_config import setup_logger

logger = setup_logger(__name__)

class DBClient(Base):
    """Client model for representing client organizations."""

    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    devices = relationship("DBDevice", back_populates="client")

class DBDevice(Base):
    """Device model for IoT device information and settings."""

    __tablename__ = "devices"
    mac = Column(String, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    short_name = Column(String, default="")
    description = Column(String, default="")

    tg_allowed = Column(Boolean, default=False)
    tg_bot_token = Column(String, default="")
    tg_message = Column(String, default="")
    tg_channel_id = Column(String, default="")

    max_allowed = Column(Boolean, default=False)
    max_bot_id = Column(String, default="")
    max_message = Column(String, default="")
    max_channel_id = Column(String, default="")

    cons_1 = Column(Integer, default=0)
    cons_2 = Column(Integer, default=0)
    cons_3 = Column(Integer, default=0)
    cons_4 = Column(Integer, default=0)
    cons_5 = Column(Integer, default=0)
    stop_flags = Column(Integer, default=0)

    fw_version = Column(String, default="")
    uptime = Column(Integer, default=0)
    ip = Column(String, default="")
    ssid = Column(String, default="")
    bssid = Column(String, default="")
    rssi = Column(Integer, default=0)

    btn1_cnt = Column(Integer, default=0)
    btn2_cnt = Column(Integer, default=0)
    btn3_cnt = Column(Integer, default=0)
    btn4_cnt = Column(Integer, default=0)
    btn5_cnt = Column(Integer, default=0)
    btn6_cnt = Column(Integer, default=0)
    total_cnt = Column(Integer, default=0)
    long_cnt = Column(Integer, default=0)
    total_duration = Column(Integer, default=0)

    global_btn1 = Column(Integer, default=0)
    global_btn2 = Column(Integer, default=0)
    global_btn3 = Column(Integer, default=0)
    global_btn4 = Column(Integer, default=0)
    global_btn5 = Column(Integer, default=0)
    global_btn6 = Column(Integer, default=0)
    global_total_cnt = Column(Integer, default=0)
    global_long_cnt = Column(Integer, default=0)
    global_total_duration = Column(Integer, default=0)

    client = relationship("DBClient", back_populates="devices")
    tasks = relationship("DBTask", back_populates="device", cascade="all, delete-orphan")

class DBHistory(Base):
    """History model for MQTT message history."""

    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    mac = Column(String, index=True)
    event_type = Column(String, index=True)
    event_data = Column(String)

class DBTask(Base):
    """Task model for scheduled device tasks."""

    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    device_mac = Column(String, ForeignKey("devices.mac"))
    cron_expr = Column(String)
    tg_flag = Column(Boolean, default=False)
    max_flag = Column(Boolean, default=False)
    reset_flag = Column(Boolean, default=False)
    device = relationship("DBDevice", back_populates="tasks")

class DBApiKey(Base):
    """API key model for authentication."""

    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
