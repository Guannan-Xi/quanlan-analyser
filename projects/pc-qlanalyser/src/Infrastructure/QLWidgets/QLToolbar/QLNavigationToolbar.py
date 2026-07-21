import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from ...LLMApi.MdStreamConvertor import MdStreamConvertor


class QLNavigationToolbar(NavigationToolbar):
    def __init__(self, canvas, parent, answer_area):

        #self.toolitems = [t for t in NavigationToolbar.toolitems if t[0] == 'Save']
        super().__init__(canvas, parent)
        self.text_area = answer_area
        self.md_stream_convertor = MdStreamConvertor()
        # # 添加一个新的按钮
        # self.custom_button = QPushButton("Custom", parent)
        # self.custom_button.clicked.connect(self.on_custom_button_clicked)
        #
        # # 将新按钮添加到工具栏
        # self.addWidget(self.custom_button)

        # 修改按钮颜色
        # for button in self.findChildren(QtWidgets.QToolButton):
        #     if 'save' in button.text().lower():
        #         button.setText("Save")
        #         #button.setIcon(None)
        #         button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        #         button.setStyleSheet("""
        #         QToolButton {
        #                 background-color: #e0e0e0;
        #                 border: none;
        #                 padding: 2px;
        #                 border-radius: 4px;
        #             }
        #             """)
    def do_save(self, file_name):
        if file_name.lower().endswith(('.jpg', '.jepg')):
            dpi_value = 72
        else:
            dpi_value = 300
        if file_name:
            self.canvas.figure.savefig(file_name, dpi=dpi_value)

    def save_figure(self, *args):
        # 自定义保存逻辑
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self.canvas.parent(), "Choose path to save", "",
            "JPEG Files(General-dpi mode)(*.jpg *.jpeg);;PNG Files(high-dpi mode) (*.png);;SVG (*.svg)",
            options=options)  #;;EPS(*.eps)

        self.do_save(file_name)

        #TODO
        self.ask_llm(file_name)

    # TODO
    def ask_llm(self, file_name):
        try:
            from ...LLMApi.DeepSeekAPI import DeepSeekAPIBySF
            from ...LLMApi.QianWenAPI import QianWenAPI, QianWenModel
            self.accessor = QianWenAPI(QianWenModel.QWEN_PLUS.value)  # TODO 要修改类只赋值一次，connect也是一次
            self.accessor.stream_signal.connect(self.append_answer)
            self.accessor.stream_end_signal.connect(self.answer_end)
            fileid = self.accessor.upload_file(file_name)
            role = "你是一个睡眠专家或者医生"
            question = """
            帮助查看文件中的睡眠分时图，黄色代表清醒，蓝色代表非快速眼动，红色代表睡醒。帮输出睡眠质量评估，包括睡眠质量得分，满分100分，并给出改善建议。总体不超过500字；不要出现X%这种没有具体数字的百分比。不要说好的，直接回答评估结果
            """
            self.text_area.appendPlainText("\n全澜大模型睡眠评估：\n\n")
            self.md_stream_convertor.preprocess(self.text_area)
            self.accessor.sleep_report(role, fileid, question)  # TODO 需要支持可重入
            self.accessor.delete_file(fileid)
        except Exception as e:
            print(f"Error in ask_llm")
            import traceback
            traceback.print_exc()

    def append_answer(self, text):
        self.md_stream_convertor.append_answer(self.text_area, text)
        # from PyQt5.QtGui import QTextCursor
        #
        # # 移动光标到文档末尾
        # cursor = self.text_area.textCursor()
        # cursor.movePosition(QTextCursor.End)
        # # 插入文本
        # cursor.insertText(text)
        # from PyQt5.QtWidgets import QApplication
        # QApplication.instance().processEvents()

    def answer_end(self, text):
        if text == "True":
            self.md_stream_convertor.postprocess(self.text_area, text)
            # self.diag_commit_button.setEnabled(True)
            self.text_area.appendPlainText("")