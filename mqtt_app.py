"""
MQTT message processing module.

This module handles MQTT message processing for device status updates,
button presses, and other IoT device events.
"""
import json
import paho.mqtt.client as mqtt
from database import get_db_session
from models import DBDevice, DBHistory
from config import config
from logger_config import setup_logger

logger = setup_logger(__name__)

def process_mqtt_message(topic, payload):
    """
    Process MQTT message and update device state.

    Args:
        topic: MQTT topic string
        payload: MQTT message payload

    Returns:
        None
    """
    with get_db_session() as db:
        parts = topic.split('/')
        if len(parts) < 3 or parts[0] != "dozerx":
            return
        mac, action = parts[1], parts[2]
        logger.debug("Processing MQTT message: %s -> %s for device %s", topic, action, mac)

        device = db.query(DBDevice).filter(DBDevice.mac == mac).first()
        if not device:
            logger.info("Creating new device record for MAC: %s", mac)
            device = DBDevice(mac=mac)
            db.add(device)
            db.flush()
            db.refresh(device)
            logger.info("Created device with MAC: %s", mac)
        else:
            logger.debug("Found existing device: %s", mac)

        if action == "status":
            logger.debug("Received status message for device %s: %s", mac, payload)
            try:
                data = json.loads(payload)
                updated_fields = []

                if "version" in data and "ver" in data["version"]:
                    device.fw_version = str(data["version"]["ver"])
                    updated_fields.append("fw_version")

                if data.get("uptime") != device.uptime:
                    device.uptime = data.get("uptime", device.uptime)
                    updated_fields.append("uptime")

                if data.get("ip") != device.ip:
                    device.ip = data.get("ip", device.ip)
                    updated_fields.append("ip")

                if data.get("ssid") != device.ssid:
                    device.ssid = data.get("ssid", device.ssid)
                    updated_fields.append("ssid")
                if data.get("bssid") != device.bssid:
                    device.bssid = data.get("bssid", device.bssid)
                    updated_fields.append("bssid")

                if data.get("rssi") != device.rssi:
                    device.rssi = data.get("rssi", device.rssi)
                    updated_fields.append("rssi")

                new_dur = data.get("long", 0)
                if new_dur != device.total_duration:
                    device.total_duration = new_dur
                    device.global_total_duration = max(device.global_total_duration, new_dur)
                    updated_fields.append("duration")

                buttons_updated = False
                for btn in data.get("buttons", []):
                    num = btn.get("num")
                    val = btn.get("cnt", 0)
                    if num is None:
                        logger.warning("Button data missing 'num' field for device %s", mac)
                        continue
                    if 1 <= num <= 6:
                        # Dynamic button processing
                        btn_cnt_attr = f"btn{num}_cnt"
                        global_btn_attr = f"global_btn{num}"

                        current_cnt = getattr(device, btn_cnt_attr)
                        current_global = getattr(device, global_btn_attr)

                        if val != current_cnt:
                            setattr(device, btn_cnt_attr, val)
                            setattr(device, global_btn_attr, max(current_global, val))
                            buttons_updated = True
                            updated_fields.append(f"btn{num}_cnt")
                            device.total_cnt += 1
                            device.global_total_cnt += 1
                            logger.debug("Updated button %s count: %s -> %s", num, current_cnt, val)
                    else:
                        logger.warning("Invalid button number: %s for device %s", num, mac)

                logger.debug("Device %s updated fields: %s", mac, updated_fields)

                history_entry = DBHistory(mac=mac, event_type="status", event_data=payload)
                db.add(history_entry)
                logger.debug("Added history entry for device %s: status", mac)

            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON payload for device %s: %s", mac, e)

        elif action == "btn" and len(parts) >= 4:
            btn_event = parts[3]
            is_stop = (len(parts) == 5 and parts[4] == "stop")
            event_type = "btn_stop" if is_stop else "btn"

            logger.debug("Button event for device %s: %s (stop: %s)", mac, btn_event, is_stop)

            history_entry = DBHistory(mac=mac, event_type=event_type, event_data=btn_event)
            db.add(history_entry)
            logger.debug("Added history entry for device %s: %s", mac, event_type)

            if not is_stop:
                if btn_event == "long":
                    device.long_cnt += 1
                    device.global_long_cnt += 1
                    logger.debug("Incremented long press count for device %s", mac)
                elif btn_event.isdigit():
                    num = int(btn_event)
                    if num == 1:
                        device.btn1_cnt += 1
                        device.global_btn1 += 1
                    elif num == 2:
                        device.btn2_cnt += 1
                        device.global_btn2 += 1
                    elif num == 3:
                        device.btn3_cnt += 1
                        device.global_btn3 += 1
                    elif num == 4:
                        device.btn4_cnt += 1
                        device.global_btn4 += 1
                    elif num == 5:
                        device.btn5_cnt += 1
                        device.global_btn5 += 1
                    elif num == 6:
                        device.btn6_cnt += 1
                        device.global_btn6 += 1
                    device.total_cnt += 1
                    device.global_total_cnt += 1
                    logger.debug("Incremented button %s count for device %s", num, mac)

        logger.debug("Database changes will be committed by context manager for device %s", mac)

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if config['mqtt'].get('user'):
    mqtt_client.username_pw_set(config['mqtt']['user'], config['mqtt'].get('password'))

@mqtt_client.connect_callback()
def on_connect(client, userdata, flags, rc, prop=None):
    """MQTT connection callback - subscribe to dozerx topics"""
    client.subscribe("dozerx/#")

@mqtt_client.message_callback()
def on_message(client, userdata, msg):
    """
    MQTT message callback - process incoming messages.

    Args:
        client: MQTT client instance
        userdata: User data
        msg: MQTT message object
    """
    logger.debug("Received MQTT message: %s - %s", msg.topic, msg.payload.decode())
    process_mqtt_message(msg.topic, msg.payload.decode())

def start_mqtt():
    """Start MQTT client and connect to broker"""
    mqtt_client.connect(config['mqtt']['broker'], config['mqtt']['port'], 60)
    mqtt_client.loop_start()
    logger.info("MQTT client started")

def stop_mqtt():
    """Stop MQTT client and disconnect from broker"""
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    logger.info("MQTT client stopped")
