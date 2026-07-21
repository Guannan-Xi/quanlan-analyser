import os
import platform
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent
if (PROJECT_ROOT / "AR_neurokit2").is_dir():
    project_root_text = str(PROJECT_ROOT)
    if project_root_text not in sys.path:
        # 源码运行时优先加载当前仓库的 AR_neurokit2，避免误用外部旧包。
        sys.path.insert(0, project_root_text)

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
# 必须在创建 QApplication 之前导入 QWebEngineWidgets，以避免导入错误
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
except ImportError:
    # 如果未安装 QtWebEngine，则跳过导入（某些功能可能不可用）
    pass

from src.Data_Info import Ui_Data_info, MainWindow
from PyQt5.QtGui import QIcon
import psutil
from src.Infrastructure.mng.Updater import UpdaterTask
from src.Infrastructure.log.QLLogging import QLLogging
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
from src.Domain.OPLog.OPLog  import OPLogTask, OPType, OPLog
from src.Control_Style import ControlStyle
from src.utils import ConfigManager

import psutil
import time
import win32event
import win32api
import winerror
from src.Clience import Licence
from src.AuthorizationCodeWindow import CodeWindow

class SingleInstance:
    """ Limits application to single instance """
    def __init__(self, name="QLANALYSER"):
        self.mutex_name = name
        self.mutex = win32event.CreateMutex(None, False, self.mutex_name)
        self.last_error = win32api.GetLastError()

    def is_already_running(self):
        return self.last_error == winerror.ERROR_ALREADY_EXISTS

    def __del__(self):
        if self.mutex:
            win32api.CloseHandle(self.mutex)

def monitor_memory_usage():
    """监控当前进程的内存使用情况"""
    process = psutil.Process()
    while True:
        # 获取内存信息(MB)
        memory_info = process.memory_info().rss / 1024 / 1024
        print(f"Memory Usage: {memory_info:.2f} MB")
        time.sleep(2)  # 每秒更新一次

def log_backend_diagnostics():
    try:
        import AR_neurokit2 as nk

        neurokit_file = getattr(nk, "__file__", None)
        neurokit_version = getattr(nk, "__version__", None)
        neurokit_error = None
    except Exception as exc:
        neurokit_file = None
        neurokit_version = None
        neurokit_error = repr(exc)

    try:
        from AR_neurokit2.complexity import _rust_backend

        backend = _rust_backend.get_backend()
        backend_file = getattr(backend, "__file__", None) if backend is not None else None
        rust_available = _rust_backend.is_available()
        rust_error = _rust_backend.get_backend_error()
        rust_thread_count = _rust_backend.thread_count() if rust_available else None
    except Exception as exc:
        backend_file = None
        rust_available = False
        rust_error = repr(exc)
        rust_thread_count = None

    try:
        from AR_neurokit2.complexity import _cuda_cpp_fullscale_backend

        cuda_cpp_wrapper_file = getattr(_cuda_cpp_fullscale_backend, "__file__", None)
        # 启动诊断不能 import CUDA C++ .pyd；原生访问冲突无法被 Python try/except 捕获。
        cuda_cpp_available = "not_checked_at_startup"
        cuda_cpp_error = "CUDA C++ backend is loaded only when explicitly selected."
        cuda_cpp_backend_file = None
    except Exception as exc:
        cuda_cpp_wrapper_file = None
        cuda_cpp_available = False
        cuda_cpp_error = repr(exc)
        cuda_cpp_backend_file = None

    try:
        from numba import cuda

        numba_cuda_available = cuda.is_available()
    except Exception as exc:
        numba_cuda_available = False
        QLLogging.log.info(f"Numba CUDA availability check failed: {exc!r}")

    QLLogging.log.info(f"runtime python: {sys.version.replace(os.linesep, ' ')}")
    QLLogging.log.info(f"runtime executable: {sys.executable}")
    QLLogging.log.info(f"runtime platform: {platform.platform()}")
    QLLogging.log.info(f"AR_neurokit2 file: {neurokit_file}")
    QLLogging.log.info(f"AR_neurokit2 version: {neurokit_version}")
    QLLogging.log.info(f"AR_neurokit2 import error: {neurokit_error}")
    QLLogging.log.info(f"AR_neurokit2 Rust available: {rust_available}")
    QLLogging.log.info(f"AR_neurokit2 Rust backend file: {backend_file}")
    QLLogging.log.info(f"AR_neurokit2 Rust backend error: {rust_error}")
    QLLogging.log.info(f"AR_neurokit2 Rust thread count: {rust_thread_count}")
    QLLogging.log.info(f"AR_neurokit2 CUDA C++ wrapper file: {cuda_cpp_wrapper_file}")
    QLLogging.log.info(f"AR_neurokit2 CUDA C++ available: {cuda_cpp_available}")
    QLLogging.log.info(f"AR_neurokit2 CUDA C++ backend file: {cuda_cpp_backend_file}")
    QLLogging.log.info(f"AR_neurokit2 CUDA C++ backend error: {cuda_cpp_error}")
    QLLogging.log.info(f"Numba CUDA available: {numba_cuda_available}")

