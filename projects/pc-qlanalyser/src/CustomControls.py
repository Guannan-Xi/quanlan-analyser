from PyQt5 import QtWidgets, QtCore
from .Control_Style import ControlStyle
from .Infrastructure.log.QLLogging import QLLogging

from PyQt5.QtWidgets import (QWidget, QPushButton, QProgressBar, QLabel,QListView,
                           QComboBox, QPlainTextEdit, QGridLayout, QHBoxLayout,
                           QVBoxLayout, QMessageBox, QInputDialog, QSizePolicy, QSlider,
                           QStyle, QStyleOptionSlider, QFrame, QLineEdit, QSpacerItem,
                           QToolButton, QMenuBar, QMenu, QToolButton, QAction, QScrollArea)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QCoreApplication, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap, QMovie,QValidator


# 通道选择
class StyledCheckboxWidget(QtWidgets.QWidget):
    def __init__(self, channel_names, label_text="Channel Selection", parent=None):
        super().__init__(parent)
        self.channel_names = channel_names
        self.label_text = label_text  # 接收构造函数中的 label 文本
        self.checkbox_map = {}  # 初始化 checkbox_map
        self.init_ui()

    def init_ui(self):
        # 创建主布局
        layout = QtWidgets.QVBoxLayout(self)  # 依次放 label，all_widget，channel_widget
        layout.setContentsMargins(30, 20, 20, 20)
        layout.setSpacing(1)

        # 添加顶部的 QLabel
        self.label_6 = QtWidgets.QLabel(self)
        self.label_6.setText(self.label_text)
        self.label_6.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_6, 12)
        layout.addWidget(self.label_6)
        # 添加一个固定像素的垂直间距
        vertical_spacer = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout.addItem(vertical_spacer)

        # 创建 "ALL" 复选框
        all_widget = QtWidgets.QWidget()
        all_widget.setMinimumSize(149, 30)
        all_widget.setStyleSheet(ControlStyle.get_all_widget_style())

        self.all_checkbox = QtWidgets.QCheckBox("ALL")
        self.all_checkbox.setObjectName("All")
        self.all_checkbox.setMinimumSize(149, 10)
        self.all_checkbox.setStyleSheet(ControlStyle.get_all_channel_checkBox_style())
        ControlStyle.get_font_size(self.all_checkbox, 10)

        all_widget_layout = QtWidgets.QVBoxLayout(all_widget)
        all_widget_layout.setContentsMargins(24, 0, 0, 0)
        all_widget_layout.setSpacing(0)
        all_widget_layout.addWidget(self.all_checkbox)
        layout.addWidget(all_widget)

        # 创建通道复选框
        channel_widget = QtWidgets.QWidget()
        channel_widget.setStyleSheet(ControlStyle.get_channel_widget_style())
        channel_widget_layout = QtWidgets.QVBoxLayout(channel_widget)
        channel_widget_layout.setContentsMargins(24, 15, 0, 10)
        channel_widget_layout.setSpacing(15)

        self.channel_checkboxes = []
        for channel_name in self.channel_names:
            checkbox = QtWidgets.QCheckBox(channel_name)
            checkbox.setStyleSheet(ControlStyle.get_all_channel_checkBox_style())
            ControlStyle.get_font_size(checkbox, 10)
            channel_widget_layout.addWidget(checkbox)
            checkbox.stateChanged.connect(self.update_all_checkbox_state)
            self.channel_checkboxes.append(checkbox)
            self.checkbox_map[channel_name] = checkbox  # 将复选框与通道名称映射

        self.all_checkbox.toggled.connect(self.toggle_all_checkboxes)

        # 将通道复选框放入 QScrollArea
        scroll_area = QtWidgets.QScrollArea()
        # 设置滚动区域可调整大小
        scroll_area.setWidgetResizable(False)
        # 设置滚动区域的内容为通道复选框
        scroll_area.setWidget(channel_widget)
        scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())
        # 隐藏水平滚动条
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # 将滚动区域添加到主布局
        layout.addWidget(scroll_area)

        # 设置主布局
        self.setLayout(layout)

    def toggle_all_checkboxes(self, state):
        """全选或取消全选所有通道复选框"""
        for checkBox in self.channel_checkboxes:
            if checkBox.isEnabled():  # 仅对未禁用的复选框操作
                checkBox.setChecked(state)

    def update_all_checkbox_state(self):
        """
        根据通道复选框的状态更新 "ALL" 复选框的状态
        """
        # 阻塞 ALL 复选框的信号
        self.all_checkbox.blockSignals(True)

        # 获取已启用的复选框
        enabled_checkboxes = [cb for cb in self.channel_checkboxes if cb.isEnabled()]

        if not enabled_checkboxes:
            # 如果没有启用的复选框，设置为未选中状态
            self.all_checkbox.setCheckState(QtCore.Qt.Unchecked)
        else:
            # 计算选中状态
            checked_count = sum(1 for cb in enabled_checkboxes if cb.isChecked())
            total_count = len(enabled_checkboxes)

            if checked_count == total_count:
                # 全部选中
                self.all_checkbox.setCheckState(QtCore.Qt.Checked)
            else:
                # 全部未选中
                self.all_checkbox.setCheckState(QtCore.Qt.Unchecked)
            # else:
            #     # 部分选中
            #     self.all_checkbox.setCheckState(QtCore.Qt.PartiallyChecked)

        # 恢复 ALL 复选框的信号
        self.all_checkbox.blockSignals(False)

    def get_selected_channels(self):
        """获取所有选中的通道名称"""
        return [checkbox.text() for checkbox in self.channel_checkboxes if checkbox.isChecked()]
        

    def print_selected_channels(self):
        """打印选中的通道名称"""
        selected_channels = self.get_selected_channels()
        print("Selected Channels:", selected_channels)

    def set_setEnabled_channels(self, enabled_channels):
        """
        根据传入的通道名称列表禁用对应的复选框。
        :param enabled_channels: 要启用的通道名称列表
        """
        for channel_name, checkbox in self.checkbox_map.items():
            if channel_name in enabled_channels:
                checkbox.setEnabled(True)  # 启用复选框
            else:
                checkbox.setEnabled(False)  # 禁用复选框
                checkbox.setChecked(False)  # 确保禁用时取消选中

#定义时间控件
# 定义时间选择框
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QTimeEdit,QSpacerItem
)
from PyQt5.QtCore import QDateTime, QDate, QTime


from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import QDateTime, QDate, QTime, Qt
from PyQt5.QtGui import QDoubleValidator


