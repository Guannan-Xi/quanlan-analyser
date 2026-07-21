import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtGui import QMovie, QPainter, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSignal


class GifProgressBar(QWidget):
    valueChanged = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.progress = 0
        self.movie = QMovie("resource/picture/move.gif")
        self._maximum = 100  # 默认最大值

        if not self.movie.isValid():
            print("GIF 加载失败！请检查路径或文件格式")
            return

        self.movie.setScaledSize(QSize(40, 40))

        # 优化2: 设置缓存模式以提高性能
        self.movie.setCacheMode(QMovie.CacheAll)

        self.movie.frameChanged.connect(self.update)
        self.movie.setSpeed(150)
        self.movie.start()

        # 设置固定高度，确保有足够空间显示GIF
        self.setFixedHeight(100)
        # 设置最小宽度
        self.setMinimumWidth(350)


    def setGreaterValue(self, value):
        if value > self.progress:
            old_value = self.progress
            self.progress = value
            if old_value != self.progress:  # 仅在值实际变化时发出信号
                self.valueChanged.emit(self.progress)
        pass
    
    def resetValue(self):
        old_value = self.progress
        self.progress = 0
        if old_value != self.progress:
            self.valueChanged.emit(self.progress)  # 发出信号

    def value(self):
        return self.progress

    def maximum(self):
        return self._maximum  # 提供 maximum() 方法

    def paintEvent(self, event):
        #print("enter paintEvent")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        margin = 5

        # 绘制进度条背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.lightGray)
        painter.drawRoundedRect(10, height - 30, width - 20, 20, 5, 5)

        # 绘制进度
        progress_width = int((width - 20) * self.progress / 100)
        painter.setBrush(QColor("#2A87DB"))  #TODO
        painter.drawRoundedRect(10, height - 30, progress_width, 20, 5, 5)

        # 绘制GIF
        if not self.movie.currentPixmap().isNull():
            gif_x = 10 + progress_width - self.movie.currentPixmap().width() // 2
            gif_y = height - 30 - self.movie.currentPixmap().height()
            painter.drawPixmap(gif_x, gif_y, self.movie.currentPixmap())

            # 设置字体（新增部分）
            font = painter.font()
            font.setPointSize(12)  # 设置字体大小为12（可根据需要调整）
            font.setBold(True)  # 可选：加粗字体
            painter.setFont(font)

            # # 绘制百分比文本
            painter.setPen(QColor("#2A87DB"))
            text = f"{self.progress}%"
            font_metrics = painter.fontMetrics()
            text_width = font_metrics.horizontalAdvance(text)
            text_x = max(margin, width - margin - text_width)  # 固定在进度条末端附近
            text_y = height - 30 - self.movie.currentPixmap().height() - 5
            painter.drawText(text_x, text_y , text)  # 注意：drawText的y坐标是基线位置


    # 添加sizeHint方法，告诉布局管理器我们需要的空间
    def sizeHint(self):
        return QSize(1000, 150)