def on_application_quit():
    OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.BASIC.value, 'stop application', 0)
    SQLLiteDB_Only_MainTread.close()
    QLLogging.log.info("......................analyser stop successfully......................")

analyser = SingleInstance()

if analyser.is_already_running():
    print("The program is already running and will exit...")
    QLLogging.log.info("The program is already running and will exit...")
    app = QtWidgets.QApplication([])
    app.setWindowIcon(QIcon('QL1.ico'))
    QtWidgets.QMessageBox.critical(None, "Notice", "The program is already running and will exit...")
    sys.exit(0)

QLLogging.init()
log_backend_diagnostics()

app = QtWidgets.QApplication(sys.argv)
app.setWindowIcon(QIcon('QL1.ico'))

# ---------- 解析命令行参数 ----------
import sys
use_qeeg = len(sys.argv) >= 7
if use_qeeg:
    edfpath = sys.argv[1]
    username = sys.argv[2]
    gender = sys.argv[3]
    age = sys.argv[4]
    create_date = sys.argv[5]
    analyst = sys.argv[6]

# ---------- 根据参数创建窗口 ----------
if use_qeeg:
    from src.QEEGAnalysis import Ui_qeeg_analysis, QEEGAnalysisMainWindow
    main_window = QEEGAnalysisMainWindow(edfpath, username, gender, age, create_date, analyst)
else:
    # 原有 Data Info 窗口
    main_window = MainWindow()
    main_window.ui_main.licence = Licence(main_window)
    main_window.ui_main.licence.remind.connect(main_window.ui_main.on_remind)
    # 为了统一访问，将 licence 也挂载到窗口实例上
    main_window.licence = main_window.ui_main.licence

current_working_directory = os.getcwd()
QLLogging.log.info(f"current working directory: {current_working_directory}")



if __name__ == "__main__":
    import multiprocessing

    # PyInstaller 下防止 multiprocessing/joblib 子进程重复启动主窗口。
    multiprocessing.freeze_support()

    QLLogging.log.info(f"......................analyser startup......................")

    try:
        app.setStyleSheet(ControlStyle.get_menuBar_style())

        SQLLiteDB_Only_MainTread.connect()
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.BASIC.value, 'start application', 0)
        # 授权检查
        licence = main_window.licence
        # 暂时关闭授权检查
        licence.need_licence=True

        # 如果需要授权且当前未通过，则弹出授权窗口
        if licence.need_licence and (not licence.licence_verifies_sus()):
            dlg = CodeWindow(licence)
            dlg.setWindowModality(Qt.ApplicationModal)
            # 阻塞等待用户输入授权码
            result = dlg.exec_()
            # 再验一次（授权成功时 save_input_licence_text 已经落盘）
            if not licence.licence_verifies_sus():
                print(licence.result)
                QtWidgets.QMessageBox.critical(None, "授权失败", "未获得有效授权，程序将退出。")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.BASIC.value, 'stop application', 1)
                SQLLiteDB_Only_MainTread.close()
                sys.exit(0)

        # 检查更新
        updater_task = UpdaterTask(os.path.abspath(sys.executable))
        if use_qeeg:
            updater_task.connect(main_window.notify_update_signal)
            main_window.set_update_task_signal(updater_task.update_signal)
        else:
            updater_task.connect(main_window.ui_main.notify_update_signal)
            main_window.ui_main.set_update_task_signal(updater_task.update_signal)
        updater_task.start()  # 启动后台线程

        thread_oplog = OPLogTask()
        thread_oplog.start()
        main_window.show()

        app.aboutToQuit.connect(on_application_quit)
        sys.exit(app.exec_())

    except Exception as e:
        QLLogging.log.exception(f"main exception: {e}")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.BASIC.value, 'stop application', 1)

        SQLLiteDB_Only_MainTread.close()
        sys.exit()

# 当文件不存在或者通道数不对 ，打开Data info