class TimeRangeSelector(QWidget):
    def __init__(self, parent=None):
        super(TimeRangeSelector, self).__init__(parent)
        self.min_time = None  # 最小时间
        self.max_time = None  # 最大时间
        self.init_ui()
        self.setContentsMargins(0,0,0,0)

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 10, 20, 20)
        pixel_ratio = QApplication.instance().devicePixelRatio() # 获取设备像素比

        # 根据缩放比例调整边距
        margin_left = int(32 * pixel_ratio)
        margin_top = int(10 * pixel_ratio)
        margin_right = int(20 * pixel_ratio)
        margin_bottom = int(20 * pixel_ratio)

        main_layout.setContentsMargins(margin_left, margin_top, margin_right, margin_bottom)
        main_layout.setSpacing(int(self.devicePixelRatio() * 4))

        # 时间选择标签
        self.label_time_selection = QLabel("Time:", self)
        self.label_time_selection.setFixedSize(250, 32)
        self.label_time_selection.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_time_selection, 12)
        main_layout.addWidget(self.label_time_selection, alignment=Qt.AlignLeft)

        # 开始时间布局
        start_layout = QHBoxLayout()
        start_layout.setContentsMargins(0, 0, 0, 0)
        # spacing适配设备像素比
        dpi_ratio = self.devicePixelRatio()
        start_layout.setSpacing(int(dpi_ratio*4))

        # ---- 标签部分：保留固定宽度但适配DPI ----
        self.label_start = QLabel("Start:", self)
        # 最小尺寸/固定宽度适配DPI（原55→55*dpi_ratio）
        label_width = int(55 * dpi_ratio)
        self.label_start.setMinimumSize(label_width, int(32 * dpi_ratio))
        self.label_start.setFixedWidth(label_width)
        self.label_start.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        # 字体大小适配DPI（原10→10*dpi_ratio）
        ControlStyle.get_font_size(self.label_start, int(10 * dpi_ratio))

        # ---- 下拉框部分：同样适配DPI ----
        self.combobox_start = QComboBox(self)
        combo_width = int(150 * dpi_ratio)
        self.combobox_start.setMinimumSize(combo_width, int(32 * dpi_ratio))
        self.combobox_start.setFixedWidth(combo_width)
        self.combobox_start.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_start, int(10 * dpi_ratio))
        # 添加行高
        # 创建 QListView 并设置行高
        view1 = QListView()
        view1.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_start.setView(view1)  # 绑定视图到 QComboBox

        # ---- 时间选择框----
        # self.lineedit_start = QLineEdit(self)
        self.lineedit_start = QTimeEdit(QTime.currentTime())
        # 1. 取消固定宽度！改用最小宽度（适配DPI），让布局自动调整
        time_edit_min_width = int(95 * dpi_ratio)
        self.lineedit_start.setMinimumSize(time_edit_min_width, int(32 * dpi_ratio))
        # self.lineedit_start.setFixedWidth(95)
        # 2. 优化样式：移除内边距，最大化显示空间（核心解决显示不全）
        time_edit_style = f"""
            {ControlStyle.get_timeEdit_style()}  # 保留原有样式
            padding: 2px {2 * dpi_ratio}px;  # 极小内边距（适配DPI）
            border: none;  # 可选：移除边框进一步节省空间（根据需求调整）
        """
        self.lineedit_start.setStyleSheet(time_edit_style)

        # self.lineedit_start.setValidator(None)  # 验证输入为数字
        # 3. 字体大小适配DPI
        ControlStyle.get_font_size(self.lineedit_start, int(10 * dpi_ratio))
        self.lineedit_start.setDisplayFormat("HH:mm:ss")  # 显示小时:分钟:秒

        start_layout.addWidget(self.label_start)
        start_layout.addWidget(self.combobox_start)
        start_layout.addWidget(self.lineedit_start)
        main_layout.addLayout(start_layout)



        # 结束时间布局
        end_layout = QHBoxLayout()
        end_layout.setContentsMargins(0, 0, 0, 0)
        dpi_ratio = self.devicePixelRatio()
        end_layout.setSpacing(int(4 * dpi_ratio))

        self.label_end = QLabel("End:", self)
        label_width = int(55 * dpi_ratio)
        self.label_end.setMinimumSize(label_width, int(32 * dpi_ratio))
        self.label_end.setFixedWidth(label_width)
        self.label_end.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        ControlStyle.get_font_size(self.label_end, int(10 * dpi_ratio))

        self.combobox_end = QComboBox(self)
        combo_width = int(150 * dpi_ratio)
        self.combobox_end.setMinimumSize(combo_width, int(32 * dpi_ratio))
        self.combobox_end.setFixedWidth(combo_width)
        self.combobox_end.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_end, int(10 * dpi_ratio))
        view1 = QListView()
        view1.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_end.setView(view1)  # 绑定视图到 QComboBox

        self.lineedit_end = QTimeEdit(QTime.currentTime())
        time_edit_min_width = int(95 * dpi_ratio)
        self.lineedit_end.setMinimumSize(time_edit_min_width, int(32 * dpi_ratio))
        # self.lineedit_end.setFixedWidth(time_edit_min_width)
        time_edit_style = f"""
            {ControlStyle.get_timeEdit_style()}  # 保留原有样式
            padding: 2px {2 * dpi_ratio}px;  # 极小内边距（适配DPI）
            border: none;  # 可选：移除边框进一步节省空间（根据需求调整）
        """
        self.lineedit_end.setStyleSheet(time_edit_style)
        # self.lineedit_start.setValidator(None)  # 验证输入为数字
        ControlStyle.get_font_size(self.lineedit_end,  int(10 * dpi_ratio))
        self.lineedit_end.setDisplayFormat("HH:mm:ss")  # 显示小时:分钟:秒

        end_layout.addWidget(self.label_end)
        end_layout.addWidget(self.combobox_end)
        end_layout.addWidget(self.lineedit_end)
        main_layout.addLayout(end_layout)

        # 信号连接
        self.combobox_start.currentIndexChanged.connect(self.validate_time_range)
        # self.lineedit_start.textChanged.connect(self.validate_time_range)
        self.combobox_end.currentIndexChanged.connect(self.validate_time_range)
        # self.lineedit_end.textChanged.connect(self.validate_time_range)

    def get_time_range(self):
        """返回选中的时间范围，格式为 QDateTime 元组"""
        start_date = QDate.fromString(self.combobox_start.currentText(), "yyyy-MM-dd")
        start_time = self.lineedit_start.time()
        end_date = QDate.fromString(self.combobox_end.currentText(), "yyyy-MM-dd")
        end_time = self.lineedit_end.time()

        start = QDateTime(start_date, start_time)
        end = QDateTime(end_date, end_time)
        return start, end

    def set_time_range(self, start, end):
        """设置初始时间范围"""
        # 确保 start 和 end 是 datetime.datetime 类型
        # 检查并转换 start 参数
        if isinstance(start, datetime):
            q_start_date = QDate(start.year, start.month, start.day)
            q_start_time = QTime(start.hour, start.minute, start.second)
        elif isinstance(start, QDateTime):
            q_start_date = start.date()
            q_start_time = start.time()
        else:
            raise ValueError("start 参数必须是 datetime.datetime 或 QDateTime 类型")

        # 检查并转换 end 参数
        if isinstance(end, datetime):
            q_end_date = QDate(end.year, end.month, end.day)
            q_end_time = QTime(end.hour, end.minute, end.second)
        elif isinstance(end, QDateTime):
            q_end_date = end.date()
            q_end_time = end.time()
        else:
            raise ValueError("end 参数必须是 datetime.datetime 或 QDateTime 类型")

        # # 打印调试信息
        # print("type(start):", type(start))
        # print("start:", q_start_date, q_start_time)
        # print("type(end):", type(end))
        # print("end:", q_end_date, q_end_time)

        # 确保日期在 QComboBox 中
        start_date_str = q_start_date.toString("yyyy-MM-dd")
        end_date_str = q_end_date.toString("yyyy-MM-dd")
        if start_date_str == end_date_str:
            # 只有一个选项
            self.combobox_start.addItem(start_date_str)
            self.combobox_end.addItem(start_date_str)
        else:
            # 有两个选项
            self.combobox_start.addItem(start_date_str)
            self.combobox_end.addItem(start_date_str)
            self.combobox_start.addItem(end_date_str)
            self.combobox_end.addItem(end_date_str)


        # 设置开始时间
        self.combobox_start.setCurrentText(q_start_date.toString("yyyy-MM-dd"))
        # self.lineedit_start.setText(q_start_time.toString("HH:mm:ss"))
        self.lineedit_start.setTime(q_start_time)

        # 设置结束时间
        self.combobox_end.setCurrentText(q_end_date.toString("yyyy-MM-dd"))
        # self.lineedit_end.setText(q_end_time.toString("HH:mm:ss"))
        self.lineedit_end.setTime(q_end_time)
    # def set_time_range_(self, start, end):
    #     """设置初始时间范围"""
    #     # self.start_date.setDate(start.date())
    #     # self.start_time.setTime(start.time())
    #     # self.end_date.setDate(end.date())
    #     # self.end_time.setTime(end.time())
    #     from PyQt5.QtCore import QDate, QTime
    #
    #     print("type(start):",type(start))
    #     print("start:",start.date() )
    #     print(start.time() )
    #     print("type(end):",type(end))
    #     print("end:",end.date())
    #     print(end.time())
    #     # 设置开始时间
    #     #self.combobox_start.setCurrentText(start.date())
    #     # self.lineedit_start.setText(start.time())
    #
    #     # 设置结束时间
    #     # self.combobox_end.setCurrentText(q_end.date().toString("yyyy-MM-dd"))
    #     # self.lineedit_end.setText(q_end.time().toString("HH:mm:ss"))

    def set_min_time(self, min_time: QDateTime):
        """设置最小时间"""
        self.min_time = min_time
        self.validate_time_range()

    def set_max_time(self, max_time: QDateTime):
        """设置最大时间"""
        self.max_time = max_time
        self.validate_time_range()

    def validate_time_range(self):
        """验证并限制时间范围"""
        start, end = self.get_time_range()

        # 如果开始时间小于最小时间，则恢复为最小时间
        if self.min_time and start < self.min_time:
            #self.set_time_range(self.min_time, end)
            return False

        # 如果结束时间大于最大时间，则恢复为最大时间
        if self.max_time and end > self.max_time:
            #self.set_time_range(start, self.max_time)
            return False

        # 如果开始时间晚于结束时间，则调整为合法范围
        if start > end:
            #self.set_time_range(end, start)
            return False
        return True


#自定义界面   请设置分析参数后点击“Analyse”开始分析"界面
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

class IconWithTextWidget(QWidget):
    def __init__(self, icon_path, text, parent=None):
        super().__init__(parent)
        self.init_ui(icon_path, text)
        self.setContentsMargins(0,0,0,0)

    def init_ui(self, icon_path, text):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(self.devicePixelRatio()*10))  # 图标和文字之间固定10像素

        # 设置布局对齐方式为居中
        layout.setAlignment(Qt.AlignCenter)

        # 添加图标
        icon_label = QLabel(self)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(icon_path)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        # 添加文字
        text_label = QLabel(text, self)
        text_label.setAlignment(Qt.AlignCenter)
        #text_label.setStyleSheet("font-size: 14px; color: #808080;")
        text_label.setStyleSheet("""
            width: 261px;
            height: 14px;
            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 10pt;
            color: #BBBDBF;
            line-height: 14px;
            text-align: left;
            font-style: normal;
            text-transform: none;
        """)
        layout.addWidget(text_label)

        # 设置主布局
        self.setLayout(layout)

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLineEdit, QLabel, QSpacerItem, QSizePolicy

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QDoubleValidator

