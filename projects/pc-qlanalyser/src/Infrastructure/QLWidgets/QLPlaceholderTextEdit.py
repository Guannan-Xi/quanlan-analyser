from PyQt5.QtWidgets import QTextEdit, QApplication
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt


class QLPlaceholderTextEdit(QTextEdit):
    def __init__(self, parent=None, placeholderText="", *args, **kwargs):
        super(QLPlaceholderTextEdit, self).__init__(*args, **kwargs)
        self.placeholder_text = placeholderText
        self.placeholder_color = QColor(128, 128, 128, 128)  # 灰色，半透明
        self.setPlaceholder(self.placeholder_text)
        # 禁用垂直滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 禁用水平滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setPlaceholder(self, text):
        self.placeholder_text = text
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.toPlainText() and self.placeholder_text:
            color = self.palette().color(self.foregroundRole())
            painter = QPainter(self.viewport())
            painter.setPen(self.placeholder_color)
            painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignTop, self.placeholder_text)

    def focusInEvent(self, event):
        if not self.toPlainText():
            self.clear()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if not self.toPlainText():
            self.setPlaceholder(self.placeholder_text)
        super().focusOutEvent(event)
