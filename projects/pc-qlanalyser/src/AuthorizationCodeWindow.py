from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, 
                            QPushButton, QTextEdit, QMessageBox, QApplication)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize
from src.Control_Style import ControlStyle
from src.Clience import Licence
import sys


class MsgTip(QMessageBox):
    """消息提示框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("提示")
        self.setStyleSheet(ControlStyle.get_widget_style())
    
    def showTips(self, iconType, msgText, title="", btn1="", btn2="", callbackFunc=None):
        """显示提示信息"""
        if iconType == "ok":
            self.setIcon(QMessageBox.Information)
        elif iconType == "error":
            self.setIcon(QMessageBox.Critical)
        elif iconType == "warning":
            self.setIcon(QMessageBox.Warning)
            
        self.setText(msgText)
        if title:
            self.setWindowTitle(title)
            
        if btn1 and btn2:
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.button(QMessageBox.Yes).setText(btn1)
            self.button(QMessageBox.No).setText(btn2)
        else:
            self.setStandardButtons(QMessageBox.Ok)
            
        result = self.exec_()
        
        if callbackFunc and (result == QMessageBox.Yes or result == QMessageBox.Ok):
            callbackFunc()
            

class CodeWindow(QDialog):
    """授权码窗口"""
    def __init__(self, licence: Licence, parent=None):
        super().__init__()
        # 初始化授权管理器
        self.licence_manager = licence

        # 创建界面
        if self.licence_manager.is_continue:
            self.setWindowTitle("授权码")
            self.setFixedSize(900, 700)
            # 设置窗口图标
            self.setWindowIcon(QIcon("C:/Users/l_y/Desktop/QuanLan/program/AR_analyser_PC/QL1.ico"))
            # 设置窗口标志
            self.setWindowFlags(Qt.WindowType.Window)  # 普通窗口
            self.setStyleSheet(ControlStyle.get_widget_style())

            # 初始化消息提示组件
            self.msgTips = MsgTip(self)
            self._init_ui()
        else:
            self.close()
        
    def _init_ui(self):
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(55, 40, 40, 20)  # 左底右顶
        layout.setSpacing(10)

        # 提示信息
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 10)
        show_label = QLabel("无授权信息，请联系售后获取授权信息！")
        show_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-size: 36px;
                color: #333333;
                font-weight: bold;
            }
        """)
        show_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(show_label)
        layout.addWidget(title_container)

        # 机器码区域
        machine_code_container = QWidget()
        machine_code_layout = QHBoxLayout(machine_code_container)
        machine_code_layout.setContentsMargins(0, 15, 0, 15)
        machine_code_layout.addStretch()
        machine_code_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 整个布局左对齐
        layout.addWidget(machine_code_container)

        machine_code_label = QLabel("机器码:")
        machine_code_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-size: 28px;
                color: #333333;
                font-weight: bold;
            }
        """)

        self.machine_text = self.licence_manager.get_serial_number("PSRegulation-" + self.licence_manager.get_base_board_serial_number())
        self.machine_code_text = QLabel(self.machine_text)
        self.machine_code_text.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-size: 26px;
                color: #333333;
            }
        """)

        def _icon_path():
            from pathlib import Path
            import sys

            # PyInstaller 下：_MEIPASS 通常指向 ...\_internal
            meipass = Path(getattr(sys, "_MEIPASS", ""))
            exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else None
            here = Path(__file__).resolve().parent  # 通常是 ...\src

            candidates = []
            if getattr(sys, "frozen", False):
                # ① _internal/resource（很多 --add-data/--add-binary 会落在这）
                candidates.append(meipass / "resource" / "picture" / "copy.png")
                # ② exe 同级的 resource（你“打包目录里的 resource”指的就是它）
                candidates.append(exe_dir / "resource" / "picture" / "copy.png")
                # ③ 兼容某些布局：_internal 的上一级就是 exe_dir
                candidates.append(meipass.parent / "resource" / "picture" / "copy.png")
            else:
                # 开发环境：src 同级的 resource
                candidates.append(here.parent / "resource" / "picture" / "copy.png")

            for p in candidates:
                if p and p.exists():
                    return p
            return None
        p = _icon_path()
        copy_button = QPushButton()
        copy_button.setIcon(QIcon(str(p)))
        copy_button.setFixedSize(26, 26)
        copy_button.setStyleSheet(ControlStyle.get_pushButton_style_white())
        copy_button.setToolTip("复制机器码")
        copy_button.setStyleSheet("""
            QPushButton {
                border: none;  /* 移除边框 */
                background: transparent;  /* 设置背景透明 */
                padding: 0px;  /* 移除内边距 */
            }
            QPushButton:hover {
                background-color: rgba(240, 240, 240, 0.5);  /* 悬停时半透明背景 */
                border-radius: 12px;  /* 圆角效果 */
            }
            QPushButton:pressed {
                background-color: rgba(220, 220, 220, 0.7);  /* 按下时背景 */
            }
        """)
        copy_button.clicked.connect(self.copy_machine_code)
        
        machine_code_layout.addWidget(machine_code_label)
        machine_code_layout.addWidget(self.machine_code_text)
        machine_code_layout.addStretch()
        machine_code_layout.addWidget(copy_button)
        
        # 授权码输入区域
        auth_label = QLabel("授权码:")
        auth_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-size: 28px;
                font-weight: bold;
                color: #333333;
            }
        """)
        auth_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(auth_label)
        
        self.auth_code_input = QTextEdit()
        self.auth_code_input.setMinimumHeight(100)
        self.auth_code_input.setStyleSheet("""
            QTextEdit {
                background-color: #F6F9FF;
                border: 1px solid #E5E5E5;
                border-radius: 4px;
                padding: 5px;
                font-family: Microsoft YaHei;
                font-size: 20px;
            }
        """)
        layout.addWidget(self.auth_code_input)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 20, 0, 10)
        
        self.apply_btn = QPushButton("注入授权码")
        self.apply_btn.setStyleSheet(ControlStyle.get_pushButton_style())
        self.apply_btn.setMinimumSize(170, 50)
        self.apply_btn.clicked.connect(self.apply_authorization_code)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2A87DB;
                color: white;
                font-family: Microsoft YaHei;
                font-size: 28px;
            }
        """)

        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def copy_machine_code(self):
        """复制机器码到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.machine_text)
        self.notShowMsgTips("ok", "机器码已拷贝至剪切板！")
        
    def apply_authorization_code(self):
        """注入授权码"""
        auth_code = self.auth_code_input.toPlainText()
        print(f"Applying authorization code: {auth_code}")
        if self.licence_manager.save_input_licence_text(auth_code):
            print("a")
            print(self.licence_manager.result)
            self.notShowMsgTips("ok", "授权码应用成功，即将重新打开软件，请稍等！", callbackFunc=self.close)
        else:
            self.notShowMsgTips("error", "授权码应用失败，请检查授权码是否正确或过期！")
            
    def notShowMsgTips(self, iconType, msgText, callbackFunc=None):
        """显示消息提示"""
        self.msgTips.showTips(iconType, msgText, "", "", "", callbackFunc)
        

if __name__ == "__main__":
    # 确保有一个应用程序实例
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("授权码验证测试")
    app.setOrganizationName("QuanLan")
    
    # 创建并显示授权码窗口
    auth_window = CodeWindow()
    auth_window.show()
    
    try:
        sys.exit(app.exec_())
    except Exception as e:
        print(f"应用程序异常: {e}")
        # 确保程序能够正常退出
        sys.exit(1)