class FrequencyCheckboxWidget(QtWidgets.QWidget):
    def __init__(self, freq_dict=None, label_text="Frequency Selection", parent=None):
        super().__init__(parent)
        self.freq_dict = freq_dict
        self.label_text = label_text
        self.item_dict = {}  # 用于保存每一项的控件引用
        self.init_ui()

    def init_ui(self):
        # 创建主布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 10, 20, 10)
        layout.setSpacing(1)

        # 添加顶部的 QLabel
        self.label_6 = QtWidgets.QLabel(self)
        self.label_6.setText(self.label_text)
        self.label_6.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_6, 12)
        layout.addWidget(self.label_6)

        # 添加一个固定像素的垂直间距
        vertical_spacer = QtWidgets.QSpacerItem(0, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        layout.addItem(vertical_spacer)

        # 创建 "ALL" 复选框
        all_widget = QtWidgets.QWidget()
        all_widget.setMinimumSize(149, 30)
        all_widget.setStyleSheet(ControlStyle.get_all_widget_style())

        self.all_checkbox = QtWidgets.QCheckBox("ALL")
        self.all_checkbox.setObjectName("All")
        self.all_checkbox.setMinimumSize(149, 30)
        self.all_checkbox.setStyleSheet(ControlStyle.get_all_channel_checkBox_style())
        ControlStyle.get_font_size(self.all_checkbox, 10)

        all_widget_layout = QtWidgets.QVBoxLayout(all_widget)
        all_widget_layout.setContentsMargins(24, 0, 0, 0)
        all_widget_layout.setSpacing(0)
        all_widget_layout.addWidget(self.all_checkbox)
        layout.addWidget(all_widget)

        # 创建通道复选框
        channel_widget = QtWidgets.QWidget()
        channel_widget.setStyleSheet(ControlStyle.get_channel_widget_style())
        channel_widget_layout = QtWidgets.QVBoxLayout(channel_widget)
        channel_widget_layout.setContentsMargins(24, 15, 0, 10)
        channel_widget_layout.setSpacing(int(self.devicePixelRatio()*15) )

        self.channel_checkboxes = []
        for name, freq_range in self.freq_dict.items():
            item = self.create_item_widget(name, freq_range)
            self.item_dict[name] = item
            channel_widget_layout.addWidget(item["widget"])
            self.channel_checkboxes.append(item["checkbox"])

        self.all_checkbox.toggled.connect(self.toggle_all_checkboxes)

        # 将通道复选框放入 QScrollArea
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(channel_widget)
        scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        layout.addWidget(scroll_area)
        # 设置主布局
        self.setLayout(layout)

    def create_item_widget(self, name, range_tuple):
        """创建单个通道复选框及其右侧输入框"""
        item_widget = QtWidgets.QWidget()
        item_layout = QtWidgets.QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 10)
        item_layout.setSpacing(int(self.devicePixelRatio()*10) )

        # 创建复选框
        checkbox = QtWidgets.QCheckBox(name)
        checkbox.setStyleSheet(ControlStyle.get_all_channel_checkBox_style())
        checkbox.stateChanged.connect(self.update_all_checkbox_state)
        ControlStyle.get_font_size(checkbox, 10)
        item_layout.addWidget(checkbox,alignment=Qt.AlignLeft)  # 靠左对齐
        # 添加动态扩展的空白区域
        spacer = QtWidgets.QSpacerItem(5, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        item_layout.addItem(spacer)
        # 创建最小值输入框
        min_edit = QtWidgets.QLineEdit(str(range_tuple[0]))
        min_edit.setFixedWidth(50)
        min_edit.setAlignment(QtCore.Qt.AlignCenter)
        min_edit.setStyleSheet(ControlStyle.get_lineEdit_style())
        min_edit.setValidator(QDoubleValidator())
        # min_edit.setReadOnly(True)  # 设置为只读
        min_edit.hide()
        item_layout.addWidget(min_edit, alignment=Qt.AlignRight)  # 靠右对齐

        # 创建分隔符
        dash_label = QtWidgets.QLabel("-")
        dash_label.setFixedWidth(10)
        #dash_label.setAlignment(QtCore.Qt.AlignCenter)
        dash_label.setStyleSheet("color: #808080; font-size: 14px;")
        dash_label.hide()
        item_layout.addWidget(dash_label, alignment=Qt.AlignRight)  # 靠右对齐

        # 创建最大值输入框
        max_edit = QtWidgets.QLineEdit(str(range_tuple[1]))
        max_edit.setFixedWidth(50)
        max_edit.setAlignment(QtCore.Qt.AlignCenter)
        max_edit.setStyleSheet(ControlStyle.get_lineEdit_style())
        max_edit.setValidator(QDoubleValidator())
        # max_edit.setReadOnly(True)  # 设置为只读
        max_edit.hide()
        item_layout.addWidget(max_edit, alignment=Qt.AlignRight)  # 靠右对齐

        # 添加固定大小的空白区域
        fixed_spacer = QtWidgets.QWidget()
        fixed_spacer.setFixedWidth(40)  # 设置固定宽度为 35 像素
        item_layout.addWidget(fixed_spacer)
        # # 添加动态扩展的空白区域
        # spacer = QtWidgets.QSpacerItem(35, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        # item_layout.addItem(spacer)

        # 连接复选框的状态改变信号
        checkbox.stateChanged.connect(
            lambda state, e1=min_edit, e2=max_edit, d=dash_label: self.on_checkbox_toggle(state, e1, e2, d)
        )

        return {
            "widget": item_widget,
            "checkbox": checkbox,
            "min_edit": min_edit,
            "max_edit": max_edit,
            "dash": dash_label
        }

    def on_checkbox_toggle(self, state, min_edit, max_edit, dash_label):
        """复选框状态改变时显示或隐藏输入框"""
        visible = state == QtCore.Qt.Checked
        min_edit.setVisible(visible)
        max_edit.setVisible(visible)
        dash_label.setVisible(visible)

    def toggle_all_checkboxes(self, state):
        """全选或取消全选所有通道复选框"""
        for item in self.item_dict.values():
            item["checkbox"].setChecked(state)

    def update_all_checkbox_state(self):
        """
        根据通道复选框的状态更新 "ALL" 复选框的状态
        """
        # 阻塞 ALL 复选框的信号
        self.all_checkbox.blockSignals(True)

        # 获取已启用的复选框
        enabled_checkboxes = [cb for cb in self.channel_checkboxes ]

        if not enabled_checkboxes:
            # 如果没有启用的复选框，设置为未选中状态
            self.all_checkbox.setCheckState(QtCore.Qt.Unchecked)
        else:
            # 计算选中状态
            checked_count = sum(1 for cb in enabled_checkboxes if cb.isChecked())
            total_count = len(enabled_checkboxes)

            if checked_count == total_count:
                # 全部选中
                self.all_checkbox.setCheckState(QtCore.Qt.Checked)
            else:
                # 全部未选中
                self.all_checkbox.setCheckState(QtCore.Qt.Unchecked)

        # 恢复 ALL 复选框的信号
        self.all_checkbox.blockSignals(False)

    def get_selected_frequencies(self):
        """返回所有被选中的频段及其范围"""
        result = {}
        for name, item in self.item_dict.items():
            if item["checkbox"].isChecked():
                try:
                    min_val = float(item["min_edit"].text())
                    max_val = float(item["max_edit"].text())
                    result[name] = (min_val, max_val)
                except ValueError:
                    continue  # 忽略无法转换为 float 的内容
        return result

#上侧导航栏  Time Scale 加页面选择
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QCoreApplication

class NavButtonsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)

        # 初始化当前页和总页数
        self.current_page = 1
        self.total_pages = 1

        # 绑定按钮的槽函数
        self.first_pushButton.clicked.connect(self.go_to_first_page)
        self.last_pushButton.clicked.connect(self.go_to_last_page)
        self.button_previous.clicked.connect(self.go_to_previous_page)
        self.button_next.clicked.connect(self.go_to_next_page)

    def initUI(self, parent=None):
        # 整体布局为水平布局
        self.nav_button_widget_hlayout = QHBoxLayout(self)
        self.nav_button_widget_hlayout.setObjectName("nav_button_widget_hlayout")
        self.nav_button_widget_hlayout.setContentsMargins(0, 0, 0, 0)
        self.nav_button_widget_hlayout.setSpacing(int(self.devicePixelRatio()*10) )

        # Time Scale 标签和选择框
        self.label_time_scale = QLabel("Time Scale(h):", self)
        self.label_time_scale.setMinimumSize(100, 32)
        self.label_time_scale.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_time_scale, 10)
        self.nav_button_widget_hlayout.addWidget(self.label_time_scale)

        self.combo_time_scale = QComboBox(self)
        self.combo_time_scale.setMinimumSize(80, 32)
        self.combo_time_scale.addItems(["1", "2", "4", "8", "16", "All"])
        self.combo_time_scale.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combo_time_scale, 10)
        self.combo_time_scale.setCurrentIndex(0)  # 设置默认选择第一个选项
        self.nav_button_widget_hlayout.addWidget(self.combo_time_scale)

        # First 按钮
        self.first_pushButton = QPushButton(parent)
        self.first_pushButton.setObjectName("first_pushButton")
        self.first_pushButton.setMinimumSize(60, 32)
        self.first_pushButton.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.first_pushButton, 10)
        self.nav_button_widget_hlayout.addWidget(self.first_pushButton)
        # 创建一个空白区域
        spacerItem1 = QSpacerItem(12, 32)
        self.nav_button_widget_hlayout.addSpacerItem(spacerItem1)

        # 中间导航按钮布局
        nav_page_hlayout = QHBoxLayout()
        nav_page_hlayout.setContentsMargins(0, 0, 0, 0)
        nav_page_hlayout.setSpacing(0)

        # Previous 按钮
        self.button_previous = QPushButton(parent)
        self.button_previous.setObjectName("button_previous")
        self.button_previous.setMinimumSize(32, 32)
        self.button_previous.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.button_previous, 10)
        nav_page_hlayout.addWidget(self.button_previous)

        # 当前页按钮
        self.button_goto_epoch = QPushButton("1", parent)
        self.button_goto_epoch.setObjectName("button_goto_epoch")
        self.button_goto_epoch.setMinimumSize(32, 32)
        self.button_goto_epoch.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.button_goto_epoch, 10)
        nav_page_hlayout.addWidget(self.button_goto_epoch)

        # 添加一个固定大小的空白区域
        spacer_fixed = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        nav_page_hlayout.addSpacerItem(spacer_fixed)

        # 总页数标签
        self.label_of_page = QLabel("of 1", parent)
        self.label_of_page.setObjectName("label_of_page")
        self.label_of_page.setMinimumSize(59, 32)
        nav_page_hlayout.addWidget(self.label_of_page)

        self.label_of_page.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_of_page, 10)

        # Next 按钮
        self.button_next = QPushButton(parent)
        self.button_next.setObjectName("button_next")
        self.button_next.setMinimumSize(32, 32)
        self.button_next.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.button_next, 10)
        nav_page_hlayout.addWidget(self.button_next)

        self.nav_button_widget_hlayout.addLayout(nav_page_hlayout)

        # 创建一个空白区域
        spacerItem2 = QSpacerItem(12, 32)
        self.nav_button_widget_hlayout.addSpacerItem(spacerItem2)

        # Last 按钮
        self.last_pushButton = QPushButton(parent)
        self.last_pushButton.setObjectName("last_pushButton")
        self.last_pushButton.setMinimumSize(60, 32)
        self.last_pushButton.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.last_pushButton, 10)
        self.nav_button_widget_hlayout.addWidget(self.last_pushButton)

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.first_pushButton.setText(_translate("NavButtonsWidget", "First"))
        self.button_previous.setText(_translate("NavButtonsWidget", "<"))
        self.button_next.setText(_translate("NavButtonsWidget", ">"))
        self.last_pushButton.setText(_translate("NavButtonsWidget", "Last"))

    def get_current_page(self):
        """获取当前页码"""
        return self.current_page

    def set_total_pages(self, total_pages):
        """设置总页数"""
        self.total_pages = total_pages
        self.label_of_page.setText(f"of {total_pages}")

    def set_current_page(self, current_page):
        """设置当前页码"""
        # print("set page:",current_page)
        self.current_page = current_page
        self.button_goto_epoch.setText(str(current_page))
        #print("current_page:",current_page)

    def get_time_scale_hours(self):
        """
        获取当前选择的 Time Scale 值，并返回对应的秒数。
        """
        time_scale = self.combo_time_scale.currentText()
        QLLogging.log.debug(f"Selected Time Scale: {time_scale}")  # 打印选择的时间刻度

        # 将时间刻度转换为秒数
        if time_scale.lower() == "all":
            return None  # 如果选择的是 "All"，返回 None 表示不限制
        try:
            hours = float(time_scale)  # 假设时间刻度是以小时为单位
            seconds = int(hours * 3600)  # 转换为秒
            return seconds
        except ValueError:
            QLLogging.log.error("Invalid Time Scale format.")
            return 0  # 如果格式无效，返回 0

    def get_time_scale_min(self):
        """
        获取当前选择的 Time Scale 值，并返回对应的秒数。
        """
        time_scale = self.combo_time_scale.currentText()
        QLLogging.log.debug(f"Selected Time Scale: {time_scale}")

        # 将时间刻度转换为秒数
        if time_scale.lower() == "all":
            return None  # 如果选择的是 "All"，返回 None 表示不限制
        try:
            minutes = float(time_scale)  # 假设时间刻度是以分钟为单位
            seconds = int(minutes * 60)  # 转换为秒
            return seconds
        except ValueError:
            QLLogging.log.error("Invalid Time Scale format.")
            return 0  # 如果格式无效，返回 0

    # 槽函数
    def go_to_first_page(self):
        """跳转到第一页"""
        self.set_current_page(1)

    def go_to_last_page(self):
        """跳转到最后一页"""
        self.set_current_page(self.total_pages)

    def go_to_previous_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.set_current_page(self.current_page - 1)
        else:
            self.set_current_page(self.total_pages)  # 如果是第一页，则跳转到最后一页

    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.set_current_page(self.current_page + 1)
        else:
            self.set_current_page(1)  # 如果是最后一页，则跳转到第一页

