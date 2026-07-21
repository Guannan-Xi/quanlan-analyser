import os
import json
import sqlite3
import hashlib
import base64
from datetime import datetime, timedelta
import math
from pathlib import Path

import wmi
import logging
from PyQt5.QtCore import QObject, QTimer,pyqtSignal
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from src.licence_core_ctypes import LicenceCore

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 常量定义
CACHE_FILE_LICENCE_QL = "licence.lic"
DT_PRM_KEY_SYS_DEFAULT = "System"
DT_PRM_KEY_SYS_INSTALL_LICENCE = "NeedLicence"
_TIME_SPLIT = 60  # 验证间隔，单位秒

class QEncryption:
    """提供加密功能,对主板机器码加密，生成序列号"""
    @staticmethod
    def encrypt_md5(text):
        """MD5加密"""
        if isinstance(text, str):
            text = text.encode('utf-8')
        return hashlib.md5(text).hexdigest()

class SysConfig:
    """系统配置管理类"""
    @staticmethod
    def get_key_value(ini_path, section, key, default=""):
        """从INI文件获取配置值"""
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(ini_path)
            return config.get(section, key)
        except:
            return default

class GlobalAPI:
    """全局API访问类"""
    @staticmethod
    def get_system_config_root_dir():
        """获取系统配置目录"""
        # 在实际应用中，这可能是一个特定目录
        # 在这个例子中，我们使用当前目录
        return os.path.dirname(os.path.abspath(__file__))

