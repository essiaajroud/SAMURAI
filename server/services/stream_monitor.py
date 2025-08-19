import logging
import time
from datetime import datetime
from threading import Timer, Thread
import requests
from requests.exceptions import ConnectionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamMonitor:
    def __init__(self):
        self.last_heartbeat = None
        self.is_stream_active = False
        self.disconnect_threshold = 30  # Augmenté à 30 secondes
        self.keepalive_interval = 5  # Intervalle de keepalive en secondes
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10  # Augmenté le nombre de tentatives
        self.reconnect_delay = 2  # Délai entre les tentatives en secondes
        self.reconnect_timer = None
        self.last_disconnect_notification = None
        self.notification_cooldown = 5  # seconds between notifications
        self.base_retry_delay = 1.0
        self.max_retry_delay = 30.0
        self.server_url = "http://localhost:5000"  # Ajustez selon votre config
        self._start_keepalive()

    def _start_keepalive(self):
        def keepalive_task():
            while self.is_stream_active:
                try:
                    self.update_heartbeat()
                    time.sleep(self.keepalive_interval)
                except Exception as e:
                    logger.error(f"Keep alive error: {str(e)}")
                    
        Thread(target=keepalive_task, daemon=True).start()

    def update_heartbeat(self):
        self.last_heartbeat = datetime.now()
        if not self.is_stream_active:
            logger.info("Stream connection restored")
        self.is_stream_active = True
        self.reconnect_attempts = 0

    def check_connection(self):
        if not self.last_heartbeat:
            return False
            
        time_since_last = (datetime.now() - self.last_heartbeat).total_seconds()
        if time_since_last > self.disconnect_threshold:
            if self.is_stream_active:
                self._handle_connection_loss(time_since_last)
            return False
        return True

    def _handle_connection_loss(self, time_since_last):
        current_time = datetime.now()
        should_notify = (
            self.last_disconnect_notification is None or
            (current_time - self.last_disconnect_notification).total_seconds() > self.notification_cooldown
        )
        
        if should_notify:
            logger.warning(f"Connection interrupted. Last heartbeat: {time_since_last:.2f}s ago")
            self.last_disconnect_notification = current_time
        
        self.handle_disconnect()

    def check_server_availability(self):
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def handle_disconnect(self):
        if not self.is_stream_active:
            return

        self.is_stream_active = False
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            self.attempt_reconnect()
            
    def attempt_reconnect(self):
        try:
            if not self.check_server_availability():
                logger.error("Server unavailable, waiting before retry...")
                retry_delay = min(self.base_retry_delay * (2 ** self.reconnect_attempts), 
                                self.max_retry_delay)
                time.sleep(retry_delay)
                return False

            logger.info("Server available, attempting to restore stream...")
            self.update_heartbeat()
            return True
        except ConnectionError as e:
            logger.error(f"Connection refused: {str(e)}")
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.handle_disconnect()
            else:
                self.reset_connection()
            return False

    def reset_connection(self):
        self.reconnect_attempts = 0
        self.is_stream_active = False
        time.sleep(self.base_retry_delay)
        self._start_keepalive()
        logger.info("Connection reset, checking server availability...")
        if self.check_server_availability():
            self.attempt_reconnect()

    def cleanup(self):
        if self.reconnect_timer:
            self.reconnect_timer.cancel()