import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSizePolicy,
    QComboBox, QSlider, QGridLayout
)
from PyQt5.QtCore import Qt, QTime, QPoint, QRectF, QTimer
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QMessageBox

import matplotlib.pyplot as plt
import numpy as np

class PropertyWidget(QtWidgets.QWidget):
    def __init__(self, properties=None, title="Property", parent=None):
        super().__init__(parent)
        self.properties = properties or {
            "Frequency (Hz)": (1.0, 4.0),  # (min, max)
            "Window size": 4.0             # 单一值
        }
        self.inputs = {}  # 存储每项输入框的引用
        self.title = title
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 10, 0, 10)
        layout.setSpacing(int(self.devicePixelRatio()*8) )

        # 添加标题标签
        title_label = QtWidgets.QLabel(self.title)
        title_label.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        layout.addWidget(title_label)

        # 添加一个固定像素的垂直间距
        vertical_spacer = QtWidgets.QSpacerItem(0, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        layout.addItem(vertical_spacer)

        # 为每一个属性添加输入行
        for name, value in self.properties.items():
            widget = QtWidgets.QWidget()
            h_layout = QtWidgets.QHBoxLayout(widget)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(int(self.devicePixelRatio()*10) )

            # 添加动态扩展的空白区域
            spacer = QtWidgets.QSpacerItem(5, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            h_layout.addItem(spacer)
            # 左边标签
            label = QtWidgets.QLabel(name)
            label.setFixedWidth(120)
            label.setStyleSheet(ControlStyle.get_all_channel_checkBox_style())
            h_layout.addWidget(label)

            if isinstance(value, tuple):
                # 是范围值（如频率）
                min_edit = QtWidgets.QLineEdit(str(value[0]))
                max_edit = QtWidgets.QLineEdit(str(value[1]))
                for edit in (min_edit, max_edit):
                    edit.setFixedWidth(40)
                    edit.setAlignment(QtCore.Qt.AlignLeft)
                    edit.setValidator(QDoubleValidator())
                    edit.setStyleSheet(ControlStyle.get_lineEdit_style())

                dash = QtWidgets.QLabel("-")
                dash.setFixedWidth(10)
                dash.setAlignment(QtCore.Qt.AlignLeft)
                dash.setStyleSheet("color: #808080; font-size: 14px;")

                h_layout.addWidget(min_edit)
                h_layout.addWidget(dash)
                h_layout.addWidget(max_edit)

                self.inputs[name] = (min_edit, max_edit)
            else:
                # 是单一值（如窗口大小）
                edit = QtWidgets.QLineEdit(str(value))
                edit.setFixedWidth(40)
                edit.setAlignment(QtCore.Qt.AlignLeft)
                edit.setValidator(QDoubleValidator())
                edit.setStyleSheet(ControlStyle.get_lineEdit_style())

                h_layout.addWidget(edit)
                self.inputs[name] = edit
            #widget.setStyleSheet(ControlStyle.get_channel_widget_style())  # 设置与 FrequencyCheckboxWidget 一致的背景样式
            # 添加动态扩展的空白区域
            spacer = QtWidgets.QSpacerItem(5, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            h_layout.addItem(spacer)
            layout.addWidget(widget)

    def get_property_values(self):
        """返回当前所有属性的值，自动判断是范围还是单一值"""
        result = {}
        for name, widget in self.inputs.items():
            if isinstance(widget, tuple):
                try:
                    min_val = float(widget[0].text())
                    max_val = float(widget[1].text())
                    result[name] = (min_val, max_val)
                except ValueError:
                    continue  # 忽略非法输入
            else:
                try:
                    result[name] = float(widget.text())
                except ValueError:
                    continue
        return result

class SliderBubble(QLabel):
    """悬浮气泡标签"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置无边框、透明背景的窗口
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置样式
        self.setStyleSheet("""
            color: #FFFFFF;
            background-color: transparent;
            font-family: Microsoft YaHei;
            font-size: 14px;
            font-weight: 300;
            font-style: normal;
            text-align: center;
            padding: 6px 10px;
        """)
        self.setFixedSize(80, 40)  # 设置气泡的固定大小
        
        # 默认隐藏
        self.hide()
    
    def showAt(self, pos, text):
        """在指定位置显示带有指定文本的气泡"""
        self.setText(text)
        self.adjustSize()
        
        # 计算位置，使气泡位于滑块正上方
        x = pos.x() - self.width() // 2
        y = pos.y() - self.height() - 10  # 滑块上方10像素
        
        self.move(x, y)
        self.show()
    
    def paintEvent(self, event):
        """绘制气泡形状的背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建气泡路径
        path = QPainterPath()
        rect = self.rect().adjusted(2, 2, -2, -8)  # 为小三角留出空间

        rectf = QRectF(rect) # 转化为 浮点矩形
        # 绘制圆角矩形
        path.addRoundedRect(rectf, 6, 6)

        # 添加底部小三角指向滑块
        triangle_width = 8
        triangle_height = 6
        bottom_center_x = rectf.center().x()
        bottom_y = rectf.bottom()
        
        path.moveTo(bottom_center_x - triangle_width//2, bottom_y)
        path.lineTo(bottom_center_x, bottom_y + triangle_height)
        path.lineTo(bottom_center_x + triangle_width//2, bottom_y)
        path.closeSubpath()
        
        # 设置填充颜色
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, int(255*0.4)))  # 半透明黑色
        painter.drawPath(path)
        
        # 绘制边框
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        
        # 绘制文本
        text_rect = rect.adjusted(0, 0, 0, -2)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(text_rect, Qt.AlignCenter, self.text())

        painter.end()

# 滑动条窗口
class TimeSliderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)

    def initUI(self, parent=None):
        # 整体为垂直布局
        self.time_slider_widget_vlayout = QVBoxLayout(self)
        self.time_slider_widget_vlayout.setObjectName("time_slider_widget_vlayout")
        self.time_slider_widget_vlayout.setContentsMargins(25, 0, 33, 0)
        self.time_slider_widget_vlayout.setSpacing(0)

        # 水平布局
        label_time_hlayout = QHBoxLayout()
        label_time_hlayout.setContentsMargins(0, 0, 0, 0)
        label_time_hlayout.setSpacing(0)

        self.label_start_time = QLabel(parent)
        self.label_start_time.setObjectName("label_start_time")
        self.label_start_time.setStyleSheet(ControlStyle.get_time_slider_label_style())

        self.label_end_time = QLabel(parent)
        self.label_end_time.setObjectName("label_end_time")
        self.label_end_time.setStyleSheet(ControlStyle.get_time_slider_label_style())

        label_time_hlayout.addWidget(self.label_start_time, alignment=Qt.AlignLeft)
        label_time_hlayout.addWidget(self.label_end_time, alignment=Qt.AlignRight)

        self.time_slider = CustomSlider(self)
        self.time_slider.setObjectName("time_slider")
        self.time_slider.setOrientation(Qt.Horizontal)  # 设置为水平方向
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.setValue(0)
        self.time_slider.setTotalPages(1)  # 设置总页数为1
        self.time_slider.setStyleSheet(ControlStyle.get_time_slider_style())

        self.time_slider_widget_vlayout.addLayout(label_time_hlayout)
        self.time_slider_widget_vlayout.addWidget(self.time_slider)

class CustomSlider(QSlider):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bubble = SliderBubble()
        self.total_pages = 1
        self.is_dragging = False  # 是否正在拖动滑块
        self.is_hovering = False  # 是否悬停在滑块上

        self.setMouseTracking(True)  # 启用鼠标跟踪
    
    def setTotalPages(self, total_pages):
        self.total_pages = total_pages

    def setCurrentPage(self):
        """设置当前页码"""
        if self.maximum() == self.minimum():
            return 1
            
        # 计算当前值对应的页码
        page = int((self.value() - self.minimum()) /
                (self.maximum() - self.minimum()) * (self.total_pages - 1)) + 1
        return max(1, min(page, self.total_pages))

    def getPageFromPosition(self, x_pos):
        """根据鼠标位置计算对应的页码"""
        if self.maximum() == self.minimum():
            return 1
            
        # 获取滑块手柄区域
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        handle_rect = self.style().subControlRect(
            QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self
        )
        
        # 计算有效轨道宽度
        groove_width = self.width() - handle_rect.width()
        relative_pos = x_pos - handle_rect.width() / 2
        
        # 限制在有效范围内
        if relative_pos < 0:
            relative_pos = 0
        if relative_pos > groove_width:
            relative_pos = groove_width
            
        # 计算相对位置（0-1）
        pos_ratio = relative_pos / groove_width if groove_width > 0 else 0
        
        # 计算对应的页码
        page = int(pos_ratio * (self.total_pages - 1) + 1)
        return max(1, min(page, self.total_pages))
    
    def updateBubble(self, x_pos=None):
        """更新气泡位置和内容"""
        if x_pos is None:
            # 使用当前滑块位置
            handle_pos = self.getHandleGlobalPosition()
            text = f"{self.setCurrentPage()}/{self.total_pages}"
        else:
            # 使用鼠标位置
            mouse_global_pos = self.mapToGlobal(QPoint(x_pos, self.height() // 2))
            page = self.getPageFromPosition(x_pos)
            handle_pos = mouse_global_pos
            text = f"{page}/{self.total_pages}"
        
        # 显示气泡
        self.bubble.showAt(handle_pos, text)
    
    def getHandleGlobalPosition(self):
        """计算滑块中心的全局位置"""
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        
        handle_rect = self.style().subControlRect(
            QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self
        )
        
        # 获取滑块中心的本地坐标
        handle_center = handle_rect.center()
        
        # 转换为全局坐标
        global_pos = self.mapToGlobal(handle_center)
        
        return global_pos

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 获取滑块的矩形区域
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            handle_rect = self.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self
            )

            # 判断点击位置是否在滑块上
            if handle_rect.contains(event.pos()):
                # 点击在滑块上，保留默认行为
                super().mousePressEvent(event)
                self.is_dragging = True
                self.updateBubble()  # 更新气泡位置和内容
                return

            # 点击在凹槽处，计算新位置
            if self.orientation() == Qt.Horizontal:
                # 计算相对位置（排除滑块宽度）
                groove_width = self.width() - handle_rect.width()
                relative_pos = event.pos().x() - handle_rect.width() / 2
                if relative_pos < 0:
                    relative_pos = 0
                if relative_pos > groove_width:
                    relative_pos = groove_width
                pos = relative_pos / groove_width
            else:
                # 垂直方向处理
                groove_height = self.height() - handle_rect.height()
                relative_pos = event.pos().y() - handle_rect.height() / 2
                if relative_pos < 0:
                    relative_pos = 0
                if relative_pos > groove_height:
                    relative_pos = groove_height
                pos = relative_pos / groove_height

            value = round(pos * (self.maximum() - self.minimum()) + self.minimum())
            self.setValue(value)

            # 更新气泡位置和内容
            self.is_dragging = False  # 重置拖动状态
            self.updateBubble(event.pos().x())

            # 阻止默认行为，避免跳动
            return
        # 其他情况调用父类方法
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_dragging:
            # 拖动时更新气泡位置
            self.updateBubble()
        elif self.rect().contains(event.pos()):
            # 悬浮时显示气泡
            if not self.is_hovering:
                self.is_hovering = True
            self.updateBubble(event.pos().x())
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """松开鼠标时隐藏气泡"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            # 如果不在悬浮状态，隐藏气泡
            if not self.is_hovering:
                self.bubble.hide()
        super().mouseReleaseEvent(event)
    
    def enterEvent(self, event):
        """鼠标进入控件时"""
        self.is_hovering = True
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开控件时隐藏气泡"""
        self.is_hovering = False
        if not self.is_dragging:
            self.bubble.hide()
        super().leaveEvent(event)

class BottomLeftWidget(QWidget):
    # 睡眠/癫痫分析页面底部左边窗口
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)

    def initUI(self, parent=None):
        # 创建主布局
        self.bottom_left_widget_vlayout = QVBoxLayout(self)
        self.bottom_left_widget_vlayout.setObjectName("bottom_left_widget_vlayout")
        self.bottom_left_widget_vlayout.setContentsMargins(0, 0, 0, 0)
        self.bottom_left_widget_vlayout.setSpacing(8)

        # Channel Selection
        channel_selection_vlayout = QVBoxLayout()
        channel_selection_vlayout.setContentsMargins(32, 24, 32, 24)
        channel_selection_vlayout.setSpacing(8)

        self.label_channel_selection = QLabel(parent)
        self.label_channel_selection.setObjectName("label_channel_selection")
        self.label_channel_selection.setMinimumSize(250, 32)
        self.label_channel_selection.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_channel_selection, 12)

        # EEG Channel Selection
        eeg_layout = QHBoxLayout()
        eeg_layout.setContentsMargins(0, 0, 0, 0)
        eeg_layout.setSpacing(0)

        self.label_eeg = QLabel(parent)
        self.label_eeg.setObjectName("label_eeg")
        self.label_eeg.setMinimumSize(49, 32)
        self.label_eeg.setStyleSheet(ControlStyle.get_wiget400_word_style(16))
        ControlStyle.get_font_size(self.label_eeg, 10)

        self.combobox_eeg = QComboBox(parent)
        self.combobox_eeg.setObjectName("combobox_eeg")
        self.combobox_eeg.setMinimumSize(201, 32)
        self.combobox_eeg.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_eeg, 10)

        eeg_layout.addWidget(self.label_eeg)
        eeg_layout.addWidget(self.combobox_eeg)

        # EMG Channel Selection
        emg_layout = QHBoxLayout()
        emg_layout.setContentsMargins(0, 0, 0, 0)
        emg_layout.setSpacing(0)

        self.label_emg = QLabel(parent)
        self.label_emg.setObjectName("label_emg")
        self.label_emg.setMinimumSize(49, 32)
        self.label_emg.setStyleSheet(ControlStyle.get_wiget400_word_style(16))
        ControlStyle.get_font_size(self.label_emg, 10)

        self.combobox_emg = QComboBox(parent)
        self.combobox_emg.setObjectName("combobox_emg")
        self.combobox_emg.setMinimumSize(201, 32)
        self.combobox_emg.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_emg, 10)

        emg_layout.addWidget(self.label_emg)
        emg_layout.addWidget(self.combobox_emg)

        # ACC Channel Selection
        acc_layout = QHBoxLayout()
        acc_layout.setContentsMargins(0, 0, 0, 0)
        acc_layout.setSpacing(0)

        self.label_acc = QLabel(parent)
        self.label_acc.setObjectName("label_acc")
        self.label_acc.setMinimumSize(49, 32)
        self.label_acc.setStyleSheet(ControlStyle.get_wiget400_word_style(16))
        ControlStyle.get_font_size(self.label_acc, 10)

        self.combobox_acc = QComboBox(parent)
        self.combobox_acc.setObjectName("combobox_acc")
        self.combobox_acc.setMinimumSize(201, 32)
        self.combobox_acc.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_acc, 10)

        acc_layout.addWidget(self.label_acc)
        acc_layout.addWidget(self.combobox_acc)

        channel_selection_vlayout.addWidget(self.label_channel_selection, alignment=Qt.AlignLeft)
        channel_selection_vlayout.addLayout(eeg_layout)
        channel_selection_vlayout.addLayout(emg_layout)
        channel_selection_vlayout.addLayout(acc_layout)

        self.bottom_left_widget_vlayout.addLayout(channel_selection_vlayout)

        # 添加分割线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Plain)
        separator1.setStyleSheet("background-color: #a9a9a9;")
        separator1.setFixedHeight(1)

        self.bottom_left_widget_vlayout.addWidget(separator1)


        # time selection
        time_selection_vlayout = QVBoxLayout()
        time_selection_vlayout.setContentsMargins(32, 24, 32, 24)
        time_selection_vlayout.setSpacing(4)

        self.label_time_selection = QLabel(parent)
        self.label_time_selection.setObjectName("label_time_selection")
        self.label_time_selection.setMinimumSize(250, 32)
        self.label_time_selection.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_time_selection, 12)
        # 分辨率问题修正
        # start time
        start_layout = QHBoxLayout()
        start_layout.setContentsMargins(0, 0, 0, 0)
        dpi_ratio = self.devicePixelRatio()
        start_layout.setSpacing(int(4 * dpi_ratio))

        self.label_start = QLabel(parent)
        self.label_start.setObjectName("label_start")
        label_width = int(55 * dpi_ratio)
        self.label_start.setMinimumSize(label_width, int(32 * dpi_ratio))
        self.label_start.setFixedWidth(label_width)
        self.label_start.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        ControlStyle.get_font_size(self.label_start, int(10 * dpi_ratio))

        self.combobox_start = QComboBox(parent)
        self.combobox_start.setObjectName("combobox_start")
        combo_width = int(145 * dpi_ratio)
        self.combobox_start.setMinimumSize(combo_width, int(32 * dpi_ratio))
        # self.combobox_start.setFixedWidth(combo_width)
        self.combobox_start.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_start, int(10 * dpi_ratio))

        self.lineedit_start = QTimeEdit(QTime.currentTime())
        time_edit_min_width = int(90 * dpi_ratio)
        self.lineedit_start.setMinimumSize(time_edit_min_width, int(32 * dpi_ratio))
        #self.lineedit_start.setFixedWidth(95)
        time_edit_style = f"""
            {ControlStyle.get_timeEdit_style()}  # 保留原有样式
            padding: 2px {2 * dpi_ratio}px;  # 极小内边距（适配DPI）
            border: none;  # 可选：移除边框进一步节省空间（根据需求调整）
        """
        self.lineedit_start.setStyleSheet(time_edit_style)
        ControlStyle.get_font_size(self.lineedit_start, int(10 * dpi_ratio))
        self.lineedit_start.setDisplayFormat("HH:mm:ss")  # 显示小时:分钟:秒

        start_layout.addWidget(self.label_start)
        start_layout.addWidget(self.combobox_start)
        start_layout.addWidget(self.lineedit_start)

        # end time
        end_layout = QHBoxLayout()
        end_layout.setContentsMargins(0, 0, 0, 0)
        dpi_ratio = self.devicePixelRatio()
        end_layout.setSpacing(int(4 * dpi_ratio))

        self.label_end = QLabel(parent)
        self.label_end.setObjectName("label_end")
        self.label_end.setMinimumSize(int(55 * dpi_ratio), int(32 * dpi_ratio))
        self.label_end.setFixedWidth(int(55 * dpi_ratio))
        self.label_end.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        ControlStyle.get_font_size(self.label_end, int(10 * dpi_ratio))

        self.combobox_end = QComboBox(parent)
        self.combobox_end.setObjectName("combobox_end")
        self.combobox_end.setMinimumSize(int(145 * dpi_ratio), int(32 * dpi_ratio))
        # self.combobox_end.setFixedWidth(int(130 * dpi_ratio))
        combo_style = f"""
            {ControlStyle.get_comboBox_word_style()}  # 保留原有样式
            padding: 2px {2 * dpi_ratio}px;  # 极小内边距（适配DPI，默认内边距大）
            border: 1px solid #ccc;  # 可选：精简边框，根据原有样式调整
            min-height: {int(32 * dpi_ratio)}px;  # 保障高度
        """
        self.combobox_end.setStyleSheet(combo_style)
        ControlStyle.get_font_size(self.combobox_end, int(10 * dpi_ratio))

        self.lineedit_end = QTimeEdit(QTime.currentTime())
        self.lineedit_end.setMinimumSize(int(90 * dpi_ratio), int(32 * dpi_ratio))
        # self.lineedit_end.setFixedWidth(95)
        time_edit_style = f"""
            {ControlStyle.get_timeEdit_style()}  # 保留原有样式
            padding: 2px {2 * dpi_ratio}px;  # 极小内边距（适配DPI）
            border: none;  # 可选：移除边框进一步节省空间（根据需求调整）
        """
        self.lineedit_end.setStyleSheet(time_edit_style)
        ControlStyle.get_font_size(self.lineedit_end, int(10 * dpi_ratio))
        self.lineedit_end.setDisplayFormat("HH:mm:ss")  # 显示小时:分钟:秒

        end_layout.addWidget(self.label_end)
        end_layout.addWidget(self.combobox_end)
        end_layout.addWidget(self.lineedit_end)

        time_selection_vlayout.addWidget(self.label_time_selection, alignment=Qt.AlignLeft)
        time_selection_vlayout.addLayout(start_layout)
        time_selection_vlayout.addLayout(end_layout)

        self.bottom_left_widget_vlayout.addLayout(time_selection_vlayout)

        # 添加分割线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Plain)
        separator2.setStyleSheet("background-color: #a9a9a9;")
        separator2.setFixedHeight(1)
        self.bottom_left_widget_vlayout.addWidget(separator2)

        # Epochs length label + comboBox
        epoch_length_layout = QHBoxLayout()
        epoch_length_layout.setContentsMargins(32, 24, 32, 24)
        epoch_length_layout.setSpacing(20)

        self.label_epoch_length = QLabel(parent)
        self.label_epoch_length.setObjectName("label_epoch_length")
        self.label_epoch_length.setMinimumSize(115, 32)
        self.label_epoch_length.setFixedWidth(180)
        self.label_epoch_length.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_epoch_length, 10)

        self.combobox_epoch_length = QComboBox(parent)
        self.combobox_epoch_length.setObjectName("combobox_epoch_length")
        self.combobox_epoch_length.setMinimumSize(60, 32)
        self.combobox_epoch_length.setFixedWidth(115)

        self.combobox_epoch_length.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_epoch_length, 10)

        epoch_length_layout.addWidget(self.label_epoch_length)
        epoch_length_layout.addWidget(self.combobox_epoch_length)
        epoch_length_layout.setAlignment(Qt.AlignCenter)
        self.bottom_left_widget_vlayout.addLayout(epoch_length_layout)

        # 添加分割线
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFrameShadow(QFrame.Plain)
        separator3.setStyleSheet("background-color: #a9a9a9;")
        separator3.setFixedHeight(1)
        self.bottom_left_widget_vlayout.addWidget(separator3)

        # 增加弹簧
        spacerItem = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bottom_left_widget_vlayout.addSpacerItem(spacerItem)

        inform_layout = QVBoxLayout()
        inform_layout.setContentsMargins(32, 24, 32, 40)
        inform_layout.setSpacing(0)

        self.information_label = QLabel(parent)
        self.information_label.setObjectName("information_label")
        self.information_label.setMinimumSize(0, 32*3)
        self.information_label.setWordWrap(True)
        self.information_label.setStyleSheet(ControlStyle.get_inform_label_style())
        inform_layout.addWidget(self.information_label)
        self.bottom_left_widget_vlayout.addLayout(inform_layout)

        self.information_label.hide()  # 初始隐藏信息标签

        # Events label pushbutton
        # events_layout = QHBoxLayout()
        # events_layout.setContentsMargins(32, 24, 32, 24)
        # events_layout.setSpacing(0)

        # self.label_events = QLabel(parent)
        # self.label_events.setObjectName("label_events")
        # self.label_events.setMinimumSize(75, 32)
        # self.label_events.hide()
        # self.label_events.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        # ControlStyle.get_font_size(self.label_events, 12)
        # #
        # self.pushButton_events = QPushButton(parent)
        # self.pushButton_events.setObjectName("pushButton_events")
        # self.pushButton_events.setMinimumSize(90, 32)
        # self.pushButton_events.setIcon(QIcon("./resource/picture/plus.png"))
        # self.pushButton_events.hide()
        # self.pushButton_events.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        # ControlStyle.get_font_size(self.pushButton_events, 10)

        # events_layout.addWidget(self.label_events, alignment=Qt.AlignLeft)
        # events_layout.addWidget(self.pushButton_events, alignment=Qt.AlignRight)
        # # self.bottom_left_widget_vlayout.addLayout(events_layout)

        # # 添加分割线
        # separator3 = QFrame()
        # separator3.setFrameShape(QFrame.HLine)
        # separator3.setFrameShadow(QFrame.Plain)
        # separator3.setStyleSheet("background-color: #a9a9a9;")
        # separator3.hide()
        # separator3.setFixedHeight(1)
        # # self.bottom_left_widget_vlayout.addWidget(separator3)

        # # 创建一个空白区域
        # spacerItem = QSpacerItem(314, 492, QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.bottom_left_widget_vlayout.addSpacerItem(spacerItem)

        self.retranslateUi()  # 设置文本

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.label_channel_selection.setText(_translate("BottomLeftWidget", "Channel Select："))
        self.label_eeg.setText(_translate("BottomLeftWidget", "EEG"))
        self.label_emg.setText(_translate("BottomLeftWidget", "EMG"))
        self.label_acc.setText(_translate("BottomLeftWidget", "ACC"))
        self.label_time_selection.setText(_translate("BottomLeftWidget", "Time："))
        self.label_start.setText(_translate("BottomLeftWidget", "Start："))
        self.label_end.setText(_translate("BottomLeftWidget", "End："))
        self.label_epoch_length.setText(_translate("BottomLeftWidget", "Epoch length (s)"))
        self.information_label.setText(_translate("BottomLeftWidget", "* After changing the parameters, you need to click <b>'Analyse'</b> again for it to take effect."))

    def connect_signals(self):
        self.combobox_eeg.currentIndexChanged.connect(self.update_information_label)
        self.combobox_emg.currentIndexChanged.connect(self.update_information_label)
        self.combobox_acc.currentIndexChanged.connect(self.update_information_label)
        self.combobox_start.currentIndexChanged.connect(self.update_information_label)
        self.combobox_end.currentIndexChanged.connect(self.update_information_label)
        self.lineedit_start.timeChanged.connect(self.update_information_label)
        self.lineedit_end.timeChanged.connect(self.update_information_label)

    def update_information_label(self):
        self.information_label.show()

