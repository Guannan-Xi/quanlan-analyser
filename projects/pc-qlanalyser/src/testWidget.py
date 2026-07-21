# # # # # # # # # # import sys
# # # # # # # # # # import time
# # # # # # # # # # from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
# # # # # # # # # # from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QPushButton
# # # # # # # # # #
# # # # # # # # # # # ------------------- 子线程：处理耗时任务 -------------------
# # # # # # # # # # class TaskThread(QThread):
# # # # # # # # # #     progress_signal = pyqtSignal(int)  # 进度更新信号
# # # # # # # # # #
# # # # # # # # # #     def run(self):
# # # # # # # # # #         total_steps = 100
# # # # # # # # # #         for step in range(total_steps + 1):
# # # # # # # # # #             self.progress_signal.emit(step)  # 发送进度
# # # # # # # # # #             time.sleep(0.1)  # 模拟耗时操作
# # # # # # # # # #         self.progress_signal.emit(100)  # 任务结束
# # # # # # # # # #
# # # # # # # # # # # ------------------- 主窗口：UI 交互 -------------------
# # # # # # # # # # class TimerProgressDemo(QWidget):
# # # # # # # # # #     def __init__(self):
# # # # # # # # # #         super().__init__()
# # # # # # # # # #         self.init_ui()
# # # # # # # # # #         self.task_thread = None  # 子线程对象
# # # # # # # # # #
# # # # # # # # # #     def init_ui(self):
# # # # # # # # # #         layout = QVBoxLayout()
# # # # # # # # # #         self.progress_bar = QProgressBar(self)
# # # # # # # # # #         self.progress_bar.setRange(0, 100)
# # # # # # # # # #         layout.addWidget(self.progress_bar)
# # # # # # # # # #
# # # # # # # # # #         self.start_btn = QPushButton("启动任务", self)
# # # # # # # # # #         self.start_btn.clicked.connect(self.start_task)
# # # # # # # # # #         layout.addWidget(self.start_btn)
# # # # # # # # # #
# # # # # # # # # #         self.setLayout(layout)
# # # # # # # # # #
# # # # # # # # # #     def start_task(self):
# # # # # # # # # #         self.task_thread = TaskThread()
# # # # # # # # # #         # 关联子线程的进度信号到进度条更新
# # # # # # # # # #         self.task_thread.progress_signal.connect(self.update_progress)
# # # # # # # # # #         self.task_thread.start()  # 启动子线程
# # # # # # # # # #
# # # # # # # # # #     def update_progress(self, value):
# # # # # # # # # #         self.progress_bar.setValue(value)
# # # # # # # # # #         if value == 100:
# # # # # # # # # #             self.task_thread.wait()  # 等待线程结束
# # # # # # # # # #             self.task_thread = None
# # # # # # # # # #
# # # # # # # # # # if __name__ == "__main__":
# # # # # # # # # #     app = QApplication(sys.argv)
# # # # # # # # # #     demo = TimerProgressDemo()
# # # # # # # # # #     demo.show()
# # # # # # # # # #     sys.exit(app.exec_())
# # # # # # # # # #
# # # # # # # # # # # import sys
# # # # # # # # # # # from PyQt5.QtCore import QTimer, Qt
# # # # # # # # # # # from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
# # # # # # # # # # # import time
# # # # # # # # # # #
# # # # # # # # # # # class TimeDisplayWindow(QMainWindow):
# # # # # # # # # # #     def __init__(self):
# # # # # # # # # # #         super().__init__()
# # # # # # # # # # #         self.init_ui()
# # # # # # # # # # #         self.timer = QTimer(self)
# # # # # # # # # # #         self.timer.timeout.connect(self.update_time)  # 定时更新时间
# # # # # # # # # # #         self.timer.start(1000)  # 每秒触发一次
# # # # # # # # # # #
# # # # # # # # # # #     def init_ui(self):
# # # # # # # # # # #         # 创建中心部件和布局
# # # # # # # # # # #         central_widget = QWidget()
# # # # # # # # # # #         layout = QVBoxLayout(central_widget)
# # # # # # # # # # #
# # # # # # # # # # #         # 时间显示标签
# # # # # # # # # # #         self.time_label = QLabel("", self)
# # # # # # # # # # #         self.time_label.setAlignment(Qt.AlignCenter)
# # # # # # # # # # #         self.time_label.setStyleSheet("font-size: 24px; font-weight: bold;")
# # # # # # # # # # #         layout.addWidget(self.time_label)
# # # # # # # # # # #
# # # # # # # # # # #         self.setCentralWidget(central_widget)
# # # # # # # # # # #         self.setWindowTitle("实时时间显示")
# # # # # # # # # # #         self.setGeometry(300, 300, 300, 150)
# # # # # # # # # # #
# # # # # # # # # # #         # 首次更新时间
# # # # # # # # # # #         self.update_time()
# # # # # # # # # # #
# # # # # # # # # # #     def update_time(self):
# # # # # # # # # # #         """获取当前时间并更新界面"""
# # # # # # # # # # #         current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
# # # # # # # # # # #         self.time_label.setText(current_time)
# # # # # # # # # # #
# # # # # # # # # # #
# # # # # # # # # # # if __name__ == "__main__":
# # # # # # # # # # #     app = QApplication(sys.argv)
# # # # # # # # # # #     window = TimeDisplayWindow()
# # # # # # # # # # #     window.show()
# # # # # # # # # # #     sys.exit(app.exec_())
# # # # # # # # #
# # # # # # # # # import sys
# # # # # # # # # from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
# # # # # # # # # from PyQt5.QtGui import QKeySequence
# # # # # # # # # from PyQt5.QtWidgets import QShortcut
# # # # # # # # #
# # # # # # # # #
# # # # # # # # # class MainWindow(QMainWindow):
# # # # # # # # #     def __init__(self):
# # # # # # # # #         super().__init__()
# # # # # # # # #         self.initUI()
# # # # # # # # #
# # # # # # # # #     def initUI(self):
# # # # # # # # #         # 创建主窗口部件
# # # # # # # # #         central_widget = QWidget()
# # # # # # # # #         self.setCentralWidget(central_widget)
# # # # # # # # #
# # # # # # # # #         # 创建布局
# # # # # # # # #         layout = QVBoxLayout(central_widget)
# # # # # # # # #
# # # # # # # # #         # 创建按钮
# # # # # # # # #         self.button = QPushButton("点击我或按Shift+1")
# # # # # # # # #         self.button.clicked.connect(self.on_button_click)
# # # # # # # # #         layout.addWidget(self.button)
# # # # # # # # #
# # # # # # # # #         # 创建标签
# # # # # # # # #         self.label = QLabel("等待操作...")
# # # # # # # # #         layout.addWidget(self.label)
# # # # # # # # #
# # # # # # # # #         # 设置窗口属性
# # # # # # # # #         self.setWindowTitle('Shift+1快捷键示例')
# # # # # # # # #         self.setGeometry(300, 300, 300, 200)
# # # # # # # # #
# # # # # # # # #         # 创建Shift+1快捷键
# # # # # # # # #         self.shortcut = QShortcut(QKeySequence("Shift+1"), self)
# # # # # # # # #         self.shortcut.activated.connect(self.on_button_click)
# # # # # # # # #
# # # # # # # # #     def on_button_click(self):
# # # # # # # # #         # 按钮点击或快捷键触发时执行的函数
# # # # # # # # #         self.label.setText("Shift+1快捷键已触发!")
# # # # # # # # #
# # # # # # # # #
# # # # # # # # # if __name__ == '__main__':
# # # # # # # # #     app = QApplication(sys.argv)
# # # # # # # # #     window = MainWindow()
# # # # # # # # #     window.show()
# # # # # # # # #     sys.exit(app.exec_())
# # # # # # # import sys
# # # # # # # from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel
# # # # # # # from PyQt5.QtGui import QPixmap
# # # # # # # from PyQt5.QtCore import Qt, QRect, QSize
# # # # # # # from PyQt5.Qt import QMovie
# # # # # # #
# # # # # # #
# # # # # # # class ProgressWithGif(QWidget):
# # # # # # #     def __init__(self):
# # # # # # #         super().__init__()
# # # # # # #
# # # # # # #         # 设置窗口标题和初始大小
# # # # # # #         self.setWindowTitle("Progress Bar with GIF")
# # # # # # #         self.setGeometry(100, 100, 400, 200)
# # # # # # #
# # # # # # #         # 创建布局
# # # # # # #         layout = QVBoxLayout()
# # # # # # #
# # # # # # #         # 创建进度条
# # # # # # #         self.progressBar = QProgressBar(self)
# # # # # # #         self.progressBar.setRange(0, 100)
# # # # # # #         self.progressBar.setValue(0)
# # # # # # #         layout.addWidget(self.progressBar)
# # # # # # #
# # # # # # #         # 创建一个用于显示GIF的标签
# # # # # # #         self.movieLabel = QLabel(self)
# # # # # # #         layout.addWidget(self.movieLabel)
# # # # # # #
# # # # # # #         # 加载GIF
# # # # # # #         self.movie = QMovie("../resource/gif/DinosaurProgressBar.gif")
# # # # # # #         # 关键：设置GIF的缩放尺寸（宽300像素，高200像素）
# # # # # # #         self.movie.setScaledSize(QSize(64, 64))
# # # # # # #         self.movieLabel.setMovie(self.movie)
# # # # # # #         self.movie.start()
# # # # # # #
# # # # # # #         # 设置定时器更新进度条
# # # # # # #         self.timer = self.startTimer(100)  # 每100毫秒触发一次timerEvent
# # # # # # #         self.progress_value = 0
# # # # # # #
# # # # # # #         # 初始化位置信息
# # # # # # #         self.movie_initial_width = self.movie.frameRect().width()
# # # # # # #         self.movie_initial_height = self.movie.frameRect().height()
# # # # # # #
# # # # # # #         self.setLayout(layout)
# # # # # # #
# # # # # # #     def timerEvent(self, event):
# # # # # # #         # 更新进度条的值
# # # # # # #         self.progress_value += 1
# # # # # # #         if self.progress_value > 100:
# # # # # # #             self.killTimer(self.timer)
# # # # # # #         else:
# # # # # # #             self.progressBar.setValue(self.progress_value)
# # # # # # #
# # # # # # #             # 根据进度条调整GIF的位置或大小
# # # # # # #             # 这里以调整大小为例
# # # # # # #             new_width = int(self.movie_initial_width * (self.progress_value / 100))
# # # # # # #             new_height = int(self.movie_initial_height * (self.progress_value / 100))
# # # # # # #             self.movieLabel.setFixedSize(new_width, new_height)
# # # # # # #
# # # # # # #
# # # # # # # if __name__ == '__main__':
# # # # # # #     app = QApplication(sys.argv)
# # # # # # #     window = ProgressWithGif()
# # # # # # #     window.show()
# # # # # # #     sys.exit(app.exec_())
# # # # # # #
# # # # # # #
# # # # # # # # import sys
# # # # # # # # from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
# # # # # # # # from PyQt5.QtGui import QMovie
# # # # # # # # from PyQt5.QtCore import Qt
# # # # # # # #
# # # # # # # # class GifViewer(QWidget):
# # # # # # # #     def __init__(self):
# # # # # # # #         super().__init__()
# # # # # # # #
# # # # # # # #         self.setWindowTitle("PyQt5 显示 GIF 示例")
# # # # # # # #         self.resize(400, 300)
# # # # # # # #
# # # # # # # #         layout = QVBoxLayout()
# # # # # # # #
# # # # # # # #         # 创建 QLabel 并居中显示
# # # # # # # #         self.gif_label = QLabel(self)
# # # # # # # #         self.gif_label.setAlignment(Qt.AlignCenter)
# # # # # # # #
# # # # # # # #         # 加载 GIF
# # # # # # # #         self.movie = QMovie("test.gif")
# # # # # # # #         if not self.movie.isValid():
# # # # # # # #             print("❌ GIF 文件加载失败，请检查路径或文件有效性")
# # # # # # # #             return
# # # # # # # #         else:
# # # # # # # #             print("✅ GIF 文件加载成功")
# # # # # # # #
# # # # # # # #         # 设置 GIF 到 QLabel 上
# # # # # # # #         self.gif_label.setMovie(self.movie)
# # # # # # # #
# # # # # # # #         # 开始播放 GIF
# # # # # # # #         self.movie.start()
# # # # # # # #
# # # # # # # #         # 将 QLabel 添加到布局中
# # # # # # # #         layout.addWidget(self.gif_label)
# # # # # # # #         self.setLayout(layout)
# # # # # # # #
# # # # # # # # if __name__ == '__main__':
# # # # # # # #     app = QApplication(sys.argv)
# # # # # # # #     window = GifViewer()
# # # # # # # #     window.show()
# # # # # # # #     sys.exit(app.exec_())
# # # # # #
# # # # import sys
# # # # from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QSlider, QVBoxLayout
# # # # from PyQt5.QtGui import QMovie
# # # # from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, pyqtProperty
# # # #
# # # # class AnimatedGif(QLabel):
# # # #     def __init__(self, parent=None):
# # # #         super().__init__(parent)
# # # #         self._pos_x = 0  # 控制水平位置的属性
# # # #
# # # #     # 定义动画属性
# # # #     def get_pos_x(self):
# # # #         return self._pos_x
# # # #
# # # #     def set_pos_x(self, x):
# # # #         self._pos_x = x
# # # #         self.move(x, self.y())  # 更新标签位置
# # # #
# # # #     pos_x = pyqtProperty(int, get_pos_x, set_pos_x)
# # # #
# # # #
# # # # class GifSliderDemo(QWidget):
# # # #     def __init__(self):
# # # #         super().__init__()
# # # #         self.initUI()
# # # #
# # # #     def initUI(self):
# # # #         # 创建GIF标签
# # # #         self.gif_label = AnimatedGif(self)
# # # #         self.movie = QMovie("../resource/gif/DinosaurProgressBar.gif")
# # # #         self.gif_label.setMovie(self.movie)
# # # #         self.movie.start()
# # # #
# # # #         # 创建水平进度条
# # # #         self.slider = QSlider(Qt.Horizontal, self)
# # # #         self.slider.setRange(0, 400)  # 设置进度条范围
# # # #         self.slider.setValue(0)  # 初始位置
# # # #
# # # #         # 连接进度条值变化信号到自定义槽函数
# # # #         # self.slider.valueChanged.connect(self.update_gif_position)
# # # #
# # # #         self.progressBar = QProgressBar()
# # # #         self.progressBar.setMinimumSize(258, 16)
# # # #         self.progressBar.setTextVisible(False)  # 关闭进度条中间的文本显示
# # # #
# # # #         # 布局
# # # #         layout = QVBoxLayout()
# # # #         layout.addWidget(self.gif_label)
# # # #         layout.addWidget(self.slider)
# # # #         self.setLayout(layout)
# # # #
# # # #         # 设置窗口属性
# # # #         self.setWindowTitle('GIF随进度条移动')
# # # #         self.setGeometry(300, 300, 600, 400)
# # # #         self.show()
# # # #
# # # #     def update_gif_position(self, value):
# # # #         # 创建动画，使GIF平滑移动到新位置
# # # #         self.anim = QPropertyAnimation(self.gif_label, b'pos_x')
# # # #         self.anim.setDuration(200)  # 动画持续时间(毫秒)
# # # #         self.anim.setStartValue(self.gif_label.pos_x)
# # # #
# # # #         print("----------------------------------")
# # # #         print(f"self.gif_label.pos_x:{self.gif_label.pos_x}")
# # # #         print(f"value:{value}")
# # # #         print("----------------------------------")
# # # #         self.anim.setEndValue(value)
# # # #         self.anim.start()
# # # #
# # # #
# # # # if __name__ == '__main__':
# # # #     app = QApplication(sys.argv)
# # # #     ex = GifSliderDemo()
# # # #     sys.exit(app.exec_())
# # # # #
# # # # #
# # # import sys
# # # from PyQt5.QtWidgets import (QApplication, QWidget, QProgressBar, QVBoxLayout,
# # #                              QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
# # #                              QPushButton)
# # # from PyQt5.QtGui import QMovie, QPixmap
# # # from PyQt5.QtCore import Qt, QTimer
# # # #
# # # #
# # # # class GifProgressBarDemo(QWidget):
# # # #     def __init__(self):
# # # #         super().__init__()
# # # #         self.initUI()
# # # #
# # # #     def initUI(self):
# # # #         # 创建图形视图和场景
# # # #         self.scene = QGraphicsScene(self)
# # # #         self.view = QGraphicsView(self.scene)
# # # #         self.view.setFixedSize(600, 200)
# # # #         self.view.setRenderHint(QPainter.Antialiasing)
# # # #
# # # #         # 创建GIF图形项
# # # #         self.gif_item = QGraphicsPixmapItem()
# # # #         self.scene.addItem(self.gif_item)
# # # #
# # # #         # 加载GIF
# # # #         self.movie = QMovie("../resource/gif/DinosaurProgressBar.gif")
# # # #         self.movie.frameChanged.connect(self.update_frame)
# # # #         self.movie.start()
# # # #
# # # #         # 创建进度条
# # # #         self.progress_bar = QProgressBar(self)
# # # #         self.progress_bar.setRange(0, 100)
# # # #         self.progress_bar.setValue(0)
# # # #         self.progress_bar.valueChanged.connect(self.update_gif_position)
# # # #
# # # #         # 添加测试按钮
# # # #         self.start_btn = QPushButton("开始", self)
# # # #         self.start_btn.clicked.connect(self.start_progress)
# # # #
# # # #         # 布局
# # # #         layout = QVBoxLayout()
# # # #         layout.addWidget(self.view)
# # # #         layout.addWidget(self.progress_bar)
# # # #         layout.addWidget(self.start_btn)
# # # #         self.setLayout(layout)
# # # #
# # # #         self.setWindowTitle('GIF随进度条移动(高级版)')
# # # #         self.setGeometry(300, 300, 600, 400)
# # # #         self.show()
# # # #
# # # #     def update_frame(self):
# # # #         # 更新GIF帧
# # # #         pixmap = self.movie.currentPixmap()
# # # #         self.gif_item.setPixmap(pixmap)
# # # #         self.gif_item.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)
# # # #
# # # #     def update_gif_position(self, value):
# # # #         # 计算GIF的新位置
# # # #         scene_width = self.scene.width()
# # # #         item_width = self.gif_item.pixmap().width()
# # # #         max_x = scene_width - item_width
# # # #         new_x = value * max_x / 100
# # # #         self.gif_item.setPos(new_x, 50)  # Y坐标固定为50
# # # #
# # # #     def start_progress(self):
# # # #         # 模拟进度条增长
# # # #         self.progress = 0
# # # #         self.timer = QTimer()
# # # #         self.timer.timeout.connect(self.update_progress)
# # # #         self.timer.start(50)  # 更快的更新频率
# # # #
# # # #     def update_progress(self):
# # # #         self.progress += 1
# # # #         self.progress_bar.setValue(self.progress)
# # # #         if self.progress >= 100:
# # # #             self.timer.stop()
# # # #
# # # #
# # # # # 注意：需要导入QPainter
# # # # from PyQt5.QtGui import QPainter
# # # #
# # # # if __name__ == '__main__':
# # # #     app = QApplication(sys.argv)
# # # #     ex = GifProgressBarDemo()
# # # #     sys.exit(app.exec_())
# # #
# # # import sys
# # # from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel
# # # from PyQt5.QtGui import QPixmap
# # # from PyQt5.QtCore import Qt, QTimer, QSize
# # #
# # # class ProgressWithGif(QWidget):
# # #     def __init__(self):
# # #         super().__init__()
# # #
# # #         self.setWindowTitle("进度条与GIF同步示例")
# # #         self.setGeometry(100, 100, 400, 200)
# # #
# # #         # 创建布局
# # #         layout = QVBoxLayout()
# # #
# # #         # 创建进度条
# # #         self.progressBar = QProgressBar(self)
# # #         self.progressBar.setRange(0, 100)  # 设置进度条范围
# # #         self.progressBar.setValue(0)  # 初始值设为0
# # #
# # #         self.container = QWidget(self)
# # #         self.container.setStyleSheet("background-color: transparent; border: none;")
# # #         self.container.setAttribute(Qt.WA_TranslucentBackground)
# # #
# # #         # 创建 QLabel 显示 GIF
# # #         self.gif_label = QLabel()
# # #         self.gif_label.setParent(self.container)
# # #         self.gif_label.move(0, 0)
# # #         self.gif_label.setFixedSize(64, 64)
# # #         self.movie = QMovie("../resource/gif/DinosaurProgressBar.gif")  # 替换为你的GIF路径
# # #         self.movie.setScaledSize(QSize(64, 64))
# # #         if not self.movie.isValid():
# # #             print("❌ GIF 文件加载失败，请检查路径或文件有效性")
# # #             return
# # #         else:
# # #             print("✅ GIF 文件加载成功")
# # #
# # #         self.gif_label.setMovie(self.movie)
# # #         self.movie.start()
# # #
# # #         # 将控件添加到布局中
# # #         layout.addWidget(self.progressBar)
# # #         layout.addWidget(self.gif_label)
# # #         self.setLayout(layout)
# # #
# # #         # 初始化 GIF 的初始位置
# # #         self.updateGifPosition()
# # #
# # #         # 定时器模拟进度条更新
# # #         self.timer = QTimer(self)
# # #         self.timer.timeout.connect(self.updateProgress)
# # #         self.timer.start(100)  # 每100毫秒更新一次进度
# # #
# # #         self.progressBar.valueChanged.connect(self.updateGifPosition)
# # #
# # #     def updateProgress(self):
# # #         """ 更新进度条 """
# # #         value = self.progressBar.value() + 1
# # #         if value > self.progressBar.maximum():
# # #             self.timer.stop()
# # #             return
# # #         self.progressBar.setValue(value)
# # #         # self.updateGifPosition()
# # #
# # #     def updateGifPosition(self):
# # #         """ 根据进度条的值调整 GIF 的位置 """
# # #         progress_value = self.progressBar.value()
# # #         gif_width = self.gif_label.width()
# # #         bar_width = self.progressBar.width()
# # #
# # #         # 计算新的X坐标
# # #         new_x = (progress_value / self.progressBar.maximum()) * (bar_width - gif_width)
# # #
# # #         # 设置新的位置
# # #         # self.gif_label.move(int(new_x), self.gif_label.y())
# # #         #
# # #         # print("---------------------------------------------------")
# # #         # print(progress_value)
# # #         # print(self.progressBar.maximum())
# # #         # print(bar_width)
# # #         # print(gif_width)
# # #         # print(new_x)
# # #         # print(self.gif_label.y())
# # #         # print(self.gif_label.x())
# # #         # print("---------------------------------------------------
# # #
# # #         self.updateGifPosition1(new_x)
# # #
# # #         # 刷新 GUI
# # #         QApplication.processEvents()
# # #
# # #     # 更新位置
# # #     def updateGifPosition1(self, new_x):
# # #         # 确保容器大小足够
# # #         self.container.setFixedSize(self.width(), self.height())
# # #
# # #         # 设置目标控件在容器中的绝对位置
# # #         self.gif_label.setGeometry(int(new_x), self.gif_label.y(),
# # #                                    self.gif_label.width(), self.gif_label.height())
# # #
# # # if __name__ == '__main__':
# # #     app = QApplication(sys.argv)
# # #     window = ProgressWithGif()
# # #     window.show()
# # #     sys.exit(app.exec_())
# #
# #
# # import sys
# # import time
# # import numpy as np
# # from PyQt5.QtGui import QImage, QPainter, QPixmap
# # from PyQt5.QtCore import Qt, QSize
# # import pyqtgraph as pg
# # import matplotlib.pyplot as plt
# # import scipy.signal
# #
# # # ------------------- （你的原有逻辑中，确保有这些对象：ax_hypnogram、plot_eeg、plot_emg、plot_acc、plot_widget 等） ------------------- #
# # # 这里模拟你的部分对象，实际用你代码里的即可
# # fig, ax_hypnogram = plt.subplots()
# # plot_eeg = pg.PlotWidget()
# # plot_emg = pg.PlotWidget()
# # plot_acc = pg.PlotWidget()
# # plot_widget = pg.PlotWidget()
# #
# #
# # def save_combined_plot(dpi, file_type, save_path):
# #     """
# #     合并保存 Matplotlib + PyQtGraph 绘制的图像
# #     :param dpi: 图像分辨率（影响截图清晰度）
# #     :param file_type: 文件类型，如 'png', 'jpg'
# #     :param save_path: 完整保存路径，如 'D:/output/result.png'
# #     """
# #     try:
# #         # ============= Step 1: 对 Matplotlib 画布（ax_hypnogram）截图 ============= #
# #         # 调整 Matplotlib 画布 DPI（提升清晰度）
# #         fig = ax_hypnogram.get_figure()
# #         fig.set_dpi(dpi)
# #         # 渲染为 QImage
# #         mpl_img = QImage(int(fig.get_figwidth() * dpi),
# #                          int(fig.get_figheight() * dpi),
# #                          QImage.Format_ARGB32)
# #         mpl_painter = QPainter(mpl_img)
# #         fig.canvas.render(mpl_painter)
# #         mpl_painter.end()
# #
# #         # ============= Step 2: 对 PyQtGraph 画布（plot_eeg 等）截图 ============= #
# #         # 可根据实际布局，灵活调整要截图的 widget
# #         widgets_to_capture = [plot_eeg, plot_emg, plot_acc, plot_widget]
# #         pg_imgs = []
# #         for widget in widgets_to_capture:
# #             # 用 grab() 截图，QSize 可自定义尺寸，也可直接用 widget.size()
# #             pg_pixmap = widget.grab(QSize(int(widget.width() * (dpi / 96)),  # 96 是默认 DPI，按比例缩放
# #                                           int(widget.height() * (dpi / 96))))
# #             pg_imgs.append(pg_pixmap.toImage())
# #
# #         # ============= Step 3: 拼接所有截图到新画布 ============= #
# #         # 这里仅示例“垂直拼接”，可根据实际布局（上下/左右/网格）调整坐标
# #         total_height = mpl_img.height() + sum(img.height() for img in pg_imgs)
# #         total_width = max(mpl_img.width(), max(img.width() for img in pg_imgs))
# #
# #         combined_img = QImage(total_width, total_height, QImage.Format_ARGB32)
# #         combined_img.fill(Qt.white)  # 背景填充白色
# #
# #         painter = QPainter(combined_img)
# #         # 先画 Matplotlib 图
# #         painter.drawImage(0, 0, mpl_img)
# #         # 再依次画 PyQtGraph 图（垂直排列）
# #         y_offset = mpl_img.height()
# #         for img in pg_imgs:
# #             painter.drawImage(0, y_offset, img)
# #             y_offset += img.height()
# #         painter.end()
# #
# #         # ============= Step 4: 保存最终图像 ============= #
# #         if not combined_img.save(save_path, format=file_type):
# #             raise RuntimeError(f"保存图像失败：{save_path}")
# #         print(f"图像已保存至：{save_path}，DPI={dpi}，类型={file_type}")
# #
# #     except Exception as e:
# #         print(f"保存图像时出错：{str(e)}")
# #         import traceback
# #         traceback.print_exc()
# #
# #
# # # ------------------- 测试调用（替换成你实际的触发逻辑，比如按钮点击） ------------------- #
# # if __name__ == "__main__":
# #     # 模拟你原有代码里的绘图逻辑（实际无需重复写，用你已有的即可）
# #     # Matplotlib 部分
# #     ax_hypnogram.hlines([1, 2, 3], [0, 10, 20], [5, 15, 25], colors=['r', 'g', 'b'], linewidths=2)
# #     ax_hypnogram.set_yticks([1, 2, 3])
# #     ax_hypnogram.set_yticklabels(["Wake", "NREM", "REM"])
# #
# #     # PyQtGraph 部分（简单模拟数据）
# #     plot_eeg.plot(np.random.rand(100), pen='k')
# #     plot_emg.plot(np.random.rand(100), pen='g')
# #     plot_acc.plot(np.random.rand(100), pen='b')
# #
# #     # 调用保存函数
# #     save_combined_plot(
# #         dpi=300,  # 高分辨率
# #         file_type='png',  # 支持 'jpg'/'bmp' 等
# #         save_path='G:/Quanlan/edf文件/test(delete)/combined_plot.png'  # 自定义路径
# #     )
#
# import sys
# from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout,
#                              QCheckBox, QLabel, QPushButton)
# from PyQt5.QtCore import Qt
# from PyQt5.QtGui import QFont
#
#
# class CheckboxFontDemo(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.initUI()
#
#     def initUI(self):
#         # 设置窗口标题和尺寸
#         self.setWindowTitle('QCheckBox 字体加粗示例')
#         self.setGeometry(300, 300, 400, 200)
#
#         # 创建主布局
#         layout = QVBoxLayout()
#         self.setLayout(layout)
#
#         # 创建说明标签
#         self.info_label = QLabel("选中下方的复选框，观察字体变化：")
#         layout.addWidget(self.info_label)
#
#         # 方法1：使用CSS样式表实现选中加粗
#         self.checkbox_css = QCheckBox("使用CSS样式表")
#         self.checkbox_css.setStyleSheet("""
#             QCheckBox {
#                 font-weight: normal;  /* 未选中时正常字体 */
#             }
#             QCheckBox:checked {
#                 font-weight: bold;     /* 选中时加粗 */
#             }
#         """)
#         layout.addWidget(self.checkbox_css)
#
#         # 方法2：使用信号槽动态修改字体
#         self.checkbox_signal = QCheckBox("使用信号槽机制")
#         self.checkbox_signal.stateChanged.connect(self.on_checkbox_state_change)
#         layout.addWidget(self.checkbox_signal)
#
#         # 方法3：组合CSS和信号（增强兼容性）
#         self.checkbox_combined = QCheckBox("组合方案（推荐）")
#         self.checkbox_combined.setStyleSheet("""
#             QCheckBox {
#                 font-weight: normal;
#             }
#             QCheckBox:checked {
#                 font-weight: bold;
#             }
#         """)
#         self.checkbox_combined.stateChanged.connect(self.on_combined_state_change)
#         layout.addWidget(self.checkbox_combined)
#
#         # 显示窗口
#         self.show()
#
#     def on_checkbox_state_change(self, state):
#         """方法2的槽函数：根据选中状态动态设置字体粗细"""
#         font = self.checkbox_signal.font()
#         font.setBold(state == Qt.Checked)  # 选中时加粗
#         self.checkbox_signal.setFont(font)
#
#     def on_combined_state_change(self, state):
#         """方法3的槽函数：确保CSS和字体同步"""
#         font = self.checkbox_combined.font()
#         font.setBold(state == Qt.Checked)
#         self.checkbox_combined.setFont(font)
#
#
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     demo = CheckboxFontDemo()
#     sys.exit(app.exec_())


