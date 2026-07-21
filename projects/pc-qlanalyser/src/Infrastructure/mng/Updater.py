# from pyupdater import PyUpdater
# from pyupdater.client import Client
from .Version import Version, config
import os
import requests
import sys
from pathlib import Path
import threading
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from src.Infrastructure.log.QLLogging import QLLogging
from src.utils import ConfigManager

from enum import Enum, auto

config = ConfigManager("./config/config.dat")


class UpdateStatus(Enum):
    """
    更新状态枚举类
    """
    INITIAL = 0  # 初始状态
    WAIT_CONFIRM = 1  # 等待用户确认下载
    DOWNLOADING = 2  # 正在下载
    WAIT_RESTART = 3  # 等待重启安装
    REMIND_RESTART = 4  # 提醒重启


class Updater:
    def __init__(self, home_path, update_signal):

        self.version_url = config.config['version_url']
        self.file_url = ''
        self.full_path_name = ''
        self.new_version_code = None

        self.extract_dir_prefix = "extract_dir"
        self.pkg_pattern = "QLanalyserpkg*.zip"
        self.extract_dir_pattern = f"{self.extract_dir_prefix}*"

        self.seq = 1

        self.home_dir = os.path.dirname(
            os.path.abspath(home_path))  # "D:\Users\wuhuayun\AppData\Local\Programs\QLanalyser"
        self.work_dir = self.get_work_dir(self.home_dir)  # temp\update
        self.extract_dir = self.get_extract_dir(self.work_dir)
        QLLogging.log.info(f"home_dir: {self.home_dir}")
        QLLogging.log.info(f"work_dir+: {self.home_dir + os.sep}")
        print("home_dir:", self.home_dir)
        print("work_dir+:", self.home_dir + os.sep)
        self.update_status = UpdateStatus.INITIAL

        self.update_signal = update_signal

    def is_open_update(self):
        # TODO
        # 看用户开关和网络
        return True

    def get_remote_version(self, url):
        import requests
        # 调用
        reg_code = self.get_serial_number(
            "PSRegulation-" + self.get_base_board_serial_number())
        QLLogging.log.info(f"机器码（registrationCode）: {reg_code}")
        params = {'type': '13', 'registrationCode': reg_code}
        headers = {}

        # 定义空代理字典，告诉 requests 不要使用任何系统代理
        proxies = {
            "http": None,
            "https": None,
        }

        # 网络请求异常处理
        try:
            # 添加 proxies=proxies 参数
            response = requests.get(url, params=params, headers=headers, proxies=proxies)
            response.raise_for_status()  # 检查请求是否成功
        except requests.exceptions.RequestException as e:
            QLLogging.log.error(f"Failed to get remote version: {e}")
            return None, None, None, None

        # JSON 解析
        try:
            payload = response.json()
        except ValueError as e:
            QLLogging.log.error(f"Failed to parse JSON response: {e}")
            return None, None, None, None

        # 检查响应状态码和数据
        data = payload.get('data')
        if not response.status_code == 200 or not data:
            return None, None, None, None
        QLLogging.log.debug(f"response: {data}")
        if data:
            appPath = data.get('appPath')
            versionCode = data.get('versionCode')
            versionName = data.get('versionName')
            description = data.get('description')
            QLLogging.log.debug(f"get path:{appPath}, {versionCode}")
            return appPath, versionCode, versionName, description
        return None, None

    # 新增注册码register
    def get_base_board_serial_number(self):
        """获取主板序列号(硬件指纹)"""
        # 引入 pythoncom 用于线程初始化
        import pythoncom
        import wmi

        # 1. 显式初始化 COM
        pythoncom.CoInitialize()

        try:
            w = wmi.WMI()
            for board in w.Win32_BaseBoard():
                return board.SerialNumber
            return ""
        except Exception as e:
            # 建议打印具体错误以便后续排查
            print(f"Error getting serial number: {e}")
            return ""
        finally:
            # 2. 必须释放资源，否则可能导致内存泄漏或线程问题
            pythoncom.CoUninitialize()

    def encrypt_md5(self, text):
        import hashlib
        """MD5加密"""
        if isinstance(text, str):
            text = text.encode('utf-8')
        return hashlib.md5(text).hexdigest()

    def get_serial_number(self, board_serial_number=""):
        """格式化序列号"""
        # if not board_serial_number:
        #     return self.board_serial_number_md5

        if not board_serial_number:
            return ""

        serial_encrypt = self.encrypt_md5(board_serial_number)

        # 格式化为带连字符的序列号
        mid_len = len(serial_encrypt) // 4
        if (len(serial_encrypt) % 4) < 1:
            mid_len -= 1

        serial_num = ""
        for i in range(mid_len):
            serial_num += serial_encrypt[4 * i:4 * (i + 1)] + "-"
        serial_num += serial_encrypt[28:32]

        return serial_num.upper()

    def get_seq(self):
        ret = self.seq
        self.seq += 1
        if self.seq > 88888888:
            self.seq = 0
        return ret

    def get_work_dir(self, home_dir):
        return home_dir + os.sep + "temp" + os.sep + "update"

    def get_extract_dir(self, work_dir):
        now = datetime.now()
        dir_name = self.extract_dir_prefix + now.strftime('%Y%m%d%H%M%S') + str(self.get_seq())
        dir_path = work_dir + os.sep + dir_name
        return dir_path

    def gen_work_dir(self):
        path = Path(self.work_dir)
        path.mkdir(parents=True, exist_ok=True)
        print(f"create dir successfully:{self.work_dir}")

    def gen_extract_dir(self):
        path = Path(self.extract_dir)
        path.mkdir(parents=True, exist_ok=True)
        print(f"create dir successfully:{self.extract_dir}")

    def check_and_fill_for_update(self, remote_url):
        if not self.is_open_update():
            return False
        file_url, version_code, versionName, description = self.get_remote_version(remote_url)
        if version_code and file_url:
            if Version.need_upgrade(version_code):
                self.file_url = file_url
                self.full_path_name = self.work_dir + os.sep + Path(file_url).name
                self.new_version_code = version_code
                self.versionName = versionName
                self.description = description
                return True
        return False

    def download_update(self, url, destination):
        self.gen_work_dir()
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            QLLogging.log.error(f"Failed to download update: {e}")
            QMessageBox.critical(None, "Error", f"Failed to download update: {e}")
            return

        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    def install_update(self, file_path):
        self.run_installer_silently(file_path)

    def backup(self):
        # TODO
        pass

    def safe_delete(self, pattern, is_directory=False):
        import glob
        import shutil
        path = self.work_dir + os.sep + pattern
        items = glob.glob(path)
        if not items:
            print(f"no {path} ")
            return

        for item in items:
            try:
                if is_directory:
                    shutil.rmtree(item)
                    print(f"rm: {item} successfully")
                else:
                    os.remove(item)
                    print(f"rm: {item} successfully")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to remove {item}: {e}")
                QLLogging.log.exception(f"rm {item} failed: {e}")

    def cleanup_file(self):
        self.safe_delete(self.pkg_pattern)
        self.safe_delete(self.extract_dir_pattern, True)

    def unzip_file_exit(self, zip_path, extract_to):
        if not os.path.exists(zip_path):
            print(f"{zip_path} not exist in unzip_file!!!")
            return

        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        # 检查解压后的文件是否包含非法文件夹
        entries = os.listdir(extract_to)
        extracted_dirs = [
            name for name in entries
            if os.path.isdir(os.path.join(extract_to, name))
        ]
        # 允许存在的顶层子文件夹
        allowed = {'_internal', 'config', 'resource'}

        invalid = [d for d in extracted_dirs if d not in allowed]
        if invalid:
            QMessageBox.critical(None, "Error",
                                 f"Installation package is not available"
                                 )
            QLLogging.log.error(
                "Installation package is not available"
                f"unzip_file_exit: illegal subfolder detected {invalid}；"
                f"Update packages can only contain {allowed} directories"
            )
            self.update_status = UpdateStatus.DOWNLOADING
            return

        update_path = self.home_dir + os.sep + "update.bat"
        src_update_file_path = self.extract_dir + os.sep + "update.bat"
        self.upgrade_bat_if_exist(src_update_file_path, update_path)

    def upgrade_bat_if_exist(self, src_file, dst_file):
        if os.path.isfile(src_file) and os.path.isfile(dst_file):
            import shutil
            try:
                # 复制文件到目标目录
                shutil.move(src_file, dst_file)
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to upgrade update.bat: {e}")
                QLLogging.log.exception(f"upgrade_bat_if_exist exception: {e}")

    def run_installer_silently(self, pkg_path):
        file = pkg_path.lower()
        if file.endswith('.exe'):
            # #TODO
            # subprocess.Popen([exe_path, '/S'], shell=False)  # 不使用 shell=True，避免潜在的安全风险
            # sys.exit(0)
            pass
        elif file.endswith('.zip'):
            self.gen_extract_dir()
            self.unzip_file_exit(pkg_path, self.extract_dir)
        else:
            print("unknown file type")

    def notify_run_update_bat(self):
        print(f"notify_run_update_bat")
        update_path = self.home_dir + os.sep + "update.bat"
        exe_path = self.home_dir + os.sep + "AR_analyser.exe"
        QLLogging.log.debug(f"exe_path:{exe_path}")
        cmd = [update_path, self.extract_dir, self.home_dir, exe_path]
        # self.update_signal.emit("restart_update", f"{update_path} {self.extract_dir} {self.home_dir} {exe_path}")
        self.update_signal.emit("restart_update", cmd)

    def is_wait_yes_for_download(self):
        return self.update_status == UpdateStatus.WAIT_CONFIRM

    def auto_update(self, download=None):
        if not self.check_and_fill_for_update(self.version_url):  # 检查是否需要更新
            return
        QLLogging.log.debug(f"enter auto_update:{download}, {self.update_status}")

        if self.update_status == UpdateStatus.WAIT_CONFIRM and download is None:  # wait for choosing
            return

        if self.update_status == UpdateStatus.WAIT_CONFIRM and download:  # 用户确认下载  进入下载状态
            self.update_status = UpdateStatus.DOWNLOADING
        import time
        second_confirm_span = 7200  # s
        match self.update_status:
            case UpdateStatus.INITIAL:
                self.cleanup_file()  # TODO clean file，要把上次启动的文件也清理掉
                QLLogging.log.debug(f"find a newer version pkg")
                self.update_signal.emit("check_download", [self.versionName, self.description])
                self.update_status = UpdateStatus.WAIT_CONFIRM
            case UpdateStatus.WAIT_CONFIRM:  # wait yes for download
                time.sleep(second_confirm_span)
                status_msg = f"[updating]:find a newer version, will download new package from server"
                QLLogging.log.debug(status_msg)
                self.update_signal.emit("check_download", [status_msg])
            case UpdateStatus.DOWNLOADING:  # start to download
                self.update_signal.emit("status", ["[updating]:downloading........."])
                QLLogging.log.debug(f"start to download file from:{self.file_url}")
                self.download_update(self.file_url, self.full_path_name)
                QLLogging.log.debug(f"finish download file:{self.full_path_name}")
                self.install_update(self.full_path_name)
                self.update_status = UpdateStatus.WAIT_RESTART
                QLLogging.log.debug(f"Waiting for restart")
            case UpdateStatus.WAIT_RESTART:  # notify main thread to restart
                self.notify_run_update_bat()
                self.update_status = UpdateStatus.REMIND_RESTART
            case UpdateStatus.REMIND_RESTART:
                time.sleep(second_confirm_span)
                self.notify_run_update_bat()
            case _:
                return


