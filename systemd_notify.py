"""
Systemd notify support for service type=notify.
Allows systemd to know when the service is ready and track its status.
"""
import os
import sys
from logger_config import setup_logger

logger = setup_logger(__name__)

if sys.platform != 'win32':
    import socket

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
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)  # pylint: disable=E1101
            sock.connect(notify_socket)
            sock.sendall(state.encode('utf-8'))
            sock.close()
            logger.debug("Sent systemd notify: %s", state)
            return True
        except (socket.error, OSError) as e:
            logger.error("Failed to send systemd notify: %s", e)
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
else:
    # Stub functions for Windows
    def sd_notify(state):
        """Systemd notify not available on Windows."""
        return False

    def sd_ready():
        """Systemd notify not available on Windows."""
        return False

    def sd_status(status):
        """Systemd notify not available on Windows."""
        return False

    def sd_reload():
        """Systemd notify not available on Windows."""
        return False

    def sd_stopping():
        """Systemd notify not available on Windows."""
        return False

    def is_systemd_notify_available():
        """Systemd notify not available on Windows."""
        return False