class Licence(QObject):
    """许可证验证类"""
    
    # 验证结果枚举
    RESULT_INIT = -1
    RESULT_NORMAL = 0
    RESULT_NO_AUTH_FILE = 1
    RESULT_ILLEGAL = 2
    RESULT_FILE_ABNORMAL = 3
    RESULT_NOT_LOCAL_AUTH_FILE = 4
    RESULT_NOT_AVAILABLE = 5
    RESULT_AUTH_TIME_ABNORMAL = 6
    RESULT_USE_TIME_ABNORMAL = 7
    RESULT_TRIAL_EXPIRES = 8
    RESULT_AUTH_EXPIRES = 9

    authorized = pyqtSignal()  # 授权成功信号
    remind = pyqtSignal(str, int)  # 新增：提醒信号 (message, seconds_left)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.licence_id = ""
        self.used_day = 0.0
        self.auth_clock = None
        self.need_licence = True
        self.result = self.RESULT_INIT
        self.licence_path = ""
        self.ini_file_path = ""
        self.board_serial_number_md5 = ""
        self.licence = {
            'board_mac': '',
            'auth_time': '',
            'last_use_time': '',
            'trial_day': 0,
            'valid_day': 0,
            'stim_enabled': False,
            'edit_enabled': False,
            'micro_state_enabled': False,
            'simu_enabled': False,
            'filter_enabled': False
        }
        self.is_continue = True
        # 提醒阈值（秒）与状态
        # 3天、1天、3小时、5分钟（单位：秒）
        self._remind_thresholds = [3 * 24 * 3600, 24 * 3600, 3 * 3600, 5 * 60]
        self._fired_thresholds = set()  # 已触发过的阈值，避免重复提醒
        self._expired_notified = False  # 到期仅提醒一次
        self.init_licence()

    def lic_path(self, name: str, ensure_dir: bool = False) -> Path | None:
        """返回资源图片的完整路径。
        - ensure_dir=False（默认）：只读模式，文件不存在则返回 None。
        - ensure_dir=True：写入模式，需要时创建父目录并返回路径（即使文件现在不存在）。
        """
        here = Path(__file__).resolve().parent
        p = here.parent / "resource" / name
        if ensure_dir:
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        return p if p.exists() else None

    def init_licence(self):
        """初始化许可证系统"""
        # user_docs = os.path.join(os.path.expanduser('~'), 'Documents')
        # log_dir = os.path.join(user_docs, 'AR_Analyser_Logs',)
        # log_dir = os.path.join(log_dir, CACHE_FILE_LICENCE_QL, )
        p = self.lic_path(CACHE_FILE_LICENCE_QL, True)
        self.licence_path = p
        
        # 获取硬件指纹
        self.board_serial_number_md5 = self.get_serial_number(
            "PSRegulation-" + self.get_base_board_serial_number())
        self.core = LicenceCore(self.board_serial_number_md5)
        # 检查许可证文件
        licence_id = ""
        result = self.check_licence_by_file(self.licence_path, licence_id)
        if result == self.RESULT_NORMAL:
            self.is_continue = False
            self.authorized.emit()

    def licence_verifies_sus(self):
        """许可证验证是否成功"""
        return self.result == self.RESULT_NORMAL

    # def get_check_result_msg(self):
    #     """获取验证结果消息"""
    #     if self.result == self.RESULT_NORMAL:
    #         return ""
    #
    #     messages = {
    #         self.RESULT_INIT: "还未验证授权！",
    #         self.RESULT_NO_AUTH_FILE: "无授权信息，请联系售后获得授权信息！",
    #         self.RESULT_ILLEGAL: "授权信息异常，请联系售后获得正确授权信息！",
    #         self.RESULT_FILE_ABNORMAL: "授权文件异常，请联系售后获得正确授权信息！",
    #         self.RESULT_NOT_LOCAL_AUTH_FILE: "非本机授权信息，请联系售后获得正确授权信息！",
    #         self.RESULT_NOT_AVAILABLE: "授权信息不可用，请联系售后获得正确授权信息！",
    #         self.RESULT_AUTH_TIME_ABNORMAL: "授权信息时间异常，请联系售后获得正确授权信息！",
    #         self.RESULT_USE_TIME_ABNORMAL: "授权使用时间异常，请联系售后获得正确授权信息！",
    #         self.RESULT_TRIAL_EXPIRES: "试用已到期，请联系售后获得使用授权！",
    #         self.RESULT_AUTH_EXPIRES: "授权已到期，请联系售后延长使用授权！"
    #     }
    #
    #     return messages.get(self.result, "未知的验证授权错误！")

    def check_licence_by_file(self, lic_path, licence_id):
        """通过文件检查许可证"""
        licence_id = ""
        if not self.need_licence:
            self.result = self.RESULT_NORMAL
            return self.result
            
        if self.result != self.RESULT_INIT:
            return self.result

        if not os.path.exists(lic_path):
            logger.error("licence file not found")
            self.result = self.RESULT_NO_AUTH_FILE
            return self.RESULT_NO_AUTH_FILE
            
        try:
            with open(lic_path, 'r') as file:
                licence_raw = file.read()
        except Exception as e:
            logger.error(f"open licence file failed: {e}")
            self.result = self.RESULT_FILE_ABNORMAL
            return self.RESULT_FILE_ABNORMAL
            
        self.result = self.check_licence(licence_raw, licence_id)
        self.licence_id = licence_id
        return self.result

    def check_licence(self, licence_raw, licence_id, need_clock=True):
        """检查许可证内容"""
        result = self.core.check(licence_raw)

        if result == self.RESULT_NORMAL:
            at = self.core.info()
            self.licence['auth_time'] = self._parse_dt(at.get("auth_time"))
            self.licence['valid_day'] = at.get("valid_days")

        if need_clock and result == self.RESULT_NORMAL:
            # 启动定时检查
            self.auth_clock = QTimer(self)
            self.auth_clock.timeout.connect(self.auth_clock_func)
            self.auth_clock.start(1000 * _TIME_SPLIT)
        return result

    def auth_clock_func(self):
        """定时检查授权状态"""
        self.update_licence_use_time()
        print(self.licence)
        print("info:", self.core.info())

        secs = self._get_remaining_seconds()
        if secs is None:
            return

        # 到期提醒（只提醒一次）
        if secs <= 0 and not self._expired_notified:
            self._expired_notified = True
            self.remind.emit("授权已到期，请尽快续期！", 0)
            return

        need_send = False
        # 如果剩余时间小于需要提醒的最大值，说明有可能需要发送提醒弹窗
        if secs > self._remind_thresholds[0]:
            need_send = False
        elif secs <= self._remind_thresholds[0] and secs > 0:
            need_send = True

        if not need_send:
            return

        for i,t in enumerate(reversed(self._remind_thresholds)):
            if secs > 0 and secs<t:
                if t not in self._fired_thresholds:
                    self._fired_thresholds.add(t)
                    msg = self._format_remind_message(t, secs)
                    self.remind.emit(msg, secs)
                # 遇到第一个大的，直接返回，不继续遍历
                return

    def _format_remind_message(self, threshold_seconds: int, seconds_left: int) -> str:
        """根据阈值生成友好提示"""
        mapping = {
            3 * 24 * 3600: " 3 天内到期",
            24 * 3600: " 1 天内到期",
            3 * 3600: " 3 小时内到期",
            5 * 60: " 5 分钟内到期",
        }
        base = mapping.get(threshold_seconds, f"剩余 {seconds_left} 秒到期")
        return f"授权提醒：{base}，请及时处理（续期/联系售后）。"

    def update_licence_use_time(self):
        """更新许可证使用时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if current_time:
            self.licence['last_use_time'] = current_time

    def get_base_board_serial_number(self):
        """获取主板序列号(硬件指纹)"""
        try:
            w = wmi.WMI()
            for board in w.Win32_BaseBoard():
                return board.SerialNumber
            return ""
        except Exception as e:
            logger.error(f"Failed to get board serial number: {e}")
            return ""

    def get_serial_number(self, board_serial_number=""):
        """格式化序列号"""
        if not board_serial_number:
            return self.board_serial_number_md5
            
        if not board_serial_number:
            return ""
            
        serial_encrypt = QEncryption.encrypt_md5(board_serial_number)
        
        # 格式化为带连字符的序列号
        mid_len = len(serial_encrypt) // 4
        if (len(serial_encrypt) % 4) < 1:
            mid_len -= 1
            
        serial_num = ""
        for i in range(mid_len):
            serial_num += serial_encrypt[4*i:4*(i+1)] + "-"
        serial_num += serial_encrypt[28:32]
        
        return serial_num.upper()

    def save_input_licence_text(self,lic_text):
        """保存输入的许可证文本"""
        licence_id = ""
        self.result = self.check_licence(lic_text, licence_id, True)

        if self.result > self.RESULT_NORMAL:
            return False
            
        try:
            with open(self.licence_path, 'w') as file:
                file.write(lic_text)
            self.authorized.emit()
            return True
        except Exception as e:
            logger.error(f"Failed to save licence: {e}")
            return False
    def _parse_dt(self, dt_str: str):
        """尽量稳妥地解析 auth_time 字符串"""
        if not dt_str:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(dt_str, fmt)
            except Exception:
                continue
        return None

    def _get_remaining_seconds(self):
        """
        根据 当前时间、auth_time、valid_days 计算剩余秒数。
        """
        try:
            expire_dt = self.licence['auth_time'] + timedelta(days=self.licence['valid_day'])
            secs = int((expire_dt - datetime.now()).total_seconds())
            return max(0, secs)
        except Exception as e:
            logger.error(f"Failed to compute remaining seconds: {e}")
            return None
