from .transdata2edf import find_file, data_translate_edf, data_translate_edf_path, is_dir_all_file
import time
import os
from PyQt5.QtWidgets import QProgressDialog, QMessageBox
from PyQt5 import QtCore

def process_path(path):
    print("1")
    if not os.path.exists(path):
        QMessageBox.warning(None, "错误", "路径无效，请选择一个有效的文件夹。")
        return

    progressDialog = QProgressDialog("Processing...", "Abort", 0, 0)
    progressDialog.setWindowModality(QtCore.Qt.WindowModal)
    progressDialog.setMinimumDuration(500)  # 显示半秒后显示对话框
    progressDialog.setWindowTitle("Please Wait")
    #progressDialog.show()

    if os.path.isfile(path):
        data_single_translate_edf(path)
    elif os.path.isdir(path):
        data_batch_translate_edf(path)

    progressDialog.close()


def data_single_translate_edf(path):
    err = data_translate_edf(path)
    if err is None:
        #go_to_format_conversion_2()
        pass
    else:
        QMessageBox.information(None, "提示", err)

def data_batch_translate_edf(path):
    start_time = time.time()

    def func(path: str):
        if os.path.isdir(path) and is_dir_all_file(path):
            def find_x8_data(path: str):
                return path.endswith('.eeg') or path.endswith('.acc') or path.endswith('.qle')
            ret = find_file(path, find_x8_data)
            return len(ret) > 0
        else:
            return False
        
    dirs = find_file(path, func, find_dir=True, recursion=True)
    if func(path):
        dirs.append(path)

    for d in dirs:
        data_translate_edf_path(d)
    print(dirs)
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Transformation took {execution_time} seconds to run.")


