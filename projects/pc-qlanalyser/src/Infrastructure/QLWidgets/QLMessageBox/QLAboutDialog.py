from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QTextBrowser
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextCursor, QTextDocument

class QLAboutDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        # 创建布局
        layout = QVBoxLayout()
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # 创建 QTextEdit 用于显示消息
        self.text_browser = QTextBrowser(self)

        self.text_browser.setHtml(message)
        self.text_browser.setReadOnly(True)  # 设置为只读模式
        self.text_browser.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse | Qt.TextBrowserInteraction)  # 允许文本选择
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.anchorClicked.connect(self.handle_link_click)

        layout.addWidget(self.text_browser)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.accept)  # 关闭对话框
        button_layout.addStretch(1)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.set_style()

    def handle_link_click(self, url: QUrl):
      QDesktopServices.openUrl(url)  # 在默认浏览器中打开链接

    def set_style(self):
        # self.setStyleSheet("""
        #             QMainWindow {
        #                 background-color: #ffffff;
        #             }
        #         """)

        #self.setFixedSize(600, 200)

        # 设置背景颜色
        self.setStyleSheet("background-color: #ffffff;")  # 浅灰色背景
        self.text_browser.setStyleSheet("background-color: white; border: none ; padding: 5px;")
        self.ok_button.setStyleSheet("background-color: #4285F4; color: #000000; padding: 5px 20px; border-radius: 3px;")

    def show_dialog(self):
        self.exec_()