class BottomRightWidget(QWidget):
    # EEG,EMG,癫痫分析页面底部右边窗口
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)

    def initUI(self, parent=None):
        # 这里是底部右边窗口的布局
        bottom_right_widget_vlayout = QVBoxLayout(self)
        bottom_right_widget_vlayout.setContentsMargins(0, 0, 0, 24)
        bottom_right_widget_vlayout.setSpacing(0)

        # 主要是绘画窗口
        # 先将初始化页面画出，当获取到点击事件之后，将其页面换成进度条，当进度条走完之后，将图形显示出来
        draw_pic_vlayout = QVBoxLayout()
        draw_pic_vlayout.setContentsMargins(0, 0, 32, 0)
        draw_pic_vlayout.setSpacing(0)

        # 创建一个首页页面
        self.icon_with_text_widget = IconWithTextWidget(
            icon_path="./resource/picture/Analyse.png",  # 图标路径
            text="请设置分析参数后点击“Analyse”开始分析"
        )
        self.icon_with_text_widget.setObjectName("icon_with_text_widget")
        self.icon_with_text_widget.setMinimumSize(1126, 692)

        # 创建进度条页面
        self.progressBar_widget = QWidget(parent)
        self.progressBar_widget.setMinimumSize(1126, 692)

        progressBar_vlayout = QVBoxLayout(self.progressBar_widget)
        progressBar_vlayout.setContentsMargins(434, 0, 434, 0)
        progressBar_vlayout.setAlignment(Qt.AlignCenter)
        progressBar_vlayout.setSpacing(0)

        progressBar_label_hlayout = QHBoxLayout()
        progressBar_label_hlayout.setContentsMargins(0, 0, 0, 0)
        progressBar_label_hlayout.setSpacing(0)

        self.label_progressBar = QLabel(parent)
        self.label_progressBar.setText("分析中")
        self.label_progressBar.setObjectName("label_progressBar")
        self.label_progressBar.setMinimumSize(50, 20)
        self.label_progressBar.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())

        self.label_progressBar_count = QLabel(parent)
        self.label_progressBar_count.setText("0%")
        self.label_progressBar_count.setObjectName("label_progressBar_count")
        self.label_progressBar_count.setMinimumSize(50, 20)
        self.label_progressBar_count.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        self.label_progressBar_count.setAlignment(Qt.AlignRight)

        progressBar_label_hlayout.addWidget(self.label_progressBar, alignment=Qt.AlignLeft)
        progressBar_label_hlayout.addWidget(self.label_progressBar_count, alignment=Qt.AlignRight)

        self.progressBar = QProgressBar(parent)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setMinimumSize(258, 16)
        self.progressBar.setTextVisible(False)  # 关闭进度条中间的文本显示
        self.progressBar.setStyleSheet(ControlStyle.get_progressBar_style())

        progressBar_vlayout.addLayout(progressBar_label_hlayout)
        progressBar_vlayout.addWidget(self.progressBar)

        # 缺少顶部窗口

        # 创建一个滚动区域
        self.scrollarea_canvas = QScrollArea(parent)
        self.scrollarea_canvas.setObjectName("scrollarea_canvas")
        self.scrollarea_canvas.setMinimumSize(1085, 545)
        self.scrollarea_canvas.setWidgetResizable(True)  # 关键：启用内容自适应

        self.widget_time_slider = TimeSliderWidget(parent)
        self.widget_time_slider.setObjectName("widget_time_slider")
        self.widget_time_slider.setMinimumSize(1126, 56)
        self.widget_time_slider.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.widget_time_slider.time_slider.setEnabled(False)

        draw_pic_vlayout.addWidget(self.icon_with_text_widget)
        draw_pic_vlayout.addWidget(self.progressBar_widget)
        draw_pic_vlayout.addWidget(self.scrollarea_canvas)
        draw_pic_vlayout.addWidget(self.widget_time_slider)

        # self.icon_with_text_widget.hide()
        self.progressBar_widget.hide()
        self.scrollarea_canvas.hide()
        self.widget_time_slider.hide()

        # 下面是一个水平布局的窗口
        bottom_right_button_hlayout = QHBoxLayout()
        bottom_right_button_hlayout.setContentsMargins(32, 24, 32, 0)
        bottom_right_button_hlayout.setSpacing(24)

        # 添加分割线
        separator_bottom_right = QFrame()
        separator_bottom_right.setFrameShape(QFrame.HLine)
        separator_bottom_right.setFrameShadow(QFrame.Plain)
        separator_bottom_right.setStyleSheet("background-color: #a9a9a9;")
        separator_bottom_right.setFixedHeight(1)

        # analyse
        self.pushButton_analyse = QPushButton(parent)
        self.pushButton_analyse.setObjectName("pushButton_analyse")
        self.pushButton_analyse.setMinimumSize(145, 32)
        self.pushButton_analyse.setStyleSheet(ControlStyle.get_pushButton_style())

        # 创建一个空白区域
        spacerItem = QSpacerItem(603, 32, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # save pic
        self.pushButton_save_pic = QPushButton(parent)
        self.pushButton_save_pic.setObjectName("pushButton_save_pic")
        self.pushButton_save_pic.setMinimumSize(145, 32)
        self.pushButton_save_pic.setStyleSheet(ControlStyle.get_check_changed_pushButton_style())

        # save data
        self.pushButton_save_data = QPushButton(parent)
        self.pushButton_save_data.setObjectName("pushButton_save_data")
        self.pushButton_save_data.setMinimumSize(145, 32)
        self.pushButton_save_data.setStyleSheet(ControlStyle.get_check_changed_pushButton_style())

        bottom_right_button_hlayout.addWidget(self.pushButton_analyse, alignment=Qt.AlignLeft)
        bottom_right_button_hlayout.addSpacerItem(spacerItem)
        bottom_right_button_hlayout.addWidget(self.pushButton_save_pic, alignment=Qt.AlignRight)
        bottom_right_button_hlayout.addWidget(self.pushButton_save_data, alignment=Qt.AlignRight)

        bottom_right_widget_vlayout.addLayout(draw_pic_vlayout)
        bottom_right_widget_vlayout.addWidget(separator_bottom_right)
        bottom_right_widget_vlayout.addLayout(bottom_right_button_hlayout)


class CollapsibleSidebar(QWidget):
    """可折叠的侧边栏组件"""

    def __init__(self, parent=None, title="Sidebar", initial_state=True):
        """
        初始化侧边栏

        参数:
            parent: 父窗口
            title: 侧边栏标题
            initial_state: 初始状态 (True=展开, False=折叠)
        """
        super().__init__(parent)

        # 设置侧边栏基本属性
        self.setObjectName("collapsibleSidebar")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 记录侧边栏状态
        self.is_expanded = initial_state
        self.original_width = 350  # 默认展开宽度，可根据需要调整
        self.collapsed_width = 35  # 折叠后宽度，仅显示按钮

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        # 创建折叠按钮
        self.toggle_button = QPushButton("<<")
        self.toggle_button.setObjectName("sidebarToggleButton")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 5px;
                font-weight: bold;
                
                border-radius: 4px;
                min-width: 20px;
                min-height: 20px;
            }
            QPushButton:hover {
                /* 鼠标悬停时的样式 */
                background-color: #E3EAF8;
            }
        """)
        self.toggle_button.setFixedSize(30,30)  # 固定按钮尺寸
        self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_sidebar)
        self.toggle_button.move(5, 5)

        # 创建内容区域
        self.content_widget = QWidget()
        self.content_widget.setObjectName("sidebarContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)

        # 将组件添加到主布局
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_widget)

        # 初始化侧边栏状态
        self.update_sidebar_state()

    def add_widget(self, widget):
        """向侧边栏添加控件"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """向侧边栏添加布局"""
        self.content_layout.addLayout(layout)

    def set_expanded_width(self, width):
        """设置侧边栏展开时的宽度"""
        self.original_width = width
        if self.is_expanded:
            self.setFixedWidth(self.original_width)

    def toggle_sidebar(self):
        """切换侧边栏展开/折叠状态"""
        self.is_expanded = not self.is_expanded
        self.update_sidebar_state()

    def update_sidebar_state(self):
        """更新侧边栏状态（展开/折叠）"""
        if self.is_expanded:
            # 展开侧边栏
            self.content_widget.show()
            self.setFixedWidth(self.original_width)
            self.toggle_button.setText("<<")
            self.toggle_button.move(5, 5)  # 展开时定位到左上角
        else:
            # 折叠侧边栏
            self.content_widget.hide()
            self.setFixedWidth(self.collapsed_width)
            self.toggle_button.setText(">>")
            self.toggle_button.move(5, 5)  # 折叠时定位到左上角



class LoadingOverlay(QWidget):
    """加载遮罩层"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加文本
        self.text_label = QLabel("加载中，请稍候...")
        self.text_label.setStyleSheet(ControlStyle.get_loading_label_style())
        self.text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.text_label)

        # 初始隐藏
        self.hide()
    
    def paintEvent(self, event):
        """自定义绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制半透明背景
        painter.fillRect(self.rect(), QColor(255, 255, 255, 200))  # 白色背景，透明度200

        super().paintEvent(event)

    def showLoading(self):
        """显示加载界面"""
            # 确保遮罩层覆盖整个父组件
        if self.parent():
            self.setGeometry(self.parent().rect())

        self.show()
        self.raise_()
        
    def hideLoading(self):
        """隐藏加载界面"""
        self.hide()

    def resizeEvent(self, event):
        """调整大小事件"""
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())


class FocusOutCorrectDoubleValidator(QValidator):
    """
    失去焦点时自动修正的浮点数验证器：
    - 输入过程中不实时修正，仅验证格式
    - 当输入框失去焦点（鼠标移出）时，自动修正超出范围的值
      - 小于最小值 → 修正为最小值
      - 大于最大值 → 修正为最大值
    - 保留指定小数位数，支持标准/科学计数法
    """
    def __init__(self, bottom: float = 0.0, top: float = 100.0, decimals: int = -1,
                 notation: int = 0, parent=None):
        super().__init__(parent)
        self._bottom = bottom  # 最小值
        self._top = top        # 最大值
        self._decimals = decimals  # 小数位数
        self._notation = notation  # 计数法（0=标准，1=科学）

    # ------------------------------
    # 基础属性访问与设置
    # ------------------------------
    def bottom(self) -> float:
        return self._bottom

    def setBottom(self, bottom: float):
        self._bottom = bottom
        self._update_inputs()  # 更新关联的输入框

    def top(self) -> float:
        return self._top

    def setTop(self, top: float):
        self._top = top
        self._update_inputs()  # 更新关联的输入框

    def decimals(self) -> int:
        return self._decimals

    def setDecimals(self, decimals: int):
        self._decimals = max(0, decimals)
        self._update_inputs()  # 更新关联的输入框

    def notation(self) -> int:
        return self._notation

    def setNotation(self, notation: int):
        if notation in (0, 1):
            self._notation = notation
            self._update_inputs()  # 更新关联的输入框

    def setRange(self, minimum: float, maximum: float, decimals: int = 2):
        self._bottom = minimum
        self._top = maximum
        self._decimals = max(0, decimals)
        self._update_inputs()  # 更新关联的输入框

    # ------------------------------
    # 核心逻辑：输入验证（不实时修正）
    # ------------------------------
    def validate(self, input_str: str, pos: int) -> tuple[QValidator.State, str, int]:
        """只验证格式是否合法，不实时修正数值"""
        if not input_str.strip():
            return (QValidator.Intermediate, input_str, pos)

        # 检查格式是否合法（允许中间状态，如未完成的输入）
        try:
            if self._notation == 1 and ('e' in input_str.lower()):
                # 科学计数法格式检查
                float(input_str)
                return (QValidator.Acceptable, input_str, pos)
            else:
                # 标准计数法格式检查（允许负数、小数点）
                filtered = ''.join([c for c in input_str if c in '0123456789.-'])
                if filtered and (filtered != '-' and filtered != '.'):
                    float(filtered)
                    return (QValidator.Acceptable, input_str, pos)
        except ValueError:
            pass

        # 格式不合法，但保留输入（允许用户继续编辑）
        return (QValidator.Intermediate, input_str, pos)

    # ------------------------------
    # 失去焦点时自动修正
    # ------------------------------
    def fixup(self, input_str: str) -> str:
        """修正逻辑：当输入框失去焦点时调用"""
        try:
            # 解析输入值
            if self._notation == 1 and ('e' in input_str.lower()):
                value = float(input_str)
            else:
                filtered = ''.join([c for c in input_str if c in '0123456789.-'])
                if not filtered or filtered in ('-', '.'):
                    return str(self._bottom)  # 空输入或无效符号 → 修正为最小值
                value = float(filtered)
        except (ValueError, TypeError):
            return str(self._bottom)  # 解析失败 → 修正为最小值

        # 范围修正
        if value < self._bottom:
            corrected_value = self._bottom
        elif value > self._top:
            corrected_value = self._top
        else:
            corrected_value = value

        # 格式化输出
        return self._format_value(corrected_value)

    def _format_value(self, value: float) -> str:
        """格式化修正后的值"""
        if self._decimals < 0:  # 用负数表示不限制小数位
            if self._notation == 0:
                return str(value)
            else:
                return f"{value:e}"
        if self._notation == 0:  # 标准计数法
            format_str = f"%.{self._decimals}f"
            formatted = format_str % value
            # 移除末尾无意义的0和小数点
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.')
            return formatted
        else:  # 科学计数法
            format_str = f"%.{self._decimals}e"
            return format_str % value

    def _update_inputs(self):
        """当验证器参数变化时，更新所有关联的输入框"""
        if hasattr(self, 'parent') and isinstance(self.parent(), QLineEdit):
            self.parent().clearFocus()
            self.parent().setFocus()

    # ------------------------------
    # 静态常量
    # ------------------------------
    StandardNotation = 0
    ScientificNotation = 1


# 扩展QLineEdit，实现失去焦点时自动修正
class AutoCorrectLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 失去焦点时触发修正
        self.focusOutEvent = self._on_focus_out

    def _on_focus_out(self, event):
        """失去焦点时执行修正"""
        validator = self.validator()
        if isinstance(validator, FocusOutCorrectDoubleValidator):
            # 获取当前输入并修正
            current_text = self.text()
            corrected_text = validator.fixup(current_text)
            self.setText(corrected_text)
        super().focusOutEvent(event)

class CustomFrequencyCheckboxWidget(FrequencyCheckboxWidget):
    """
        继承FrequencyCheckboxWidget，重写create_item_widget方法
        实现自定义的输入框验证逻辑（最大值必须大于最小值）
        """

    def __init__(self, freq_dict=None, label_text="Frequency Selection", parent=None,min_input=0.001,max_input=float('inf')):
        self.min_input = min_input
        self.max_input = max_input
        # 调用父类构造方法
        super().__init__(freq_dict=freq_dict, label_text=label_text, parent=parent)


    def create_item_widget(self, name, range_tuple):
        """创建带验证器的输入框，确保失去焦点时自动修正"""
        item_widget = QtWidgets.QWidget()
        item_layout = QtWidgets.QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 10)
        item_layout.setSpacing(int(self.devicePixelRatio() * 10))

        # 复选框
        checkbox = QtWidgets.QCheckBox(name)
        checkbox.setStyleSheet(ControlStyle.get_all_channel_checkBox_style())
        checkbox.stateChanged.connect(self.update_all_checkbox_state)
        ControlStyle.get_font_size(checkbox, 10)
        item_layout.addWidget(checkbox, alignment=QtCore.Qt.AlignLeft)

        # 间隔
        spacer = QtWidgets.QSpacerItem(5, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        item_layout.addItem(spacer)

        # 最小值输入框（带验证器）
        min_edit = AutoCorrectLineEdit(str(range_tuple[0]))  # 使用扩展的输入框
        min_edit.setFixedWidth(50)
        min_edit.setAlignment(QtCore.Qt.AlignCenter)
        min_edit.setStyleSheet(ControlStyle.get_lineEdit_style())

        # 配置验证器：最小0.001，上限..，小数位，，，
        min_validator = FocusOutCorrectDoubleValidator(
            bottom=self.min_input,
            top=float(range_tuple[1]),
            #decimals=3,
        )
        min_edit.setValidator(min_validator)
        min_edit.hide()
        item_layout.addWidget(min_edit, alignment=QtCore.Qt.AlignRight)

        # 分隔符
        dash_label = QtWidgets.QLabel("-")
        dash_label.setFixedWidth(10)
        dash_label.setStyleSheet("color: #808080; font-size: 14px;")
        dash_label.hide()
        item_layout.addWidget(dash_label, alignment=QtCore.Qt.AlignRight)

        # 最大值输入框（带验证器）
        max_edit = AutoCorrectLineEdit(str(range_tuple[1]))
        max_edit.setFixedWidth(50)
        max_edit.setAlignment(QtCore.Qt.AlignCenter)
        max_edit.setStyleSheet(ControlStyle.get_lineEdit_style())

        # 配置验证器：最大..，无上限，...位小数
        max_validator = FocusOutCorrectDoubleValidator(
            bottom=float(range_tuple[0]),  # 初始下限为当前最小值
            top=self.max_input,
            #decimals=3
        )
        max_edit.setValidator(max_validator)
        max_edit.hide()
        item_layout.addWidget(max_edit, alignment=QtCore.Qt.AlignRight)

        def update_max_bottom():
            try:
                current_min = float(min_edit.text())
                max_validator.setBottom(current_min)
            except ValueError:
                pass

        # 2. 当最大值变化时，更新最小值的上限（确保 min ≤ max）
        def update_min_top():
            try:
                current_max = float(max_edit.text())
                min_validator.setTop(current_max)
            except ValueError:
                # 若最大值格式错误，暂时不更新（失去焦点时会被修正为最小值）
                pass

        min_edit.textChanged.connect(update_max_bottom)
        max_edit.textChanged.connect(update_min_top)

        # 固定间隔
        fixed_spacer = QtWidgets.QWidget()
        fixed_spacer.setFixedWidth(40)
        item_layout.addWidget(fixed_spacer)

        # 连接复选框状态改变信号
        checkbox.stateChanged.connect(
            lambda state, e1=min_edit, e2=max_edit, d=dash_label: self.on_checkbox_toggle(state, e1, e2, d)
        )

        return {
            "widget": item_widget,
            "checkbox": checkbox,
            "min_edit": min_edit,
            "max_edit": max_edit,
            "dash": dash_label
        }


    def on_checkbox_toggle(self, state, min_edit, max_edit, dash_label):
        visible = state == QtCore.Qt.Checked
        min_edit.setVisible(visible)
        max_edit.setVisible(visible)
        dash_label.setVisible(visible)

    def toggle_all_checkboxes(self, state):
        for item in self.item_dict.values():
            item["checkbox"].setChecked(state)

    def update_all_checkbox_state(self):
        self.all_checkbox.blockSignals(True)

        enabled_checkboxes = self.channel_checkboxes
        if not enabled_checkboxes:
            self.all_checkbox.setCheckState(QtCore.Qt.Unchecked)
        else:
            checked_count = sum(1 for cb in enabled_checkboxes if cb.isChecked())
            total_count = len(enabled_checkboxes)
            self.all_checkbox.setCheckState(QtCore.Qt.Checked if checked_count == total_count else QtCore.Qt.Unchecked)

        self.all_checkbox.blockSignals(False)

    def get_selected_frequencies(self):
        result = {}
        for name, item in self.item_dict.items():
            if item["checkbox"].isChecked():
                try:
                    min_val = float(item["min_edit"].text())
                    max_val = float(item["max_edit"].text())
                    result[name] = (min_val, max_val)
                except ValueError:
                    continue
        return result