import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

# 启用全局OpenGL加速
pg.setConfigOptions(useOpenGL=True)

class HighlightItem(pg.GraphicsObject):
    def __init__(self, start_time, end_time, brush=None):
        super().__init__()
        self.start_time = start_time
        self.end_time = end_time
        self.brush = brush or pg.mkBrush(255, 192, 203, 76)
        self.prepareGeometryChange()

    def boundingRect(self):
        return QtCore.QRectF(self.start_time, 0, self.end_time - self.start_time, 1)

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush)
        painter.setPen(pg.mkPen(None))
        painter.drawRect(self.boundingRect())

class FastPlotWidget(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent, useOpenGL=True)
        self.setBackground('w')
        self.showGrid(x=True, y=True)

class HypnogramPlot(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.plot_widget = FastPlotWidget()
        self.layout.addWidget(self.plot_widget)

        self.highlight_regions = []

        # 示例数据
        self.plot_data(np.random.rand(1000), np.arange(1000))

    def plot_data(self, y_data, x_data):
        self.plot_widget.plot(x_data, y_data, pen='b')

    def get_plot_widgets(self):
        return [self.plot_widget]

    def update_highlight(self, start_time, end_time):
        if not self.highlight_regions:
            for widget in self.get_plot_widgets():
                region = HighlightItem(start_time, end_time)
                region.setZValue(1000)
                widget.addItem(region)
                self.highlight_regions.append(region)
        else:
            for region in self.highlight_regions:
                region.start_time = start_time
                region.end_time = end_time
                region.prepareGeometryChange()
                region.update()

# 测试代码
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = HypnogramPlot()
    window.show()

    # 更新高亮区域
    window.update_highlight(200, 400)

    app.exec_()