lock = threading.Lock()


class UpdaterTask(QThread):
    # 定义一个信号，可以携带任意类型的数据
    update_signal = pyqtSignal(str, list)

    def __init__(self, home_path):
        super().__init__()
        self.home_path = home_path
        self.download = None
        self.updater = None

    def connect(self, update_signal_from_user):
        update_signal_from_user.connect(self.proc_signal)
        self.updater = Updater(self.home_path, self.update_signal)

    def proc_signal(self, str):
        with lock:
            if str == "download":
                self.download = True
            elif str == "no_download":
                self.download = False
            QLLogging.log.debug(f"proc_signal: download：{self.download}")

    def run(self):
        import time
        while True:
            try:
                # QLLogging.log.debug(f"run updater task")
                notify_down = None
                with lock:
                    if self.updater.is_wait_yes_for_download():
                        if self.download is None:
                            time.sleep(0.5)
                            # QLLogging.log.debug(f"continue:is_wait_yes_for_download.")
                            continue
                        else:
                            notify_down = self.download
                            self.download = None
                self.updater.auto_update(notify_down)
                QLLogging.log.debug(f"auto_update: notify_down:{notify_down}, self.download:{self.download}")
                time.sleep(120)  # 模拟耗时操作
            except Exception as e:
                QLLogging.log.exception(f"UpdaterTask run failed: {e}")
                time.sleep(1800)  # 模拟耗时操作
