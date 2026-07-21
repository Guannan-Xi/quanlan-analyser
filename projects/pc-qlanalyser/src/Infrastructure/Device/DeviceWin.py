import socket
import uuid
import psutil
from ..log.QLLogging import QLLogging

# 获取本地IP地址
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        QLLogging.log.error(f"get IP failed: {e}")
        return None

# 获取设备标识(计算机名称)
def get_device_identifier():
    return socket.gethostname()
