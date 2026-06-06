import subprocess
import time
import numpy as np
import cv2
from typing import Optional, Tuple
from src.utils.logger import log

class ADBManager:
    def __init__(self, host: str = "127.0.0.1", port: int = 5555, package_name: str = "com.my.defense"):
        self.host = host
        self.port = port
        self.package_name = package_name
        self.device_address = f"{self.host}:{self.port}"
        self.is_connected = False

    def connect(self) -> bool:
        try:
            log.info(f"Connecting to ADB device at {self.device_address}...")
            subprocess.run(["adb", "start-server"], capture_output=True, text=True)
            result = subprocess.run(["adb", "connect", self.device_address], capture_output=True, text=True)
            if "connected" in result.stdout or "already connected" in result.stdout:
                self.is_connected = True
                log.info(f"Successfully connected to {self.device_address}")
                return True
            log.error(f"Failed to connect to device: {result.stdout}")
            self.is_connected = False
            return False
        except Exception as e:
            log.error(f"Exception occurred during ADB connection: {str(e)}")
            self.is_connected = False
            return False

    def verify_connection(self) -> bool:
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            if self.device_address in result.stdout and "device" in result.stdout.split(self.device_address)[1].split('\n')[0]:
                self.is_connected = True
                return True
            self.is_connected = False
            return False
        except Exception:
            self.is_connected = False
            return False

    def tap(self, x: int, y: int) -> bool:
        if not self.is_connected and not self.verify_connection():
            log.warning("ADB not connected. Dropping tap command.")
            return false
        try:
            subprocess.run(["adb", "-s", self.device_address, "shell", "input", "tap", str(x), str(y)], capture_output=True)
            return True
        except Exception as e:
            log.error(f"Failed to execute tap action at ({x}, {y}): {str(e)}")
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        if not self.is_connected and not self.verify_connection():
            log.warning("ADB not connected. Dropping swipe command.")
            return False
        try:
            subprocess.run(["adb", "-s", self.device_address, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)], capture_output=True)
            return True
        except Exception as e:
            log.error(f"Failed to execute swipe action from ({x1}, {y1}) to ({x2}, {y2}): {str(e)}")
            return False

    def take_screenshot(self) -> Optional[np.ndarray]:
        if not self.is_connected and not self.verify_connection():
            log.warning("ADB not connected. Cannot take screenshot.")
            return None
        try:
            pipe = subprocess.Popen(["adb", "-s", self.device_address, "shell", "screencap", "-p"], stdout=subprocess.PIPE)
            image_bytes, _ = pipe.communicate()
            if not image_bytes:
                return None
            image_bytes = image_bytes.replace(b'\r\n', b'\n')
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            log.error(f"Exception while pulling screenshot via ADB: {str(e)}")
            return None

    def start_app(self) -> bool:
        try:
            log.info(f"Starting application: {self.package_name}")
            subprocess.run(["adb", "-s", self.device_address, "shell", "monkey", "-p", self.package_name, "1"], capture_output=True)
            return True
        except Exception as e:
            log.error(f"Failed to start app: {str(e)}")
            return False

    def stop_app(self) -> bool:
        try:
            log.info(f"Force stopping application: {self.package_name}")
            subprocess.run(["adb", "-s", self.device_address, "shell", "am", "force-stop", self.package_name], capture_output=True)
            return True
        except Exception as e:
            log.error(f"Failed to stop app: {str(e)}")
            return False

    def press_back(self) -> bool:
        try:
            subprocess.run(["adb", "-s", self.device_address, "shell", "input", "keyevent", "4"], capture_output=True)
            return True
        except Exception as e:
            log.error(f"Failed to press back button: {str(e)}")
            return False