"""
Systemd notify support for service type=notify.
Allows systemd to know when the service is ready and track its status.
"""
import os
import socket
from logger_config import setup_logger

logger = setup_logger(__name__)

def sd_notify(state):
    """
    Send notification to systemd.
    
    Args:
        state: Notification state string (e.g., "READY=1", "STATUS=Working...")
    """
    notify_socket = os.environ.get('NOTIFY_SOCKET')
    if not notify_socket:
        logger.debug("NOTIFY_SOCKET not set, systemd notify not available")
        return False
    
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.connect(notify_socket)
        sock.sendall(state.encode('utf-8'))
        sock.close()
        logger.debug(f"Sent systemd notify: {state}")
        return True
    except Exception as e:
        logger.error(f"Failed to send systemd notify: {e}")
        return False

def sd_ready():
    """Tell systemd that the service is ready to accept connections."""
    return sd_notify("READY=1")

def sd_status(status):
    """
    Send status message to systemd.
    
    Args:
        status: Status string to display
    """
    return sd_notify(f"STATUS={status}")

def sd_reload():
    """Tell systemd that the service is reloading its configuration."""
    return sd_notify("RELOADING=1")

def sd_stopping():
    """Tell systemd that the service is stopping."""
    return sd_notify("STOPPING=1")

def is_systemd_notify_available():
    """Check if systemd notify is available."""
    return os.environ.get('NOTIFY_SOCKET') is not None
