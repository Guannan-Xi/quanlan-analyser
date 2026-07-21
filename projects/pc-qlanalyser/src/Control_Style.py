from PyQt5.QtGui import QFont, QTextBlockFormat
import re

class ControlStyle:
    @staticmethod
    def get_pushButton_style_gray():
        """设置灰色背景按钮样式"""
        return "QPushButton { background-color: #ECECEC; border: 1px solid #CCCCCC; border-radius: 4px; }"

    @staticmethod
    def get_pushButton_style_white():
        """设置白色背景按钮样式"""
        return "QPushButton { background-color: white; border: 1px solid #CCCCCC; border-radius: 4px; }"

    @staticmethod
    def get_checkbox_style():
        """设置复选框样式，可自定义选中、未选中状态外观"""
        return """
                QCheckBox {
                    color: #333333;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                }
                QCheckBox::indicator:checked {
                    image: url(:/icons/checked.png);  /* 若有选中状态图标可这样设置，也可用背景色 */
                    background-color: #007ACC;
                }
            """

    @staticmethod
    def get_widget_style():
        widget_style = """
            QWidget {
                background-color: #F6F9FF;
                border: none;
            }
        """
        return widget_style

    @staticmethod
    def get_label_word_style():
        label_word_style = """
            QLabel {
                font-family: Microsoft YaHei;
                font-size: 12pt;
                font-weight: 500;
                color: #000000;
                line-height: 19px;
                text-align: left;
                font-style: normal;
                text-transform: none;
            }
        """
        return label_word_style

    @staticmethod
    def get_label_wordSmall_style():
        label_wordSmall_style = """
            font-family: Microsoft YaHei;
            font-weight: 500;
            color: #000000;
            line-height: 16px;
            text-align: center;
            font-style: normal;
            text-transform: none;
        """
        return label_wordSmall_style

    @staticmethod
    def get_comboBox_word_style():
        comboBox_word_style = """
            QComboBox {
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 10pt;
                color: #31373D;
                line-height: 40px;
                text-align: left;
                font-style: normal;
                text-transform: none;
                background: #FFFFFF;
                border-radius: 4px 4px 4px 4px;
                border: 1px solid #D4D6D9;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding; /* 子控件原点位置 */
                subcontrol-position: top right; /* 子控件位置在右上角 */
                border: none;
            }
            QComboBox::down-arrow {
                image: url(./resource/picture/arrowhead.png);
                width: 16px;
                height: 16px;
                right: 10px;
            }
            QComboBox QAbstractItemView {
                font-size:10pt;
                background-color: white;
                selection-background-color: lightgray; /* 选中选项的背景色 */
                selection-color: black; /* 选中选项的文本颜色 */
            }
            QComboBox QAbstractItemView::item {
                font-size:10pt;
                background-color: white;
                color: black;
                padding-left: 10px;
            }
        """
        return comboBox_word_style

    @staticmethod
    def get_combobox_list_view():
        combobox_list_view = """
                    QListView::item {
                        font-size: 10pt;
                        border: none;
                        background-color: white;
                    }
                    QListView {
                        border: none;
                        outline: 0;
                        background-color: white;
                        font-family: Microsoft YaHei;
                        font-weight: 400;
                        font-size: 10pt;
                        color: #31373D;
                        line-height: 12px;
                        text-align: left;
                        font-style: normal;
                        text-transform: none;
                    }
                    QComboBox QAbstractItemView {
                        outline: 0;  /* 移除默认焦点边框 */
                        background-color: white;  /* 下拉列表背景 */
                        selection-background-color: #f0f0f0;  /* 选中项的背景颜色（例如浅灰色） */
                        selection-color: black;    /* 选中项的字体颜色（例如黑色） */
                    }
                    QComboBox QAbstractItemView::item:hover {  /* 鼠标悬停时的样式 */
                        background-color: #2A87DB;  /* 悬停背景颜色 */
                        color: #FFFFFF;               /* 悬停字体颜色 */
                    }
                """
        return combobox_list_view

    @staticmethod
    def get_lineEdit_style():
        lineEdit_style = """
            QLineEdit {
                font-family: Microsoft YaHei;
                font-size: 10pt;
                font-weight: 400;
                color: #000000;
                line-height: 14px;
                text-align: left;
                font-style: normal;
                text-transform: none;
                background: #FFFFFF;
                border-radius: 4px 4px 4px 4px;
                border: 1px solid #D4D6D9;
            }
        """
        return lineEdit_style

    @staticmethod
    def get_timeEdit_style():
        timeEdit_style = """
            QTimeEdit {
                font-family: Microsoft YaHei;
                font-size: 10pt;
                font-weight: 400;
                color: #000000;
                line-height: 14px;
                text-align: left;
                font-style: normal;
                text-transform: none;
                background: #FFFFFF;
                border-radius: 4px 4px 4px 4px;
                border: 1px solid #D4D6D9;
            }

            /* 隐藏上下箭头按钮 */
            QTimeEdit::up-button,
            QTimeEdit::down-button {
                width: 0px;
             border: none;
            }

        """
        return timeEdit_style

    @staticmethod
    def get_pushButton_style():
        pushButton_style = """
            QPushButton:enabled {
                font-family: Microsoft YaHei;
                font-size: 10pt;
                font-weight: 400;
                color: #FFFFFF;
                line-height: 14px;
                text-align: center;
                font-style: normal;
                text-transform: none;       
                background: #2A87DB;
                border-radius: 4px 4px 4px 4px;
            }

            QPushButton:hover {
                background: #1E6BB8; /* 鼠标悬停时颜色加深 */
            }

            QPushButton:pressed {
                background: #175C9E; /* 点击时颜色更深 */
            }

            QPushButton:disabled {
                font-family: Microsoft YaHei;
                font-size: 10pt;
                font-weight: 400;
                color: #FFFFFF;
                line-height: 14px;
                text-align: center;
                font-style: normal;
                text-transform: none;  
                background: rgba(42,135,219,0.5);
                border-radius: 4px 4px 4px 4px;
            }

            QPushButton {
                outline: none; /* 去除点击时的虚线边框 */
            }
        """
        return pushButton_style

    @staticmethod
    def get_scrollArea_style():
        scrollArea_style = """
            QScrollArea {
                border: none;
            }
        """
        return scrollArea_style

    @staticmethod
    def get_scrollAreaWidgetContents_style():
        scrollAreaWidgetContents_style = """
            QWidget {
                background: #FFFFFF;
                border-radius: 4px 4px 4px 4px;
            }
        """
        return scrollAreaWidgetContents_style

    @staticmethod
    def get_all_channel_checkBox_style():
        all_checkBox_style = """
            QCheckBox {
                font-family: Microsoft YaHei;
                font-size: 10pt;
                font-weight: 300;
                color: #000000;
                line-height: 14px;
                text-align: left;
                font-style: normal;
                text-transform: none;
                border-radius: 0px 0px 0px 0px;
            }
            QCheckBox:checked {
                font-weight: bold;
                color: #2A87DB;
            }
        """
        return all_checkBox_style

    @staticmethod
    def get_all_widget_style():
        all_widget_style = """
            QWidget {
                background: #E3EAF8;
                border-radius: 0px 0px 0px 0px;
            }
        """
        return all_widget_style

    @staticmethod
    def get_channel_widget_style():
        channel_widget_style = """
            QWidget {
                background: #FFFFFF;
                border-radius: 0px 0px 4px 4px;
            }
        """
        return channel_widget_style

    @staticmethod
    def get_time_label_style():
        time_label_style = """
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 10pt;
                color: #676666;
                line-height: 14px;
                text-align: left;
                font-style: normal;
                text-transform: none;
            }
        """
        return time_label_style

    @staticmethod
    def get_check_changed_pushButton_style():
        check_changed_pushButton_style = """
            QPushButton {
                border-radius: 4px 4px 4px 4px;
                border: 1px solid #2A87DB;
                font-family:Microsoft YaHei;
                font-weight:400;
                font-size: 10pt;
                color:#007AC3;
                line-height:16px;
                text-align:center;
                font-style:normal;
               text-transform:none;
            }
            QPushButton:hover {
                color:#FFFFFF;
                background-color:#007AC3;
            }
        """
        return check_changed_pushButton_style

    @staticmethod
    def get_textEdit_word_style():
        textEdit_word_style = """
            QTextEdit {
                font-weight: 300;
                font-size: 10pt;
                color: #000000;
                text-align: left;
                font-style: normal;
                text-transform: none;
                background: #FFFFFF;
                border-radius: 4px 4px 4px 4px;
                padding: 16px;  /* 内边距 */
                margin: 16px    /* 外边距 */
            }
            p {
                margin-top: 10px;            /* 段落顶部间距 */
                margin-bottom: 10px;         /* 段落底部间距 */
            }
        """
        return textEdit_word_style

    @staticmethod
    def get_menuBar_style():
        menuBar_style = """
            QMenu {
            background-color: white;
        }
        QMenu::item {
            font-family:Microsoft YaHei;
            font-weight:400;
            font-size:10pt;
            color:#000000;
            line-height:16px;
            text-align:left;
            font-style:normal;
            text-transform:none;
            padding: 4px 16px 4px 16px;
        }
        QMenu::item:selected {
            color: #FFFFFF;
            background: #2A87DB;
            border-radius: 4px 4px 4px 4px;
        }
        QMenu::item:disabled {
            color: gray;
        }
        QMenu::item:disabled:selected {
             color: #FFFFFF; /* 禁用项的文字颜色 */
             background-color: gray;
             border-radius: 4px 4px 4px 4px;
        }
        QMenuBar::item {
            background: #FFFFFF;
            border-radius: 0px 0px 0px 0px;
            padding: 6px 24px;
            margin: 0;
            font-family: PingFang SC;
            font-weight: 400;
            color: #000000;
            line-height: 16px;
            text-align: left;
            font-style: normal;
            text-transform: none;
        }
        QMenuBar::item:disabled {
            color: gray;
        }
        QMenuBar::item:selected {
           background-color: #E7F3FF
        }
    """
        return menuBar_style

    @staticmethod
    def get_menu_item_style():
        """兼容旧调用：复用统一菜单样式。"""
        return ControlStyle.get_menuBar_style()

    @staticmethod
    def get_font_size(control, font_size):
        # 设置字体大小
        font = QFont("Microsoft YaHei", font_size)  # 设置字体和大小
        control.setFont(font)

    @staticmethod
    def _textEdit_word_style(textEdit):
        # 設置為只讀
        textEdit.setReadOnly(True)
        # 设置字体大小
        font = QFont("Microsoft YaHei", 10)  # 设置字体和大小
        textEdit.setFont(font)
        # 设置行间距
        cursor = textEdit.textCursor()
        block_format = QTextBlockFormat()
        block_format.setLineHeight(150, QTextBlockFormat.ProportionalHeight)  # 2 倍行距
        cursor.mergeBlockFormat(block_format)

    @staticmethod
    def get_pushButton_style_white():
        pushButton_style = """
            QPushButton::enabled {
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 10pt;
                color: #2A87DB;  /* 字体颜色为蓝色 */
                line-height: 14px;
                text-align: center;
                font-style: normal;
                text-transform: none;       
                background: #FFFFFF;  /* 背景为白色 */
                border: 2px solid #2A87DB;  /* 边框为蓝色 */
                border-radius: 4px;  /* 圆角 */
            }
            QPushButton::disabled {
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 10pt;
                color: rgba(42, 135, 219, 0.5);  /* 字体颜色为半透明蓝色 */
                line-height: 14px;
                text-align: center;
                font-style: normal;
                text-transform: none;  
                background: #F0F0F0;  /* 背景为浅灰色 */
                border: 2px solid rgba(42, 135, 219, 0.5);  /* 边框为半透明蓝色 */
                border-radius: 4px;  /* 圆角 */
            }
            QPushButton::hover {
                background: #E6F2FF;  /* 鼠标悬停时背景为浅蓝色 */
            }
            QPushButton::pressed {
                background: #D9ECFF;  /* 按下时背景为更深的浅蓝色 */
            }
        """
        return pushButton_style

    @staticmethod
    def get_scrollbar_style():
        scrollbar_style = """
            QScrollArea {
                border: none;
                background: #FFFFFF;  /* 滚动区域背景颜色为白色 */
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;  /* 滚动条背景颜色为灰色 */
                width: 8px;           /* 滚动条宽度 */
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C0;  /* 滑块颜色为浅灰色 */
                min-height: 20px;     /* 滑块的最小高度 */
                border-radius: 4px;   /* 滑块圆角 */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: #F5F5F5;  /* 滑块未覆盖区域的背景颜色 */
            }
            QScrollBar:horizontal {  /* 错误1修复：冒号后无空格 */
                border: none;
                background: #F5F5F5;  /* 滚动条背景颜色为灰色 */
                height: 8px;          /* 错误2修复：横向用height设粗细 */
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #C0C0C0;  /* 滑块颜色为浅灰色 */
                min-width: 20px;      /* 错误2修复：横向用min-width设最小尺寸 */
                border-radius: 4px;   /* 滑块圆角 */
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;           /* 错误3修复：横向箭头设width=0隐藏 */
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: #F5F5F5;  /* 滑块未覆盖区域的背景颜色 */
            }
        """
        return scrollbar_style

    @staticmethod
    def get_data_style():
        data_style = """
            QDateEdit {
                border: 1px solid #CCCCCC;  /* 边框颜色设置为浅灰色 */
                border-radius: 6px;         /* 圆角边框 */
                padding: 6px;               /* 内边距 */
                background-color: #FFFFFF;  /* 背景颜色设置为白色 */
            }              
        """
        return data_style

    @staticmethod
    def get_time_style():
        time_style = """
            QTimeEdit {
                border: 1px solid #CCCCCC;  /* 边框颜色设置为浅灰色 */
                border-radius: 6px;         /* 圆角边框 */
                padding: 6px;               /* 内边距 */
                background-color: #FFFFFF;  /* 背景颜色设置为白色 */
            }
        """
        return time_style

    @staticmethod
    def get_nav_pushButton_style():
        nav_pushButton_style = """
            QPushButton {
                background: #FFFFFF;
                border-radius: 0px;
                border: 1px solid #C0C4CC;  /* 边框颜色加深 */
                font-family: Microsoft YaHei;
                font-weight: 400;
                color: #2478C7;  /* 文字颜色加深 */
                line-height: 14px;
                text-align: center;
                font-style: normal;
                text-transform: none;
            }

            QPushButton:hover {
                background: #EDF5FF;  /* 悬停背景色加深 */
                border: 1px solid #2478C7;  /* 悬停边框颜色加深 */
                color: #1A5C9E;  /* 悬停文字颜色加深 */
            }

            QPushButton:pressed {
                background: #DBE9FB;  /* 按下背景色加深 */
                border: 1px solid #154B85;  /* 按下边框颜色加深 */
                color: #154B85;  /* 按下文字颜色加深 */
            }

            QPushButton:disabled {
                background: #EFEFEF;  /* 禁用背景色加深 */
                border: 1px solid #D9D9D9;  /* 禁用边框颜色加深 */
                color: #A6A6A6;  /* 禁用文字颜色加深 */
            }

            QPushButton:focus {
                outline: none;
                border: 1px solid #2478C7;  /* 焦点边框颜色加深 */
            }
        """
        return nav_pushButton_style

    @staticmethod
    def get_draw_pic_widget_style():
        draw_pic_widget_style = """
            background: #FFFFFF;
            border-radius: 4px 4px 4px 4px;
        """
        return draw_pic_widget_style

    @staticmethod
    def get_box_shadow_widget_style():
        box_shadow_widget_style = """
            QWidget {
                background: #FFFFFF;
                border-radius: 0px 0px 0px 0px;
            }
        """
        return box_shadow_widget_style

    @staticmethod
    def get_progressBar_style():
        progressBar_style = """
            QProgressBar {
                background-color: #f0f0f0; /* 进度条背景色 */
                border-radius: 4px 4px 4px 4px;
            }
            QProgressBar::chunk {
                background-color: #2A87DB;
                border-radius: 4px 4px 4px 4px;
            }
        """
        return progressBar_style

    @staticmethod
    def get_color_pushButton_style(color: str) -> str:
        color_pushButton_style = f"""
            QPushButton {{
                background: #{color};
                border-radius: 4px 4px 4px 4px;
                font-family: Microsoft YaHei;
                font-weight: 400;
                color: #FFFFFF;
                line-height: 14px;
                text-align: center;
                font-style: normal;
                text-transform: none;
            }}
        """
        return color_pushButton_style

    @staticmethod
    def get_redo_set_pushButton_style():
        redo_set_pushButton_style = """
            border: none;
            font-family: Microsoft YaHei;
            font-weight: 400;
            color: #2A87DB;
            line-height: 14px;
            text-align: left;
            font-style: normal;
            text-transform: none;
        """
        return redo_set_pushButton_style

    @staticmethod
    def get_redo_undo_black_pushButton_style():
        redo_undo_black_pushButton_style = """
            QPushButton {
                border: none;
                font-family: Microsoft YaHei;
                font-weight: 400;
                color: #2A87DB;
                line-height: 14px;
                text-align: left;
                font-style: normal;
                text-transform: none;
            }
            QPushButton:disabled {
                color: grey; 
            }
        """
        return redo_undo_black_pushButton_style

    @staticmethod
    def get_wiget400_word_style(lineHeight: str) -> str:
        wiget400_word_style = f"""
            font-family: Microsoft YaHei;
            font-size: 10pt;
            font-weight: 400;
            color: #000000;
            line-height: {lineHeight}px;
            text-align: left;
            font-style: normal;
            text-transform: none;
        """
        return wiget400_word_style

    @staticmethod
    def get_light_Blue_widget_style():
        light_Blue_widget_style = """
            QWidget {
                background: #EEF2FB;
                border-radius: 0px 0px 0px 0px;
            }
        """
        return light_Blue_widget_style

    @staticmethod
    def get_time_slider_style():
        time_slider_style = """
            QSlider::groove:horizontal {
                height: 4px; /* 滑动槽的高度 */
                background: #d3d3d3; /* 滑动槽的背景颜色 */
                border-radius: 2px; /* 滑动槽的圆角 */
            }
            QSlider::handle:horizontal:hover {
            background: #1976D2; /* 鼠标悬停时滑块颜色变深 */
            border: 1px solid #1976D2;
        }

        QSlider::handle:horizontal:pressed {
            background: #0D47A1; /* 鼠标按压时滑块颜色更深 */
            border: 1px solid #0D47A1;
        }
            QSlider::handle:horizontal {
                width: 56px; /* 滑块的宽度 */
                height: 12px; /* 滑块的高度 */
                background: #2A87DB; /* 滑块的颜色 */
                border: 1px solid #5c5c5c; /* 滑块的边框 */
                border-radius: 6px; /* 滑块的圆角 */
                margin: -4px 0; /* 滑块的外边距，确保滑块居中 */
            }
            QSlider::sub-page:horizontal {
                background: #2A87DB; /* 已滑动部分的颜色 */
                border-radius: 2px; /* 已滑动部分的圆角 */
            }
            QSlider::add-page:horizontal {
                background: #d3d3d3; /* 未滑动部分的颜色 */
                border-radius: 2px; /* 未滑动部分的圆角 */
            }
        """
        return time_slider_style

    @staticmethod
    def get_time_slider_label_style():
        time_slider_label_style = """
            QLabel{
                width: 58px;
                height: 14px;
                font-family: Microsoft YaHei;
                font-weight: 300;
                font-size: 14px;
                color: #000000;
                line-height: 14px;
                text-align: right;
                font-style: normal;
                text-transform: none;
            }
        """
        return time_slider_label_style

    @staticmethod
    def get_toolbutton_style():
        toolbutton_style = """
            QToolButton {
                padding-right: 20px; 
            }
            QToolButton::menu-indicator {
                subcontrol-position: right center;  /* 箭头居中对齐 */
                subcontrol-origin: padding;
                right: 5px;  /* 调整箭头与右边框的距离 */
            }
        """
        return toolbutton_style

    @staticmethod
    def get_spinbox_style():
        spinbox_style = """
            QSpinBox {
                border: 2px solid #D4D6D9;
                border-radius: 5px;
                padding: 5px;
                background: white;
                min-width: 80px;
            }
            QSpinBox:hover {
                border-color: #4169E1;
            }
            QSpinBox:focus {
                border-color: #00BFFF;
                background: #f8f8f8;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                background: #F6F9FF;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #d0d0d0;
            }
            QSpinBox::up-arrow {
                image: url(./resource/picture/up_arrow2.png);          /* 上箭头图标 */
                width: 20px;
                height: 15px;
            }
            QSpinBox::down-arrow {
                image: url(./resource/picture/down_arrow2.png);        /* 下箭头图标 */
                width: 20px;
                height: 15px;
            }
        """
        return spinbox_style

    @staticmethod
    def get_doublespinbox_style():
        doublespinbox_style = """
            QDoubleSpinBox {
                border: 2px solid #D4D6D9;
                border-radius: 5px;
                padding: 5px;
                background: white;
                min-width: 80px;
            }
            QDoubleSpinBox:hover {
                border-color: #4169E1;
            }
            QDoubleSpinBox:focus {
                border-color: #00BFFF;
                background: #f8f8f8;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 20px;
                background: #F6F9FF;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background: #d0d0d0;
            }
            QDoubleSpinBox::up-arrow {
                image: url(./resource/picture/up_arrow2.png);          /* 上箭头图标 */
                width: 20px;
                height: 15px;
            }
            QDoubleSpinBox::down-arrow {
                image: url(./resource/picture/down_arrow2.png);        /* 下箭头图标 */
                width: 20px;
                height: 15px;
            }
        """
        return doublespinbox_style

    @staticmethod
    def get_slider_style():
        return """
        QSlider::groove:horizontal {
            border: none;
            height: 15px;
            background: #E3E3E3;  /* 滑轨背景色 */
            border-radius: 7px;   /* 左右两侧圆角，半径为高度的一半 */
        }

        QSlider::handle:horizontal {
            background: #FFFFFF;   /* 纯白色滑块 */
            border: 2px solid #1E90FF;  /* 蓝色边框 */
            width: 20px;           /* 宽度 */
            height: 20px;          /* 高度，与宽度相同确保正圆 */
            margin: -5px 0;        /* 垂直居中，计算：(20-15)/2 = 2.5，向上取整为3，再加2px边框 */
            border-radius: 10px;   /* 圆角半径为宽度/高度的一半，确保正圆 */
        }

        QSlider::handle:horizontal:hover {
            border: 2px solid #4169E1; /* 悬停时加深边框色 */
            background: #F8F8FF;   /* 轻微变亮的白色 */
        }

        QSlider::handle:horizontal:pressed {
            border: 2px solid #0F4C75; /* 按压时深蓝边框 */
            background: #EDF2F7;   /* 轻度灰白色 */
        }

        QSlider::sub-page:horizontal {
            background: #1E90FF;   /* 纯蓝色填充 */
            border-radius: 7px;    /* 与滑轨相同的圆角 */
            height: 15px;          /* 与滑轨相同高度 */
        }

        QSlider::add-page:horizontal {
            background: #E3E3E3;   /* 未填充区域背景色 */
            border-radius: 7px;    /* 与滑轨相同的圆角 */
            height: 15px;          /* 与滑轨相同高度 */
        }
        """

    @staticmethod
    def get_inform_label_style():
        inform_label_style = """
            QLabel {
                color: #2A87DB;              
                font-family: Microsoft YaHei;
                font-size: 8pt;
            }
        """
        return inform_label_style

    @staticmethod
    def get_loading_label_style():
        loading_label_style = """
            QLabel {
                color: #2A87DB;              
                font-family: Microsoft YaHei;
                font-size: 16pt;
                font-weight: 400;
                background-color: transparent;
            }
        """
        return loading_label_style

    # ========================= QEEG ============================
    @staticmethod
    def get_task_item_style():
        """任务项样式"""
        return """
                QFrame {
                    border: 1px solid #E5E9F2;
                    border-radius: 4px;
                    
                    background-color: #F8F9FA;
                    margin: 4px 0;
                    padding: 8px;
                }
                QLabel.task-label {
                    font-size: 12px;
                    color: #2E3440;
                }
                QPushButton.delete-btn {
                    background-color: #E53935;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 10px;
                }
                QPushButton.delete-btn:hover {
                    background-color: #D32F2F;
                }
            """

    @staticmethod
    def get_topWidget_Button_clicked():
        return """
         QPushButton {
                background: #FFFFFF;
                border-radius: 4px 4px 4px 4px;
                color: #2A87DB;
                border: none;
                font-size: 16px;
                font-weight: normal;
                font-family: Microsoft YaHei;
            }
        """

    @staticmethod
    def get_topWidget_Button():
        return """
             QPushButton {
                background-color:#FFF3F5F8;
                border-radius: 4px 4px 4px 4px;
                color: #979797;
                border: none;
                font-size: 16px;
                font-weight: normal;
                font-family: Microsoft YaHei;
            }
            """

    @staticmethod
    def get_addSubjwct_lineEdit():
        return """
            QLineEdit {
                width: 260px;
                height: 35px;
                border-radius: 2px 2px 2px 2px;
                border: 1px solid rgba(141,161,193,0.4);
                padding-left:5px;
            }
    """
    @staticmethod
    def get_addSubjwct_textEdit():
        return """
        QTextEdit {
            border-radius: 2px 2px 2px 2px;
            border: 1px solid rgba(141,161,193,0.4);
            padding-left:5px;
        }
    """
    @staticmethod
    def get_history_record_font_1():
        return """
            font-family: Microsoft YaHei;
            font-weight: 500;
            font-size: 14px;
            color: #979797;
            text-align: left;
            font-style: normal;
            text-transform: none;
        """

    @staticmethod
    def get_history_record_font_2():
        return """
            font-family: Microsoft YaHei;
            font-weight: 500;
            font-size: 20px;
            color: #31373D;
            text-align: left;
            font-style: normal;
            text-transform: none;
        """

    @staticmethod
    def get_QMessageBox_Style():
        return """
        /* 所有弹窗的基础样式 */
        QMessageBox {
            font-size: 16px;
            color: #2E3440;
        }
        /* 弹窗里的所有按钮统一样式：带边框、圆角、hover高亮，和你第一个弹窗一致 */
        QMessageBox QPushButton {
            border: 1px solid #DCDFE6;
            border-radius: 4px;
            padding: 6px 16px;
            min-width: 60px;
            background-color: white;
            color: #2E3440;
        }
        /* 按钮悬浮高亮效果 */
        QMessageBox QPushButton:hover {
            border-color: #2A87DB;
            color: #2A87DB;
        }
        /* 默认按钮（比如No）的高亮样式，和你的项目蓝色#2A87DB配色统一 */
        QMessageBox QPushButton:default {
            background-color: #2A87DB;
            color: white;
            border: none;
        }
    """

    @staticmethod
    def get_qeeg_font_500(color=None, size=None, align="left"):
        return """
            font-family: Microsoft YaHei;
            font-weight: 500;
            font-size: """ + size + """px;
            color: """ + color + """;
            text-align: """ + align + """;
            font-style: normal;
            text-transform: none;
        """

    @staticmethod
    def get_qeeg_font_400(color=None, size=None, align="left"):
        return """
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: """ + size + """px;
                color: """ + color + """;
                text-align: """ + align + """;
                font-style: normal;
                text-transform: none;
            """

    @staticmethod
    def get_background_border_widget(color=None, radius=None, padding="0"):
        return """
         QWidget {
                background-color:""" + color + """;
                border-radius: """ + radius + """px;
                padding: """ + padding + """px;
            }
        """

    @staticmethod
    def get_background_border(color=None, radius=None, padding="0"):
        return """
                background-color:""" + color + """;
                border-radius: """ + radius + """px;
                padding: """ + padding + """px;
            """

    @staticmethod
    def get_topwidget_style():
        return """
        QWidget#TopWidget {
                background-color: #FFFFFF;  /* 修改2：标准背景色属性，必改 */
                border-radius: 0px 0px 0px 0px;
                border: none; /* 可选，去除原生边框，纯白更干净 */
            }
        
        """

    @staticmethod
    def get_radio_style():
        return """
        /* 基础样式：矩形按钮+浅灰边框+白色背景 */
        QRadioButton {
            border: 1px solid #DCDCDC;  /* 未选中时边框颜色 */
            border-radius: 4px;         /* 按钮圆角 */
            padding: 7px 20px;         /* 按钮内边距（控制按钮大小） */
            background-color: #FFFFFF;  /* 按钮背景色 */
            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 16px;
            color: #979797;
            text-align: left;
            font-style: normal;
            text-transform: none;
        }

        /* 选中状态：蓝色边框+浅蓝背景+蓝色文字 */
        QRadioButton:checked {
            border: 1px solid #409EFF;  /* 选中时边框颜色（截图蓝色） */
            background-color: #E8F4FF;  /* 选中时背景色（截图浅蓝） */
            color: #409EFF;             /* 选中时文字颜色（截图蓝色） */
        }

        """

    @staticmethod
    def get_logoPreviewBox():
        return """
            #logoPreviewBox {
                background: #F6F9FF;
                border-radius: 8px;
                border: 1px dashed #D4D6D9;
                }
        """

    @staticmethod
    def get_is_selected():
        return """
            border: 2px solid #4C84FF; 
            border-radius: 8px; 
            background-color: #F5F9FF; 
            margin: 4px 0;
            padding: 8px;
        """

    @staticmethod
    def get_is_not_selected():
        return """
            border-radius: 8px;
            margin: 4px 0;
            padding: 8px;
        """

    @staticmethod
    def get_info_tags_style():
        return """
                background: #E3EAF8;
                border-radius: 4px 4px 4px 4px;
                padding: 2px 8px;
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 12px;
                color: #8DA1C1;
                text-align: center;
                font-style: normal;
                text-transform: none;
        """

    @staticmethod
    def get_new_task_btn_style():
        return """
            QPushButton {   background: #216DDE;
                            border-radius: 8px 8px 8px 8px; 
                            padding: 4px 16px; 
                            font-family: Microsoft YaHei;
                            font-weight: 400;
                            font-size: 14px;
                            color: #FFFFFF;
                            text-align: center;
                            font-style: normal;
                            text-transform: none;
                          }
            QPushButton:hover {background: #3B75E0;}
        """

    @staticmethod
    def get_save_template_btn_style():
        return """
                width: 140px;
                height: 20px;
                background: #FFFFFF;
                border-radius: 8px 8px 8px 8px;
                border: 1px solid #D4D6D9;
                padding: 4px 8px 4px 8px; 
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 14px;
                color: #7C7C7C;
                text-align: center;
                font-style: normal;
                text-transform: none;
        """

    @staticmethod
    def get_add_btn_style():
        return """
            width: 201px;
            height: 53px;
            background: #216DDE;
            border-radius: 8px 8px 8px 8px;
            font-family: Microsoft YaHei;
            font-weight: 500;
            font-size: 18px;
            color: #FFFFFF;
            text-align: medium;
            font-style: normal;
            text-transform: none;
        """

    @staticmethod
    def get_search_edit_style():
        return """
        QLineEdit {
            height: 59px;
            background: #F8F9FB;
            border-radius: 8px;
            /* 设置左侧背景图标 */
            background-image: url(./resource/picture/search.png);
            background-repeat: no-repeat;
            /* 修正：图标距离左侧10px，垂直居中 */
            background-position: left center;
            padding: 6px 10px 6px 35px; /* 统一padding写法 */
            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 18px;
            color: #979797;
            text-align: left;
            }
        """

    @staticmethod
    def get_table_header_style():
        return """
            QHeaderView{
                background-color: #F5F7FA;
                border: none;
                border-radius: 8px 8px 8px 8px;
            }
            QHeaderView::section {
                background-color: transparent; /* 继承表头的背景，避免覆盖圆角 */
                border: none;                  /* 去掉列标题之间的分割线 */
                font-family: Microsoft YaHei;
                font-weight: bold;
                font-size: 16px;
                color: #979797;
                text-align: center;
                font-style: normal;
                text-transform: none;
            }
            QHeaderView::section:hover {
                background-color: #e0e0e0;
            }
            
            QHeaderView::section:pressed {
                background-color: #d0d0d0;
            }
            
        """

    @staticmethod
    def get_table_item_style():
        return """
            QTableWidget {
                border: none;
                background-color: #FFFFFF;
                gridline-color: transparent; /* 核心：表格内容区 所有横竖分割线 透明=完全隐藏 */
            }
            QTableWidget::item {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 16px;
                color: #31373D;
                text-align: center;
                font-style: normal;
                text-transform: none;
                border: none;      /* 单元格无边框 */
            }
            QTableWidget::item:selected {
                background-color: #E8F4FF;
                color: #303133;
                border: none;
            }
            QTableWidget QWidget#Widget {
                background-color: transparent;
            }
            
            QTableWidget:item:selected ~ QWidget#Widget {
                background-color: #E8F4FF;
            }
            QTableWidget QWidget#actionWidget {
                background-color: transparent;
            }
            
            QTableWidget:item:selected ~ QWidget#actionWidget {
                background-color:  #E8F4FF;
            }
        """

    @staticmethod
    def get_item_widget_style():
        return """
                #item_widget {
                    background: #FFFFFF;
                    border-radius: 8px 8px 8px 8px;
                    border: 1px solid #D4D6D9;
                    padding: 12px;
                }
                QWidget{
                  background: #FFFFFF;
                }
            """

    @staticmethod
    def get_load_btn_style():
        return """
                QPushButton {
                    background: #2A87DB;
                    border-radius: 8px 8px 8px 8px;
                    font-family: Microsoft YaHei;
                    font-weight: 500;
                    font-size: 16px;
                    color: #FFFFFF;
                    text-align: medium;
                    font-style: normal;
                    text-transform: none;
                    border:none;
                }
                QPushButton:hover {
                    background-color: #337ECC;
                }
            """

    @staticmethod
    def get_card_widget_style():
        return """
            #card_widget {
                background: #FFFFFF;
                border-radius: 8px 8px 8px 8px;
                border: 1px solid #D4D6D9;
                padding: 12px;
            }
        """

    @staticmethod
    def get_view_btn_style():
        return """
            QPushButton {
                background: #2A87DB;
                border-radius: 8px 8px 8px 8px;
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 16px;
                color: #FFFFFF;
                text-align: medium;
                font-style: normal;
                text-transform: none;
            }
            QPushButton:hover {
                background-color: #337ECC;
            }
        """

    @staticmethod
    def get_analysis_btn_style():
        return """
            height:36px;
            background: #2A87DB;
            border-radius: 8px 8px 8px 8px;
            font-family: Microsoft YaHei;
            font-weight: 500;
            font-size: 16px;
            color: #FFFFFF;
            font-style: normal;
            text-transform: none;
            """

    @staticmethod
    def get_QComboBox_style():
        return """
                        QComboBox {
                            background-color: rgba(255,255,255,0.1);
                            color: #FFFFFF;
                            border: 1px solid #2a4a6c;
                            border-radius: 4px;
                            padding: 0px 8px;
                            font-weight: 400;
                            font-size: 12px;
                            font-family: Microsoft YaHei;
                            font-style: normal;
                            text-transform: none;
                        }
                        QComboBox:hover {
                            background-color: #2a4a6c;
                            border: 1px solid #3a5a7c;
                        }
                        QComboBox:focus {
                            background-color: #1a3a5c;
                            border: 1px solid #4A90E2;
                        }
                        QComboBox::drop-down {
                            border: none;
                            background: transparent;
                            width: 16px;
                        }
                        QComboBox::down-arrow {
                            image: url(./resource/picture/drop.png);
                            width: 16px;
                            height: 16px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: #1a3a5c;
                            color: white;
                            selection-background-color: #2a4a6c;
                            border: 1px solid #2a4a6c;
                            padding: 4px;
                        }
                        QComboBox QAbstractItemView::item {
                            padding: 4px 8px;
                        }
                        QComboBox QAbstractItemView::item:hover {
                            background-color: #2a4a6c;
                        }
                    """

    @staticmethod
    def get_btn_cancel_style():
        return """
                    QPushButton {
                        width: 161px;
                        height: 40px;
                        border: 1px solid #D4D6D9;
                        border-radius: 8px;
                        padding: 4px 24px;
                        background-color: white;
                        font-family: Microsoft YaHei;
                        font-weight: 400;
                        font-size: 16px;
                        color: #31373D;
                        text-align: center;
                        font-style: normal;
                        text-transform: none;
                    }

                """

    @staticmethod
    def get_btn_save_style():
        return """
                    QPushButton {
                        width: 161px;
                        height: 40px;
                        background-color: #2A87DB;
                        border: none;
                        border-radius: 8px;
                        padding: 4px 24px;
                        font-family: Microsoft YaHei;
                        font-weight: 400;
                        font-size: 16px;
                        color: #FFFFFF;
                        text-align: center;
                        font-style: normal;
                        text-transform: none;
                    }
                
                """

    @staticmethod
    def get_method_title_edit_style():
        return """
        QLineEdit{
                width: 338px;
                height: 48px;
                border-radius: 8px 8px 8px 8px;
                border: 1px solid #2A87DB;
                padding-left:10px;
        }
        """

    @staticmethod
    def get_CSS():
        return """
        <style>
            html { 
                font-family: 'Microsoft YaHei', sans-serif; 
                padding: 0; 
                margin: 0; 
                color: #333;
                background: #FFFFFF; 
                overflow-x: hidden;  /* 隐藏横向滚动 */
                overflow-y: auto;  /* 允许纵向滚动 */
                height: auto;  /* 自动高度，允许内容超出 */
                min-height: 100vh;  /* 至少占满视口 */
            }
            body { 
                font-family: 'Microsoft YaHei', sans-serif; 
                padding: 0; 
                display: block; /* 避免 flex 导致垂直方向的挤压 */
                margin: 0; 
                color: #333;
                background: #FFFFFF; 
                overflow-x: hidden;  /* 隐藏横向滚动 */
                overflow-y: auto;  /* 允许纵向滚动 */
                height: auto;  /* 自动高度，允许内容超出 */
                min-height: 100vh;  /* 至少占满视口 */
                position: relative;  /* 相对定位，确保子元素正常定位 */
                display: block; /* 避免 flex 导致垂直方向的挤压 */
            }
            .header { border-bottom: 2px solid #4A90E2; padding-bottom: 10px; margin-bottom: 10px; }
            .section { margin-bottom: 10px; page-break-inside: avoid; }
            .page-section { margin-bottom: 10px; }  /* 页面之间添加间距，防止重叠，允许滚动 */

            /* ==========================================================
             * 预览按“纸张版心”显示（屏幕上像 PDF 预览，不铺满窗口）
             * 目标：预览版式尽量与打印(PDF)一致
             * ========================================================== */
            @media screen {
                html, body {
                    background: #F2F4F7 !important; /* 类 PDF 预览器灰底 */
                }
                body {
                    padding: 16px 0 !important; /* 上下留白，便于滚动 */
                }

                /* 把每个分析板块当作一张 A4 纸展示（居中） */
                .page-section {
                    width: 210mm !important;
                    min-height: 297mm !important;
                    height: 297mm !important; /* 预览严格按一页高度显示 */
                    margin: 16px auto !important;
                    background: #FFFFFF !important;
                    border-radius: 4px !important;
                    box-shadow: 0 8px 28px rgba(16, 24, 40, 0.18) !important;
                    overflow: hidden !important; /* 避免阴影/圆角下的溢出 */
                    padding: 0 15px !important; /* 预览：左右留白 15px，避免贴边 */
                    position: relative !important; /* 供页脚绝对定位到页底 */
                    box-sizing: border-box !important;
                }

                /* 让页脚在预览时也固定在页面底部 */
                .page-footer {
                    position: absolute !important;
                    left: 0 !important;
                    right: 0 !important;
                    bottom: 0 !important;
                    margin: 0 !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                    z-index: 10 !important;
                    background: #FFFFFF !important; /* 防止灰底透出 */
                }

                /* 内容区给页脚预留空间，避免遮挡（页脚约 40~60px） */
                .section-content {
                    padding-bottom: 70px !important;
                    box-sizing: border-box !important;
                }
                .qeeg-mapping-section .section-content {
                    padding-bottom: 40px !important;
                }
                .power-mapping-page .section-content {
                    padding-bottom: 30px !important;
                    overflow: hidden !important;
                }
            }
            .metric-row { display: flex; gap: 20px; margin-bottom: 20px; }
            .metric-card { background: #F0F7FF; border: 1px solid #D0E7FF; padding: 15px; border-radius: 8px; flex: 1; text-align: center; }
            .topo-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
            .topo-item { text-align: center; border: 1px solid #EEE; padding: 5px; border-radius: 5px; }
            .topo-item img { width: 100%; }
            /* 功率矩阵：默认（单矩阵/非并排） */
            .power-matrix-section { 
                flex: 1; 
                min-width: 48%;
                background: #FFFFFF;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
                padding: 20px;
                box-sizing: border-box;
                position: relative;
            }
            /* 功率矩阵标题栏 */
            .power-matrix-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            .power-matrix-title {
                font-size: 14px;
                font-weight: 700;
                color: #000000;
                margin: 0;
            }
            .power-matrix-title-two-line {
                display: flex;
                flex-direction: column;
                line-height: 1.4;
            }
            .power-matrix-title-two-line .power-matrix-title-main {
                font-weight: 700;
                color: #000000;
            }
            /* 避免绝对功率(μV²)中的上标影响标题行高，导致上下粉色分隔线略微错位 */
            .power-matrix-title-two-line .power-matrix-title-main sup {
                font-size: 0.7em;
                vertical-align: text-top;
                line-height: 1;
            }
            .power-matrix-title-two-line .power-matrix-title-en {
                font-size: 12px;
                font-weight: 500;
                color: #999999;
            }
            .power-matrix-unit {
                font-size: 12px;
                color: #999999;
            }
            .power-matrix-divider {
                height: 2px;
                background: linear-gradient(90deg, #FFB6C1 0%, #FFC0CB 100%);
                margin-bottom: 15px;
                border-radius: 1px;
            }

            /* 功率矩阵并排页：只让矩阵容器flex，避免整页.page-section变flex */
            .power-matrices-container {
                display: flex;
                gap: 4px;
                flex-wrap: wrap;
                align-items: flex-start;
                justify-content: space-between;
                width: 100%;
                box-sizing: border-box;
                margin-bottom: 4px;
            }
            .power-matrices-container .power-matrix-section {
                flex: 1 1 50%;
                min-width: 0; /* 允许收缩，避免被挤出后换行/溢出 */
                padding: 8px;
                padding-bottom: 32px;
                border-radius: 8px;
            }
            .module-colorbar-wrap {
                position: absolute;
                right: 8px;
                bottom: -6px;
                z-index: 2;
                pointer-events: none;
            }
            .module-colorbar-legend {
                display: flex;
                align-items: center;
                gap: 3px;
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                padding: 1px 5px;
                line-height: 1;
            }
            .module-colorbar-legend .cb-tick {
                font-size: 7px;
                color: #4B5563;
                min-width: 9px;
                text-align: center;
            }
            .module-colorbar-legend .cb-bar {
                display: inline-block;
                width: 46px;
                height: 6px;
                border-radius: 999px;
                background: linear-gradient(90deg, #2166ac 0%, #f7f7f7 50%, #b2182b 100%);
                border: 1px solid #D1D5DB;
            }
            .module-colorbar-legend .cb-unit {
                font-size: 7px;
                color: #374151;
                margin-left: 2px;
            }
            .power-matrices-container .power-matrix-section.disable {
                box-shadow: none;
            }
            /* 并排时更紧凑，避免A4固定高度下被裁剪 */
            .power-matrices-container .power-matrix-header {
                margin-bottom: 4px;
            }
            .power-matrices-container .power-matrix-title {
                font-size: 12px;
            }
            .power-matrices-container .power-matrix-title-two-line .power-matrix-title-en {
                font-size: 10px;
            }
            .power-matrices-container .power-matrix-unit {
                font-size: 10px;
            }
            .power-matrices-container .power-matrix-divider {
                margin-bottom: 6px;
            }
            .power-matrices-container .topo-matrix-grid {
                gap: 4px;
                margin-bottom: 0;
            }
            .power-matrices-container .topo-matrix-grid.topo-matrix-grid-4x4 {
                grid-template-columns: repeat(4, 1fr);
                grid-template-rows: repeat(4, 1fr);
            }
            .power-matrices-container .topo-matrix-item {
                padding: 1px;
                border: none;
                background: transparent;
            }
            .power-matrices-container .topo-matrix-item img {
                width: 84%;
                max-width: 84%;
                margin: 0 auto 1px auto;
            }
            .power-matrices-container .topo-label {
                font-size: 6px;
                line-height: 1.2;
            }
            .power-matrices-container .freq-label {
                font-size: 10px;
                margin-bottom: 0;
                color: #666666;
            }
            .power-matrices-container .max-value {
                display: none;  /* 隐藏最大值 */
            }
            /* Full-Band Power Distribution (power mapping) 页面：强制缩小整个2x2布局，确保不超出页脚 */
            .power-mapping-page .section-content {
                padding-top: 5px !important;
                padding-bottom: 10px !important;
                overflow: hidden !important;
            }
            .power-mapping-page .analysis-description-box {
                padding: 8px 20px !important;
                margin-bottom: 0px !important;
            }
            .power-mapping-page .task-name-title {
                font-size: 15pt !important;
                margin-bottom: 2px !important;
            }
            .power-mapping-page .analysis-description-text {
                font-size: 11px !important;
                line-height: 1.3 !important;
                margin-top: 2px !important;
            }
            .power-mapping-page .analysis-method-label {
                margin-bottom: 2px !important;
                font-size: 12px !important;
            }
            .power-mapping-page .power-matrices-container {
                transform: scale(1.0);
                transform-origin: top center;
                margin-bottom: -30px !important;
            }
            .power-mapping-page .power-matrices-container .power-matrix-section {
                padding: 4px 6px !important;
                padding-bottom: 28px !important;  /* 为模块色条预留高度，避免压住图片标签 */
                box-shadow: none !important;
            }
            .power-mapping-page .power-matrices-container .power-matrix-header {
                margin-bottom: 2px !important;
            }
            .power-mapping-page .power-matrices-container .power-matrix-title {
                font-size: 11px !important;
            }
            .power-mapping-page .power-matrices-container .power-matrix-title-two-line .power-matrix-title-en {
                font-size: 9px !important;
            }
            .power-mapping-page .power-matrices-container .power-matrix-divider {
                margin-bottom: 3px !important;
            }
            .power-mapping-page .power-matrices-container .topo-matrix-grid {
                gap: 2px !important;
            }
            .power-mapping-page .power-matrices-container .topo-matrix-item img {
                width: 78% !important;
                max-width: 78% !important;
            }
            /* 占位区域样式（当某个矩阵无数据时显示） */
            .matrix-placeholder {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 200px;
                background: #f8f9fa;
                border: 2px dashed #ddd;
                border-radius: 8px;
                color: #999;
                font-size: 11pt;
            }
            .matrix-placeholder p {
                margin: 0;
            }
            .topo-matrix-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 15px; }
            .topo-matrix-item { 
                text-align: center; 
                border: none;
                padding: 2px;
                border-radius: 4px; 
                background: transparent;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                align-items: center;
                min-height: 0;  /* 允许收缩 */
            }
            .topo-matrix-item img { 
                width: 100%; 
                height: auto; 
                display: block; 
                margin-bottom: 2px;  /* 减少底部margin：从4px改为2px */
                max-width: 100%;
                flex-shrink: 1;
            }
            .topo-label { 
                font-size: 14pt; 
                color: #555;
                margin: 0;  /* 移除默认margin */
                padding: 0;  /* 移除默认padding */
                line-height: 1.2;  /* 减小行高 */
            }
            .freq-label { 
                font-weight: bold; 
                margin-bottom: 1px;  /* 减少底部margin：从2px改为1px */
                font-size: 9pt;
                line-height: 1.2;  /* 减小行高 */
            }
            .max-value { 
                font-size: 7pt; 
                color: #777;
                margin: 0;  /* 移除默认margin */
                line-height: 1.2;  /* 减小行高 */
            }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #DDD; padding: 10px; text-align: left; }
            th { background: #F5F5F5; }
            
             /* PSD 地形图样式 */
            .psd-topography-section { 
                width: 100%; 
                background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                /* 减少上下留白，使卡片区域更紧凑 */
                padding: 10px 10px;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
            .topography-container { 
                position: relative; 
                width: 100%; 
                /* 留白减半后多出的横向空间：容器加宽，卡片与图片横向拉伸 */
                max-width: 732px;
                /* 高度大于宽度，纵向填充更充分；仍低于可用高度（约812px），不溢出页脚 */
                height: 0;
                padding-bottom: 760px;
                /* 顶部 margin 设为负值，将图整体上移，减少上方空白 */
                margin: -10px auto 2px;
                background-size: contain;
                background-position: center;
                background-repeat: no-repeat;
                border: none;
            }
            /* PSD 页面：容器改为正方形，减少上下留白 */
            .psd-topography-section .topography-container {
                padding-bottom: 732px !important;  /* 与 max-width 一致，容器为正方形 */
                margin: -15px auto 0px !important;
            }
            .topography-bg { 
                position: absolute; 
                width: 100%; 
                height: 100%; 
                top: 0; 
                left: 0;
                pointer-events: none;  /* 允许点击穿透 */
                opacity: 0.4;  /* 降低背景线透明度，更柔和 */
            }
            .channels-wrapper {
                position: absolute;
                width: 100%;
                height: 100%;
                top: 0;
                left: 0;
                /* 去掉圆形裁剪：移除 border-radius 和 overflow: hidden，保留内容和布局 */
            }

            .channel-panel { 
                position: absolute; 
                /* 卡片变窄 3%，避免拉伸过多 */
                width: 21.3%; 
                min-width: 0; 
                max-width: none; 
                min-height: 80px;
                height: auto; 
                display: flex !important;
                flex-direction: column !important;
                background: linear-gradient(135deg, #ffffff 0%, #fafbfc 100%);
                border: 1.5px solid #e0e6ed; 
                border-radius: 6px;
                padding: 4px 0px 0px 0px !important;
                box-shadow: 0 2px 6px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08);
                transform: translate(-50%, -50%);
                z-index: 10;
                box-sizing: border-box;
                pointer-events: auto;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                /* 新增：让内部元素可以绝对定位参考 */
                overflow: hidden;
            }

            .channel-panel:hover {
                transform: translate(-50%, -50%) scale(1.03);  /* 悬停时稍微放大，避免过度 */
                box-shadow: 0 4px 12px rgba(0,0,0,0.18), 0 2px 4px rgba(0,0,0,0.12);
                z-index: 20;  /* 悬停时提高层级 */
            }
            .channel-header { 
                font-weight: bold; 
                font-size: 6pt; 
                padding: 2px 2px; /* 微调内边距，避免贴边 */
                color: #ffffff; /* 深色文字保证辨识度 */
                background: #216DDE; /* 半透明白底，重叠时不遮挡波形图细节 */
                border-radius: 3px; /* 轻微圆角，适配UI风格 */
                /* 绝对定位核心属性 */
                position: absolute; 
                top: 0; /* 与卡片上内边距一致，对齐卡片左上角 */
                left: 0; /* 与卡片左内边距一致，对齐卡片左上角 */
                z-index: 20; /* 提高层级，保证标题在波形图/分隔线上方，不被遮挡 */
                /* 清除原有冲突样式 */
                text-align: unset; /* 取消居中 */
                border-bottom: none; /* 取消原有底边框 */
                margin-bottom: 0; /* 取消原有底部间距 */
            }
            /* 仅在 PSD 页面中隐藏左上角蓝色标签（通道名），避免遮挡图像内容 */
            .psd-topography-section .channel-header {
                display: none;
            }
            /* PSD 页面：卡片纵向拉伸为正方形，减少上下留白 */
            .psd-topography-section .channel-panel {
                aspect-ratio: 1 / 1 !important;
                height: auto !important;
                min-height: 0 !important;
            }
            /*  核心：波形图与文字垂直布局 */
            .channel-content { 
                flex: 1 !important;                  /* 关键：撑满卡片剩余高度 */
                display: flex !important;
                flex-direction: column !important;
                min-height: 0 !important;           /* 允许 flex 子项收缩 */
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            /*  波形图区域放大 */
            .bar-chart { 
                width: 100%;  /* 增加宽度 */
                height:80%; /* 波形图高度放大 */
                display: flex; 
                align-items: center;
                flex-shrink: 0;  /* 防止柱状图被压缩 */
                position: relative;
                margin: 0 !important;
                padding: 0 !important;
 
            }
            /* 修改容器类名和样式 */
            .line-chart-container {
                flex-shrink: 0 !important;
                height: 70px !important;
                width: 100% !important;
                margin: 0 0 4px 0 !important;
                padding: 0 !important;
                background: #f8f9fa;
                border-radius: 4px;
            }
            
            .line-chart-svg {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 1;
                pointer-events: none;
            }
            
            /* 折线样式 */
            .line-chart-path {
                /* SVG内联样式已定义，这里可以添加动画效果 */
                transition: stroke 0.3s ease;
            }
            
            /* 数据点样式 */
            .line-chart-point {
                transition: fill 0.3s ease, stroke 0.3s ease;
            }
            
            /* 网格线样式 */
            .line-grid {
                opacity: 0.6;
            }
            
            /* X轴基线样式 */
            .line-axis {
                opacity: 0.8;
            }

            
            .bar-container {
                width: 100%;
                max-height: 60px;  /* 最大高度不超过卡片内容区域，与通道图保持一致 */
                height: 60px;  /* 固定高度，与通道图最大高度一致 */
                display: flex;
                gap: 3px;  /* 增加柱状图间距 */
                align-items: flex-end;
                justify-content: center;
                position: relative;
            }
            /* PSD 通道图像模式（算法直接返回图片时使用）——占用与 bar-container 相同的区域，保持卡片结构不变 */
            .psd-channel-spark {
                width: 100%;
                /* 在不超出通道卡片和整体拓扑容器的前提下，尽量放大PSD图片；横向填满卡片 */
                max-height: 130px;
                height: auto;
                object-fit: fill;  /* 横向拉伸填满卡片宽度，与加宽后的卡片一致 */
                display: block;
                background: rgba(255,255,255,0.55);
                border-radius: 4px;
                
                box-sizing: border-box;
            }
            /* PSD 页面：图片区域纵向拉伸为正方形，与卡片一致 */
            .psd-topography-section .bar-chart {
                flex: 1 !important;
                min-height: 0 !important;
                aspect-ratio: 1 / 1 !important;
                height: auto !important;
                align-items: stretch !important;
            }
            .psd-topography-section .psd-channel-spark {
                width: 100% !important;
                height: 100% !important;
                max-height: none !important;
                object-fit: fill !important;  /* 纵向拉伸填满正方形区域 */
            }
            .line-chart-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 1;
                pointer-events: none;
            }
            /* 柱状图宽度放大 */
            .bar { 
                width: 6px;  /* 增加柱状图宽度 */
                min-height: 2px;
                border-radius: 2px 2px 0 0;
                position: relative;
                z-index: 0;
            }
            .bar.delta { background-color: #4A90E2; }  /* 蓝色 */
            .bar.theta { background-color: #50C878; }  /* 绿色 */
            .bar.alpha { background-color: #FF8C00; }  /* 橙色 */
            .bar.beta { background-color: #9370DB; }   /* 紫色 */
            /*  文字区域放大适配 */
            .channel-values { 
                flex: 1 !important;                 /* 自动占满剩余高度 */
                display: flex !important;
                flex-direction: column !important;
                justify-content: space-around !important; /* 垂直均匀分布，或使用 flex-start */
                font-size: 10pt !important;
                line-height: 1.6 !important;
                min-height: 0 !important;
                width: 100% !important;
                margin: 0 !important;
                padding: 0 2px !important;
                box-sizing: border-box;
            }
            .value-row {
                display: flex !important;
                justify-content: space-between !important;
                gap: 8px !important;
                margin: 0 !important;
                padding: 0 !important;

            }
            .value-item { 
                display: flex; 
                justify-content: space-between;
                flex: 1;  /* 每个值占一半宽度 */
                margin: 0 !important;
                padding: 0 !important;
             
            }
            .value-item .label { 
                font-weight: bold; 
                color: #555;
                font-size: 3pt;  /* 增大字体 */
            }
            .value-item .label.label-theta{ 
                font-weight: bold; 
                color: #2A87DB;
                font-size: 3pt;  /* 增大字体 */
            }
            .value-item .label.label-alpha{ 
                font-weight: bold; 
                color: #0EB42F;
                font-size: 6pt;  /* 增大字体 */
            }
            .value-item .value { 
                color: #333;
                font-size: 9pt !important;    /* 比原来大一倍以上 */
                font-weight: normal;
                line-height: 1.5 !important;
            }
            
            /* Quantitative EEG Mapping 样式 */
            .page {
                    width: 210mm;
                    height: 297mm;

                    /* 左右按 15px 统一（与导出PDF要求一致），上下仍用 mm 便于版面控制 */
                    padding: 20mm 15px 25mm 15px; /* 底部 25mm 给页脚 */
                    box-sizing: border-box;

                    position: relative;
                    page-break-after: always;
                    overflow: hidden;
                    }

            .qeeg-mapping-section { width: 100%; 
            }
            .qeeg-mapping-section .section-content {
                padding-bottom: 10px !important;
                padding-top: 5px !important;
                padding-left: 20px !important;
                padding-right: 20px !important;
                margin-bottom: 0 !important;
                overflow: hidden !important;
            }
            .qeeg-mapping-section .analysis-description-box {
                padding: 10px 20px !important;
                margin-bottom: 0px !important;
            }
            .qeeg-mapping-section .task-name-title {
                font-size: 16pt !important;
                margin-bottom: 2px !important;
            }
            .qeeg-mapping-section .analysis-description-text {
                font-size: 11px !important;
                line-height: 1.4 !important;
                margin-top: 2px !important;
            }
            .qeeg-mapping-section .analysis-method-label {
                margin-bottom: 2px !important;
            }
            
            .analysis-name-two-line {
                display: flex;
                flex-direction: column;
                line-height: 1.4;
                margin-bottom: 10px;
            }
            .analysis-name-two-line .analysis-name-main {
                font-size: 18px;
                font-weight: 700;
                color: #2c3e50;
            }
            .analysis-name-two-line .analysis-name-en {
                font-size: 14px;
                font-weight: 500;
                color: #999999;
            }
            /* 神经指标卡片区域样式 */
            .neuro-metrics-container {
                margin-top: 5px;
                width: 100%;
            }
            
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 35px 5px;
                margin-bottom: 2px;
                /* 减少卡片最小高度，避免“指标生理含义”下方留白过大 */
                grid-auto-rows: minmax(170px, auto);
            }
            
            @media (max-width: 1100px) {
                .metrics-grid {
                    grid-template-columns: 1fr;
                }
            }
            
            .metric-card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08), 0 3px 6px rgba(0, 0, 0, 0.05);
                overflow: visible;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border: 1px solid #e9ecef;
                display: flex;
                flex-direction: column;
                margin: 0 !important;
            }
            
            .metric-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 20px rgba(0, 0, 0, 0.12), 0 5px 10px rgba(0, 0, 0, 0.08);
            }
            
            .card-header {
                padding: 4px;
                border-bottom: 1px solid #f1f3f7;
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
            }
            /* 左侧标题区域 */
            .card-header-left {
                flex: 1;
            }
            
            /* 右侧数值区域：留白缩小，避免标题（如「闭眼后 α 峰值频率」）在数值为 11.1 Hz 时换行 */
            .card-header-right {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                justify-content: center;
                margin-left: 4px;
                padding-left: 4px;
                border-left: 1px solid #e9ecef;
            }
            
            /* 大数值显示 */
            .metric-value-large {
                font-size: 20px;
                font-weight: 700;
                color: #4A90E2;
                line-height: 1;
                margin-bottom: 0px;
            }
            
            /* 大单位显示 */
            .metric-unit-large {
                font-size: 10px;
                color: #6c757d;
                font-weight: 500;
            }
            
            /* 参考值显示 */
            .ref-value-simple {
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 11px;
                color: #666666;
                text-align: right;
                margin-top: 2px;
                line-height: 1;
            }

            .card-title {
                font-size: 14px;
                font-weight: 700;
                color: #2c3e50;
                margin-bottom: 2px;
                display: flex;
                align-item: left;
            }
            .card-header-compact .card-title-compact {
                font-size: 13px;
                margin-bottom: 2px;
                line-height: 1.2;
            }
            .card-header-compact .card-subtitle-compact {
                font-size: 10px;
                margin-bottom: 2px;
                line-height: 1.2;
            }
            .card-header-compact .card-subtitle-en {
                color: #999999;
            }
            .card-title i {
                margin-right: 10px;
                font-size: 16px;
            }
            
            .card-subtitle {
                font-size: 12px;
                font-weight: 500;
                color: #4A90E2;
                margin-bottom: 1px;
                text-align: left;
            }
            
            .card-content {
                padding: 12px 12px 6px 12px !important; 
                flex-grow: 1;
                display: flex;
                flex-direction: column;
            }
            
            .spacer-after-description {
                    flex-grow: 0.5;
                    min-height: 5px;
                }

            
            .description-section {
                margin-top: 3px;  /* 与参考范围间距，三块之间留白减半 */
            }
            
            .section-title {
                font-size: 14px;
                font-weight: 600;
                color: #000000;
                margin-top: 5px;
                margin-bottom: 5px;
                padding-bottom: 5px;
                border-bottom: 1px dashed #e0e6ef;
                text-align: left;
            }
            .description-section .section-title:not(:first-of-type) {
                margin-top: 9px;
            }
            
            .description-text {
                color: #31373D;
                font-size: 12px;
                line-height: 1.6;
                margin-bottom: 5px;
                text-align: left;
            }
            
            /* 新增：内联描述行样式 */
            .description-row {
                margin-top: 2px;
                margin-bottom: 2px;
                line-height: 1.3;
                text-align: left;
            }
            .description-row i {
                margin-right: 4px;
                /* color inherited from card theme below */
            }
            .description-label {
                font-size: 13px;
                font-weight: 600;
                color: #2c3e50;
                margin-right: 4px;
            }
            .description-content {
                color: #5a6c7d;
                font-size: 11px;
            }
            /*上面是描述内容的颜色 */
            /* 描述行图标颜色统一更改为黑色 */
            .card-1 .description-row i { color: #2c3e50; }
            .card-2 .description-row i { color: #2c3e50; }
            .card-3 .description-row i { color: #2c3e50; }
            .card-4 .description-row i { color: #2c3e50; }

            .highlight-text {
                color: #e74c3c;
                font-weight: 500;
            }
            .card-1 .card-title i { color: #3498db; }
            .card-2 .card-title i { color: #2ecc71; }
            .card-3 .card-title i { color: #9b59b6; }
            .card-4 .card-title i { color: #e74c3c; }
            
            .note {
                margin-top: 30px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #4A90E2;
                font-size: 14px;
                color: #5a6c7d;
            }
            
            /* 进度条容器 */
            .score-bar {
                width: 100%;                /* 占满父容器宽度 */
                margin: 0;
                font-family: "Microsoft YaHei", Arial, sans-serif;
                display: flex;
                flex-direction: column;
                position: relative; 
            }
    
            /* 分段色块容器 */
            .bar-segments {
                display: flex;
                height: 18px;
                border-radius: 9px; /* 圆角=高度的一半，实现胶囊效果 */
                overflow: hidden; /* 隐藏超出圆角的部分 */
                position: relative; /* 必须加！成为游标的定位父级 */
                width: 100%;
            }
    
            /* 单个分段样式 */
            .segment {
                display: flex;
                align-items: center;
                justify-content: center;
                color: #fff;
                font-weight: bold;
                font-size: 12px;
                flex-shrink: 0; /* 防止压缩 */
            }
            
            /* 超出范围区间样式 */
            .seg-out-left, .seg-out-right {
                min-width: 10%;
            }
            
            /* PAF线性刻度表：刻度范围4-16 Hz，与左图一致 E=饱和红 C=黄绿 A=鲜亮绿 */
            /* 总结构：左边红色区间(10%) + seg-f(4-6: 13.33%) + seg-e(6-8: 13.33%) + seg-d(8-12: 26.67%) + seg-c(12-14: 13.33%) + seg-b(14-16: 13.33%) + 右边红色区间(10%) */
            .card-1 .seg-out-left { width: 10%; background-color: #ef4444; }  /* 左边无标签：饱和红 */
            .card-1 .seg-f { width: 13.33%; background-color: #f97316; }  /* 4-6 Hz E 饱和红 */
            .card-1 .seg-e { width: 13.33%; background-color: #f4b300; }  /* 6-8 Hz C 黄 */
            .card-1 .seg-d { width: 26.67%; background-color: #22c55e; }  /* 8-12 Hz A 鲜亮绿 */
            .card-1 .seg-c { width: 13.33%; background-color: #f4b300; }  /* 12-14 Hz C 黄 */
            .card-1 .seg-b { width: 13.33%; background-color: #f97316; }  /* 14-16 Hz E 饱和红 */
            .card-1 .seg-out-right { width: 10%; background-color: #ef4444; }  /* 右边无标签：饱和红 */ 
    
            /* TBR刻度表：与左图一致 A=鲜亮绿 B=黄绿 C=黄橙 D=橙 E=饱和红 */
            /* 总结构：seg-a(10%) + seg-b(20%) + seg-c(20%) + seg-d(20%) + seg-e(20%) + 右边无标签(10%) */
            .card-2 .seg-a { width: 10%; background-color: #22c55e; }  /* A: <1 鲜亮绿（左无标签同） */
            .card-2 .seg-b { width: 20%; background-color: #a3e635; }  /* B: [1, 1.5) 黄绿 */
            .card-2 .seg-c { width: 20%; background-color: #f4b300; }   /* C: [1.5, 2) 黄橙 */
            .card-2 .seg-d { width: 20%; background-color: #f59e0b; }  /* D: [2, 2.5) 橙 */
            .card-2 .seg-e { width: 20%; background-color: #f97316; }  /* E: [2.5, 3] 饱和红 */
            .card-2 .seg-out-right { width: 10%; background-color: #ef4444; }  /* 右无标签：饱和红 */ 
            
            /* FAA刻度表：与左图一致 E=饱和红 C=黄绿 A=鲜亮绿 */
            /* 总结构：左无名(10%) + E(13.33%) + C(13.34%) + A(26.66%) + C(13.34%) + E(13.33%) + 右无名(10%) */
            .card-3 .seg-out-left { width: 10%; background-color: #ef4444; }  /* 左无名 (-∞,-30) 饱和红 */
            .card-3 .seg-f { width: 13.33%; background-color: #f97316; }  /* 左E [-30,-10) 饱和红 */
            .card-3 .seg-e { width: 13.34%; background-color: #f4b300; }  /* 左C [-10,0) 黄绿 */
            .card-3 .seg-d { width: 26.66%; background-color: #22c55e; }  /* A (-10,10) 鲜亮绿 */
            .card-3 .seg-c { width: 13.34%; background-color: #f4b300; }  /* 右C (10,30] 黄绿 */
            .card-3 .seg-b { width: 13.33%; background-color: #f97316; }  /* 右E (10,30] 饱和红 */
            .card-3 .seg-out-right { width: 10%; background-color: #ef4444; }  /* 右无名 (30,+∞) 饱和红 */ 
            
            /* 抑制指数刻度表：与左图一致 E=饱和红 D=橙 B=黄绿 A=鲜亮绿 右无名=绿(同A) */
            /* 区间长度均为0.2，刻度条中占位一致：左边(10%) + E(20%) + D(20%) + B(20%) + A(20%) + 右无名(10%) */
            .card-4 .seg-out-left { width: 10%; background-color: #ef4444; }  /* 左边无标签：饱和红 */
            .card-4 .seg-f { width: 20%; background-color: #f97316; }  /* E: [0.8,1) 饱和红 */
            .card-4 .seg-e { width: 20%; background-color: #f59e0b; }  /* D: [1, 1.2) 橙 */
            .card-4 .seg-d { width: 20%; background-color: #a3e635; }  /* B: [1.2, 1.4) 黄绿 */
            .card-4 .seg-a { width: 20%; background-color: #22c55e; }  /* A: [1.4, 1.6] 鲜亮绿 */
            .card-4 .seg-out-right { width: 10%; background-color: #22c55e; }  /* 右无名 (1.6,∞) 绿与A同 */ 
            
            /* 数值指示竖线（如 paf=9.8 时指向 9.8 的那条）：加粗一倍，左右各一条白线 */
            .card-1 .cursor {
            position: absolute;
            top: 0;
            left: 10%; /* 关键：修改此百分比，可将游标放在任意位置（0%-100%） */
            width: 4px; /* 游标线宽：加粗一倍（原 2px） */
            height: 100%; /* 与进度条同高 */
            background-color: #000; /* 纯黑 */
            box-shadow: -1px 0 0 #fff, 1px 0 0 #fff; /* 竖线左右各一条白线 */
            transform: translateX(-50%); /* 以 left 为竖线中心对齐 */
            z-index: 1; /* 确保在色块上层显示 */
            }
            
            .card-2 .cursor {
            position: absolute;
            top: 0;
            left: 70%; /* 关键：修改此百分比，可将游标放在任意位置（0%-100%） */
            width: 4px; /* 游标线宽：加粗一倍（原 2px） */
            height: 100%; /* 与进度条同高 */
            background-color: #000; /* 纯黑 */
            box-shadow: -1px 0 0 #fff, 1px 0 0 #fff; /* 竖线左右各一条白线 */
            transform: translateX(-50%); /* 以 left 为竖线中心对齐 */
            z-index: 1; /* 确保在色块上层显示 */
            }
            
            .card-3 .cursor {
            position: absolute;
            top: 0;
            left: 50%; /* 关键：修改此百分比，可将游标放在任意位置（0%-100%） */
            width: 4px; /* 游标线宽：加粗一倍（原 2px） */
            height: 100%; /* 与进度条同高 */
            background-color: #000; /* 纯黑 */
            box-shadow: -1px 0 0 #fff, 1px 0 0 #fff; /* 竖线左右各一条白线 */
            transform: translateX(-50%); /* 以 left 为竖线中心对齐 */
            z-index: 1; /* 确保在色块上层显示 */
            }
            
            .card-4 .cursor {
            position: absolute;
            top: 0;
            left: 20%; /* 关键：修改此百分比，可将游标放在任意位置（0%-100%） */
            width: 4px; /* 游标线宽：加粗一倍（原 2px） */
            height: 100%; /* 与进度条同高 */
            background-color: #000; /* 纯黑 */
            box-shadow: -1px 0 0 #fff, 1px 0 0 #fff; /* 竖线左右各一条白线 */
            transform: translateX(-50%); /* 以 left 为竖线中心对齐 */
            z-index: 1; /* 确保在色块上层显示 */
            }
    
            /* 刻度容器 - 与bar-segments使用相同的flex布局，确保完全对齐 */
            .scale {
                display: flex;
                margin-top: 5px;
                font-size: 11px;
                color: #666;
                width: 100%;
                position: relative;
                /* 确保与bar-segments使用相同的宽度计算方式 */
                box-sizing: border-box;
            }
            
            /* 刻度表下方参考范围：左对齐，标题前带铅笔图标 */
            .scale-ref-range {
                margin-top: 6px;
                font-size: 11px;
                color: #888;
                line-height: 1.4;
                text-align: left;
            }
            .scale-ref-range-title {
                display: flex;
                align-items: center;
                font-size: 14px;
                font-weight: 600;
                color: #2c3e50;
                text-align: left;
            }
            .scale-ref-range-icon {
                display: inline-block;
                width: 12px;
                height: 5px;
                border: 1px solid #9ca3af;
                border-radius: 1.5px;
                transform: rotate(35deg);
                margin-right: 6px;
                flex-shrink: 0;
                background-image:
                    linear-gradient(#9ca3af, #9ca3af),
                    linear-gradient(#9ca3af, #9ca3af),
                    linear-gradient(#9ca3af, #9ca3af),
                    linear-gradient(#9ca3af, #9ca3af);
                background-size: 0.5px 3px;
                background-position: 2px 1px, 4px 1px, 7px 1px, 10px 1px;
                background-repeat: no-repeat;
            }
            .scale-ref-range-value {
                margin-top: 2px;
                margin-left: 18px;  /* 与标题文字左对齐，不跟图标对齐（图标约12px+6px间距） */
                padding-left: 0;
                color: #555;
                text-align: left;
            }
    
            /* 刻度标签 - 数字在对应区间分界线正下方（分界线在刻度格右边界时数字右对齐） */
            .tick {
                position: relative;
                text-align: right; /* 默认数字在分界线（右边界）正下方 */
                flex-shrink: 0; /* 防止压缩，与segment保持一致 */
                display: flex;
                flex-direction: column;
                align-items: flex-end; /* 数字对齐到分界线 */
                justify-content: flex-end;
            }
    
            /* 刻度竖线（刻度线）- 精确对齐到segment边界 */
            .tick::before {
                content: "";
                position: absolute;
                top: -12px;
                left: 0; /* 改为左对齐，与segment的左边界对齐 */
                width: 1px;
                height: 10px;
                background-color: #666;
                z-index: 1;
            }
            
            /* 脑功能核心指标分析：只隐藏刻度竖线，保留数值 */
            .neuro-metrics-container .tick::before {
                display: none;
            }
            
            /* 对于第一个刻度，竖线应该在右边界（segment的右边界） */
            .tick:first-of-type::before {
                left: auto;
                right: 0;
            }
            
            /* 对于最后一个刻度，竖线应该在左边界 */
            .tick:last-of-type::before {
                left: 0;
                right: auto;
            }
            
            /* 超出范围的刻度显示竖线（在边界上） */
            .tick-out-left::before {
                display: block; /* 左边红色区间右边界需要显示竖线 */
                left: auto;
                right: 0;
            }
            .tick-out-right::before {
                display: none; /* 右边区间不显示竖线 */
            }
            
            /* PAF线性刻度表：刻度位置按segment边界对齐 */
            /* 结构：左边红色区间(10%) + seg-f(E区间4-6: 13.33%) + seg-e(C区间6-8: 13.33%) + seg-d(A区间8-12: 26.67%) + seg-c(C区间12-14: 13.33%) + seg-b(E区间14-16: 13.33%) + 右边红色区间(10%) */
            /* 刻度位置：4在左边红色区间右边界/E区间左边界(10%), 6在E区间右边界/C区间左边界(23.33%), 8在C区间右边界/A区间左边界(36.67%), 12在A区间中间(50%), 14在C区间右边界/E区间左边界(76.67%), 16在E区间右边界/右边红色区间左边界(90%) */
            /* flex值必须与segment的宽度完全一致，确保完美对齐 */
            .card-1 .tick-out-left { flex: 0 0 10%; width: 10%; }   /* 左边红色区间：10%，刻度4在右边界 */
            .card-1 .tick:nth-child(2) { flex: 0 0 13.33%; width: 13.33%; } /* 6: E区间宽度13.33%，刻度在右边界 */
            .card-1 .tick:nth-child(3) { flex: 0 0 13.33%; width: 13.33%; } /* 8: C区间宽度13.33%，刻度在右边界 */
            .card-1 .tick:nth-child(4) { flex: 0 0 26.67%; width: 26.67%; } /* 12: A区间宽度26.67%，刻度在中间 */
            .card-1 .tick:nth-child(5) { flex: 0 0 13.33%; width: 13.33%; } /* 14: C区间宽度13.33%，刻度在右边界 */
            .card-1 .tick:nth-child(6) { flex: 0 0 13.33%; width: 13.33%; } /* 16: E区间宽度13.33%，刻度在右边界 */
            .card-1 .tick-out-right { flex: 0 0 10%; width: 10%; }   /* 右边红色区间：10% */
            
            /* PAF刻度竖线位置调整 - 刻度在segment边界；数字在分界线正下方 */
            .card-1 .tick-out-left::before { left: auto; right: 0; } /* 左边红色区间右边界显示竖线，对应刻度4 */
            .card-1 .tick:nth-child(2)::before { left: auto; right: 0; } /* 6: 在E区间右边界/C区间左边界 */
            .card-1 .tick:nth-child(3)::before { left: auto; right: 0; } /* 8: 在C区间右边界/A区间左边界 */
            .card-1 .tick:nth-child(4)::before { left: auto; right: 0; } /* 12: 在A区间右边界/C区间左边界 */
            .card-1 .tick:nth-child(5)::before { left: auto; right: 0; } /* 14: 在C区间右边界/E区间左边界 */
            .card-1 .tick:nth-child(6)::before { left: auto; right: 0; } /* 16: 在E区间右边界/右边红色区间左边界 */
           
            /* TBR刻度表：刻度1,1.5,2,2.5,3；结构：tick-out-left(1,10%) + 1.5(20%) + 2(20%) + 2.5(20%) + 3(20%) + 右边红色(10%) */
            .card-2 .tick-out-left { flex: 0 0 10%; width: 10%; }  /* 1: A/B边界 */
            .card-2 .tick:nth-child(2) { flex: 0 0 20%; width: 20%; } /* 1.5: B/C边界 */
            .card-2 .tick:nth-child(3) { flex: 0 0 20%; width: 20%; } /* 2: C/D边界 */
            .card-2 .tick:nth-child(4) { flex: 0 0 20%; width: 20%; }  /* 2.5: D/E边界 */
            .card-2 .tick:nth-child(5) { flex: 0 0 20%; width: 20%; }  /* 3: E/右边红色边界 */
            .card-2 .tick-out-right { flex: 0 0 10%; width: 10%; }   /* 右边红色区间：10% */
            
            /* TBR刻度竖线位置调整 */
            .card-2 .tick-out-left::before { left: auto; right: 0; } /* 1: 在A/B边界 */
            .card-2 .tick:nth-child(2)::before { left: auto; right: 0; } /* 1.5: 在B/C边界 */
            .card-2 .tick:nth-child(3)::before { left: auto; right: 0; } /* 2: 在C/D边界 */
            .card-2 .tick:nth-child(4)::before { left: auto; right: 0; } /* 2.5: 在D/E边界 */
            .card-2 .tick:nth-child(5)::before { left: auto; right: 0; } /* 3: 在E/右边红色边界 */ 

            /* FAA刻度表：8个刻度 (-30,空,-10,0,10,空,30,右无名)；数值在对应区间分界线(该tick右边界)正下方，总宽100% */
            .card-3 .tick:nth-child(1) { flex: 0 0 10%; width: 10%; }   /* -30: 左无名右边界 */
            .card-3 .tick:nth-child(2) { flex: 0 0 13.33%; width: 13.33%; }  /* 空: E/C交界(-20) */
            .card-3 .tick:nth-child(3) { flex: 0 0 13.34%; width: 13.34%; }  /* -10: 左C右边界=A左 */
            .card-3 .tick:nth-child(4) { flex: 0 0 13.33%; width: 13.33%; }  /* 0: A中点 */
            .card-3 .tick:nth-child(5) { flex: 0 0 13.33%; width: 13.33%; }  /* 10: A右=右C左 */
            .card-3 .tick:nth-child(6) { flex: 0 0 13.34%; width: 13.34%; }  /* 空: C/E交界(20) */
            .card-3 .tick:nth-child(7) { flex: 0 0 13.33%; width: 13.33%; }  /* 30: 右E右边界 */
            .card-3 .tick:nth-child(8) { flex: 0 0 10%; width: 10%; }   /* 右无名 */
            
            /* FAA刻度竖线位置调整；无穷大(左右端)不显示竖线；-30显示竖线(左无名/E边界)；-20、20不显示竖线不显示数值 */
            .card-3 .tick-out-left::before { display: none; left: auto; right: 0; } /* -30: 左无名右边界/E左边界，显示竖线 */
            .card-3 .tick-out-right::before { display: none; } /* 右无穷大：不显示竖线 */
            .card-3 .tick:nth-child(2)::before { left: auto; right: 0; } /* -20 E/C交界 */
            .card-3 .tick:nth-child(3)::before { left: auto; right: 0; } /* -10 */
            .card-3 .tick:nth-child(4)::before { left: auto; right: 0; } /* 0 */
            .card-3 .tick:nth-child(5)::before { left: auto; right: 0; } /* 10 */
            .card-3 .tick:nth-child(6)::before { left: auto; right: 0; } /* 20 C/E交界 */
            .card-3 .tick:nth-child(7)::before { left: auto; right: 0; } /* 30 */ 
            
            /* 抑制指数刻度表：刻度0.8,1,1.2,1.4,1.6；区间等长0.2对应等宽：左边(10%) + E(20%) + D(20%) + B(20%) + A(20%) + 右无名(10%) */
            .card-4 .tick-out-left { flex: 0 0 10%; width: 10%; }   /* 左边红色区间，刻度0.8在右边界 */
            .card-4 .tick:nth-child(2) { flex: 0 0 20%; width: 20%; }  /* 1: E/D边界 */
            .card-4 .tick:nth-child(3) { flex: 0 0 20%; width: 20%; }  /* 1.2: D/B边界 */
            .card-4 .tick:nth-child(4) { flex: 0 0 20%; width: 20%; }  /* 1.4: B/A边界 */
            .card-4 .tick:nth-child(5) { flex: 0 0 20%; width: 20%; }  /* 1.6: A/右无名边界 */
            .card-4 .tick-out-right { flex: 0 0 10%; width: 10%; }   /* 右无名 (1.6,∞) */
            
            /* 抑制指数刻度竖线位置调整 */
            .card-4 .tick-out-left::before { left: auto; right: 0; } /* 0.8: 在左边红色右边界/E区间左边界 */
            .card-4 .tick:nth-child(2)::before { left: auto; right: 0; } /* 1: 在E/D边界 */
            .card-4 .tick:nth-child(3)::before { left: auto; right: 0; } /* 1.2: 在D/B边界 */
            .card-4 .tick:nth-child(4)::before { left: auto; right: 0; } /* 1.4: 在B/A边界 */
            .card-4 .tick:nth-child(5)::before { left: auto; right: 0; } /* 1.6: 在A区间右边界/右无名左边界 */

            /* TBR 分析和 Peak Alpha Frequency 分析样式（共用相同的卡片样式） */
            .tbr-section, .paf-section { width: 100%; }
            .tbr-section .section-content,
            .paf-section .section-content {
                padding-bottom: 60px !important;  /* 为页脚预留空间 */
                padding-top: 15px !important;
                padding-left: 20px !important;
                padding-right: 20px !important;
                margin-bottom: 0 !important;
                overflow: visible !important;
            }
            .tbr-metrics-container {
                margin-top: 30px;
                width: 100%;
            }
            .tbr-cards-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 25px;
                width: 100%;
                max-width: 1200px;
                margin: 0 auto;
            }
            .tbr-metric-card {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 25px 20px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
                border: 1px solid #e9ecef;
                transition: box-shadow 0.2s ease, transform 0.2s ease;
            }
            .tbr-metric-card:hover {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.08);
                transform: translateY(-2px);
            }
            .tbr-metric-label-zh {
                font-size: 13pt;
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 6px;
                line-height: 1.4;
            }
            .tbr-metric-label-en {
                font-size: 10pt;
                color: #6c757d;
                margin-bottom: 18px;
                line-height: 1.3;
            }
            .tbr-metric-value-container {
                display: flex;
                align-items: baseline;
                justify-content: flex-end;  /* 数值和单位靠右侧显示 */
                gap: 8px;
            }
            .tbr-metric-value {
                font-size: 32pt;
                font-weight: 700;
                color: #4A90E2;
                line-height: 1;
            }
            .tbr-metric-unit {
                font-size: 12pt;
                color: #6c757d;
                font-weight: 400;
                margin-left: 4px;
            }
            
            /* Ratio Mapping 样式 */
            .ratio-mapping-section { width: 100%; }
            .ratio-mapping-section .section-content {
                padding-bottom: 60px !important;  /* 为页脚预留空间 */
                padding-top: 15px !important;  /* 统一顶部内边距 */
                padding-left: 30px !important;  /* 与 Power Mapping 一致的左右内边距 */
                padding-right: 30px !important;
                margin-bottom: 0 !important;  /* 确保底部没有margin */
                overflow: visible !important;  /* 允许内容可见，确保完整显示 */
            }
            .ratio-matrix-grid {
                margin-top: 23px;  /* 与上方内容保持间距 */
                margin-left: auto;  /* 左侧自动边距，实现水平居中 */
                margin-right: auto;  /* 右侧自动边距，实现水平居中 */
                display: flex;
                justify-content: center;  /* 内容居中显示 */
                max-width: 100%;  /* 缩小30%：从100%缩小到70% */
                width: 100%;  /* 缩小30%：从100%缩小到70% */
            }
            /* Ratio Mapping 中的矩阵网格缩小30% */
            .ratio-mapping-section .qeeg-matrix-grid-4x3 {
                width: 100% !important;  /* 相对于ratio-matrix-grid的100% */
                max-width: 100% !important;
            }
            /* Ratio Mapping 中的单元格padding也缩小30% */
            .ratio-mapping-section .qeeg-matrix-cell {
                padding: 1px !important;  /* 缩小30%：从2px缩小到1px (2px * 0.7 ≈ 1px) */
            }
            /* Ratio Mapping 中的图片缩小30% */
            .ratio-mapping-section .qeeg-matrix-cell img {
                width: 38.5% !important;  /* 缩小30%：从55%缩小到38.5% (55% * 0.7 = 38.5%) */
                height: auto !important;
            }
            /* Ratio Mapping 使用与 Power Mapping 一致的宽度比例 */
            .ratio-mapping-section .power-matrices-container {
                display: flex !important;
                gap: 4px !important;
                flex-wrap: wrap !important;
                align-items: flex-start !important;
                justify-content: space-between !important;
                transform: scale(1.0);
                transform-origin: top center;
                margin-bottom: -30px !important;
            }
            .ratio-mapping-section .power-matrices-container .power-matrix-section {
                flex: 1 1 50% !important;
                min-width: 0 !important;
                padding: 4px 6px !important;
                padding-bottom: 28px !important;  /* 为模块色条预留高度，避免压住图片标签 */
                box-shadow: none !important;
                border-radius: 8px;
            }
            .ratio-mapping-section .power-matrices-container .power-matrix-header {
                margin-bottom: 2px !important;
            }
            .ratio-mapping-section .power-matrices-container .power-matrix-title {
                font-size: 11px !important;
            }
            .ratio-mapping-section .power-matrices-container .power-matrix-title-two-line .power-matrix-title-en {
                font-size: 9px !important;
            }
            /* Ratio 页面：小图下方标签字体与 “Power Ratios” 英文字体保持一致 */
            .ratio-mapping-section .power-matrices-container .topo-label {
                font-size: 9px !important;
                line-height: 1.2 !important;
            }
            .ratio-mapping-section .power-matrices-container .power-matrix-divider {
                margin-bottom: 3px !important;
            }
            .ratio-mapping-section .power-matrices-container .topo-matrix-grid {
                gap: 2px !important;
            }
            .ratio-mapping-section .power-matrices-container .topo-matrix-item img {
                width: 78% !important;
                max-width: 78% !important;
            }
            /* Power/Ratio 页面：色条参与正常文档流，固定在矩阵下方，避免遮挡标签 */
            .power-mapping-page .power-matrices-container .module-colorbar-wrap,
            .ratio-mapping-section .power-matrices-container .module-colorbar-wrap {
                position: static !important;
                right: auto !important;
                bottom: auto !important;
                display: flex !important;
                justify-content: flex-end !important;
                width: 100% !important;
                margin-top: 10px !important;
                z-index: 1 !important;
            }
            .qeeg-quad-wrapper {
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                margin-top: 0px !important;
                transform: scale(0.78);
                transform-origin: top center;
            }
            
            
            .qeeg-quad-grid {
                display: flex !important;
                flex-direction: row !important;
                justify-content: center !important;
                align-items: flex-start !important;
                gap: 24px !important;
                width: auto !important;
                max-width: 100%;
                margin: 0 !important;
                flex-wrap: nowrap !important;
            }
            .qeeg-quad-item {
                width: 310px;
                max-height: 580px;
                background: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                display: flex;
                flex-direction: column;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                flex-shrink: 1;
                flex-grow: 0;
                margin: 0 !important;
                box-sizing: border-box;
                min-height: 0;
                overflow: hidden;
            }
            .qeeg-quad-item:first-child {
                margin-right: 0 !important;
            }
            .qeeg-quad-title {
                font-size: 10pt;
                font-weight: bold;
                text-align: left;
                margin: 0 0 2px 0;
                padding-bottom: 2px;
                border-bottom: 1px solid #d0d0d0;
                color: #000;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-shrink: 0;
            }
            .qeeg-quad-title::after {
                content: "单位: Hz";
                font-size: 8pt;
                font-weight: normal;
                color: #999;
            }
            .qeeg-matrix-grid-4x4 {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                grid-template-rows: repeat(4, auto);
                gap: 1px;
                flex: 1 1 auto;
                width: 100%;
                max-width: 100%;
                margin: 0;
                min-height: 0;
                overflow: hidden;
            }
            .qeeg-matrix-grid-4x3 {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                grid-template-rows: repeat(3, 1fr);  /* 使用1fr确保所有行高度相同 */
                gap: 2px;  /* 缩小40%：从4px缩小到2px */
                flex: 0 0 auto;  /* 不拉伸，保持固定大小 */
                width: 100%;  /* 矩阵占满容器宽度，让图像靠着边缘 */
                max-width: 100%;  /* 限制最大宽度为100% */
                margin: 0;  /* 移除居中，让矩阵靠着边缘 */
                aspect-ratio: 4/3;  /* 保持4:3比例（4列3行） */
                min-height: 0;  /* 允许收缩 */
              
            }
            /* Ratio Mapping 中的矩阵网格gap也缩小30% */
            .ratio-mapping-section .qeeg-matrix-grid-4x3 {
                gap: 1px !important;  /* 缩小30%：从2px缩小到1px (2px * 0.7 ≈ 1px) */
            }
            .qeeg-matrix-cell {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 1px;
                margin: 0;
                min-height: 0;
                width: 100%;
                box-sizing: border-box;
                overflow: hidden;
            }
            .qeeg-matrix-cell img {
                width: 80%;
                height: auto;
                max-height: 100%;
                border-radius: 50%;
                object-fit: contain;
                background: radial-gradient(circle at center, rgba(255, 200, 150, 0.3) 0%, rgba(255, 220, 180, 0.1) 50%, transparent 100%);
                border: 1px solid rgba(200, 200, 200, 0.3);
                box-shadow: 
                    0 0 8px rgba(255, 200, 150, 0.2),
                    inset 0 0 15px rgba(255, 220, 180, 0.15),
                    0 1px 2px rgba(0,0,0,0.05);
                display: block;
                margin: 0;
            }
            .qeeg-cell-label {
                font-size: 10pt;
                text-align: center;
                margin-top: 1px;
                margin-bottom: 0;
                color: #000;
                font-weight: 400;
                line-height: 1;
                padding: 0;
                white-space: nowrap;
                overflow: hidden;
            }
            
            /* Comprehensive Assessment & Recommendations 样式 */
            .assessment-section {
                width: 100%;
            }
            .assessment-container {
                width: 100%;
                padding: 20px;
            }
            .assessment-title {
                font-size: 18pt;
                font-weight: bold;
                color: #1a1a1a;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #E0E0E0;
            }
            .assessment-content {
                min-height: 300px;
                margin-bottom: 30px;
            }
            .assessment-text {
                font-size: 11pt;
                line-height: 1.8;
                color: #333;
                white-space: pre-wrap;
                word-wrap: break-word;
                padding: 20px;
                background-color: #ffffff;
                border: 2px solid #4A90E2;
                border-radius: 8px;
                min-height: 250px;
                outline: none;
                transition: border-color 0.3s ease;
                width: 100%;  /* 保持原有宽度，占满容器 */
                box-sizing: border-box;  /* 包含padding在宽度内 */
                margin: 0 auto;  /* 居中显示 */
            }
            .assessment-text:focus {
                border-color: #1E5FA8;
                box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
            }
            .assessment-text[contenteditable="true"]:empty:before {
                content: "请在此输入医生的综合评估和建议...";
                color: #999;
                font-style: italic;
            }
            .assessment-text-placeholder {
                font-size: 11pt;
                line-height: 1.8;
                color: #999;
                font-style: italic;
                padding: 20px;
                background-color: #f9f9f9;
                border: 1px dashed #ddd;
                border-radius: 4px;
            }
            .assessment-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #E0E0E0;
            }
            .doctor-signature,
            .assessment-date {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .signature-label,
            .date-label {
                font-size: 10pt;
                color: #666;
                font-weight: 500;
            }
            .signature-value,
            .date-value {
                font-size: 11pt;
                color: #333;
                font-weight: 600;
            }
            
            /* 页头和分页样式 */
            .page-section {
                page-break-after: always;  /* 每个分析方法占一页 */
                page-break-inside: avoid;  /* 避免内容被分页截断 */
                /* A4页面固定大小：使用固定的像素高度，不随窗口大小变化 */
                /* A4纸张高度：297mm ≈ 1123px (96dpi)，减去上下边距约20px */
                min-height: 1160px;  /* 固定最小页面高度（像素值），不随窗口变化 */
                height: 1100px;  /* 固定页面高度（像素值），确保所有页面大小相同且固定 */
                max-height: 1160px;  /* 最大高度也固定，防止内容超出 */
                display: flex;
                flex-direction: column;
                position: relative;  /* 相对定位，确保子元素正常定位（页脚使用绝对定位） */
                justify-content: flex-start;  /* 内容从顶部开始，页脚固定在底部 */
                margin: 0;
                margin-bottom: 30px;  /* 页面之间添加足够间距，防止重叠 */
                padding: 0;
                padding-bottom: 0;  /* 确保底部没有padding，页脚紧贴底部 */
                box-sizing: border-box;  /* 包含padding在高度内 */
                overflow: visible;  /* 允许内容可见，确保完整显示 */
                clear: both;  /* 清除浮动，确保页面正常堆叠 */
                width: 100%;  /* 确保宽度为100% */
                /* 新添加属性*/
                box-sizing: border-box;
                page-break-after: always; /* 强制 PDF 分页 */
                
            }
            .page-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 30px;
                background: #FFFFFF;
                margin-bottom: 0;
                position: relative;
                z-index: 100;
                page-break-after: avoid;
                page-break-inside: avoid;
            }
            .page-header-left {
                display: flex;
                align-items: center;
            }
            .logo-section {
                display: flex;
                align-items: center;
                gap: 12px;
                background-color: transparent;  /* 透明背景，继承页头背景 */
            }
            .logo-image {
                height: 40px;
                width: auto;
                object-fit: contain;
            }
            .logo-icon {
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .logo-text {
                font-size: 18pt;
                font-weight: bold;
                letter-spacing: 1px;
            }
            .logo-text .ql-part {
                color: #000000;  /* QL是黑色 */
            }
            .logo-text .analyser-part {
                color: #1E5FA8;  /* analyser是蓝色 */
            }
            .page-header-right {
                text-align: right;
            }
            .report-title-main {
                font-size: 15px;
                font-family: HarmonyOS Sans SC, HarmonyOS Sans SC;
                
                font-weight: 700;
                color: #000000;
                margin-bottom: 8px;
                letter-spacing: 0.5px;
            }
            .report-date {
                font-size: 10px;
                font-family: HarmonyOS Sans SC, HarmonyOS Sans SC;
                color: #31373D;
            }
            .header-divider {
                height: 2px;
                background: #31373D ;
                margin: 0 30px;
                page-break-after: avoid;
            }
            .patient-info-box {
                background: #EAF1FF;
                padding: 12px 30px;
                margin-left: 30px;
                margin-right: 30px;
                margin-top: 10px; /* 与顶部分割线的距 */
                margin-bottom: 10px;
                border-radius: 12px;
                page-break-after: avoid;
             
            }
            .info-row {
                display: flex;
              /*  justify-content: flex-start; */
                justify-content: space-between; /* 关键：让 5 个项均匀铺开 */
                align-items: center;
              /*  align-items: flex-start; */
                gap: 0;
               /* gap: 8px; */
                flex-wrap: nowrap;
            }
            .info-item {
                display: flex;
                align-items: flex-start; 
                flex-direction: column;
                gap: 6px;
                padding: 0 8px;
                flex: 0 1 auto;
                min-width: 0;
                overflow: hidden;
            }
            .info-item:first-child {
                padding-left: 0;
            }
            .info-item:last-child {
                padding-right: 0;
            }
       
            .info-label {
                font-family: 'HarmonyOS Sans SC Medium', 'HarmonyOS Sans SC', sans-serif;
                font-size: 12px;
                font-weight: 500;
                color: #31373D;
            }
            .info-value {
                font-family: 'HarmonyOS Sans SC Medium', 'HarmonyOS Sans SC', sans-serif;
                font-size: 14px;
                font-weight: 500;
                color: #31373D;
            }
            .report-title {
                font-size: 14pt;
                font-weight: bold;
                color: #4A90E2;
                margin-bottom: 5px;
            }
            .patient-info-small {
                font-size: 9pt;
                color: #666;
            }
            .analysis-name {
                font-size: 18pt;
                font-weight: bold;
                color: #1a1a1a;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #E0E0E0;
            }
            /* 分析方法描述区域样式 */
            .analysis-description-box {
                background-color: #EAF1FF;
                border-left: 4px solid #4A90E2;
                padding: 15px 30px;
                margin-bottom: 5px;  /* 大幅减小底部间距，从25px改为5px */
                border-radius: 4px;
            }
            .qeeg-mapping-section .analysis-description-box {
                margin-bottom: 0px !important;  /* Quantitative EEG Mapping 中完全移除底部间距 */
            }
            .analysis-description-content {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .task-name-title {
                font-size: 20pt;
                font-weight: bold;
                color: #000000;
                margin-bottom: 5px;
            }
            .analysis-method-label {
                font-size: 14px;
                color: #2A87DB;
                margin-bottom: 5px;
            }
            .analysis-method-value {
                font-weight: 500;
                color: #4A90E2;
            }
            .analysis-method-chinese {
                color: #4A90E2;
                margin-left: 5px;
            }
            .analysis-description-text {
                font-size: 12px;
               color: #31373D;
                line-height: 1.6;
                margin-top: 5px;
            }
            /* 页脚样式 */
            .page-footer {
                position: relative;  /* 绝对定位，相对于.page-section */
                bottom: 0;  /* 固定在页面底部，紧贴底部 */
                left: 0;  /* 从左边开始 */
                right: 0;  /* 到右边结束 */
                width: 100%;  /* 确保宽度为100% */
                margin: 0;  /* 移除所有外边距 */
                padding: 8px 30px;  /* 统一内边距 */
                padding-bottom: 15px;  /* 底部额外padding */
                box-sizing: border-box;  /* 包含padding在宽度内 */
                text-align: center;  /* 文本居中 */
                z-index: 10;  /* 确保页脚在最上层 */
            }
            .footer-divider {
                 height: 1px;
                 background-color: #D0D0D0;
                 margin-bottom: 6px;
            }
            .footer-content {
                display: flex;
                justify-content: space-between;  /* 左右分布 */
                align-items: center;
                font-size: 12px;
                color: #999;
                white-space: nowrap;  /* 防止换行 */
                width: 100%;  /* 确保宽度为100% */
                max-width: 100%;  /* 最大宽度不超过容器 */
                box-sizing: border-box;  /* 包含padding在宽度内 */
                padding: 0;  /* 移除内边距，由父元素控制 */
                margin: 0;  /* 移除外边距 */
            }
            
            
            .page-content {
                height: 100%;
                box-sizing: border-box;
                overflow: hidden;
            }
            
            
            .footer-left {
                color: #999999;
                flex: 0 0 auto;  /* 不伸缩，保持原始大小 */
                margin-right: auto;  /* 自动左边距，推向右 */
            }
            .footer-right {
                color: #999999;
                flex: 0 0 auto;  /* 不伸缩，保持原始大小 */
                margin-left: auto;  /* 自动右边距，推向左 */
            }
            .footer-right .current-page {
                color: #4A90E2;
            }
            .section-content {
                flex: 1;
                padding: 15px 30px 40px 30px;  /* 统一内边距：上下15px/40px，左右30px，底部为页脚预留空间 */
                background: #FFFFFF;
                border-radius: 0;  /* 统一圆角 */
                margin: 0;  /* 统一margin */
                margin-bottom: 0;  /* 确保底部没有margin */
                display: flex;
                flex-direction: column;
                box-sizing: border-box;  /* 包含padding在高度内 */
                overflow: visible;  /* 允许内容可见，确保完整显示 */
                min-height: 0;  /* 允许收缩 */
            }
            /* Z评分偏离分布图模块样式 */
            .zscore-deviation-section {
              margin: 10px 0;
              font-family: 'Arial', 'Microsoft YaHei', sans-serif;
            }
            .zscore-left-right-container {
              display: flex;
              align-items: flex-start;
              gap: 20px; /* 左右内容间距，可根据需要调整 */
              flex-wrap: wrap; /* 小屏幕自动换行，保证响应性 */
              margin-bottom: 10px;
            }
            /* 左侧文字内容容器：占满剩余宽度 */
            .zscore-text-content {
              flex: 1;
              min-width: 280px; /* 小屏幕最小宽度，防止挤压 */
            }
            /* 右侧图片容器：固定宽度，适配图片比例 */
            .zscore-right-img-box {
              width: 150px;
              flex-shrink: 0; /* 防止图片被挤压 */
              margin-right:20px;              
            }
            /* 随机图片样式：与报告风格统一（圆角、阴影、自适应） */
            .zscore-random-img {
              width: 100%;
              height: auto; /* 自适应高度，保持图片比例 */
              border-radius: 6px; /* 与原有total-box/physio-box圆角一致 */
              box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); /* 与表格阴影一致，提升质感 */
              border: None;
              
            }
            .zscore-map-header {
              display: flex;
              align-items: baseline;
              gap: 15px;
              margin-bottom: 10px;
            }
            .zscore-title {
              font-size: 18px;
              font-weight: 600;
              color: #333;
              margin: 0;
            }
            .zscore-title-en {
              font-size: 14px;
              color: #666;
              margin: 0;
            }
            .zscore-note {
              font-size: 12px;
              color: #e74c3c;
              font-weight: 500;
            }
            .zscore-map-desc {
              margin-bottom: 15px;
              font-size: 14px;
              color: #555;
            }
            .zscore-desc-en {
              font-size: 13px;
              color: #777;
              margin-top: 5px;
            }
            .zscore-total-box {
              display: inline-flex;
              align-items: center;
              gap: 10px;
              padding: 8px 15px;
              background-color: #f0f7ff;
              border: 1px solid #d1e7ff;
              border-radius: 6px;
              margin-bottom: 20px;
            }
            .zscore-total-icon {
              color: #4a90e2;
              font-size: 16px;
              font-weight: bold;
            }
            .zscore-total-text {
              font-size: 14px;
              color: #333;
            }
            .zscore-total-num {
              font-weight: 600;
              color: #4a90e2;
            }
            .zscore-total-en {
              font-size: 12px;
              color: #666;
              margin: 0;
            }
            .zscore-physio-box {
              padding: 15px;
              background-color: #F0F6FF;
              border: 1px solid #eee;
              border-radius: 6px;
            }
            .zscore-physio-title {
              font-size: 15px;
              font-weight: 600;
              color: #333;
              margin: 0 0 10px 0;
            }
            .zscore-physio-text {
              font-size: 14px;
              color: #555;
              line-height: 1.6;
              margin: 0;
            }
            .zscore-red {
              color: #e74c3c;
              font-weight: 500;
            }
            .zscore-blue {
              color: #3498db;
              font-weight: 500;
            }
            
            
            .zscore-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-family: 'Arial', 'Microsoft YaHei', sans-serif;
                background-color: #ffffff;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                border: none;  /* 表格整体无边框 */
                table-layout: fixed; /* 必须加，否则列宽可能失效 */
                word-wrap: break-word;
            }
            .zscore-table thead {
                background-color: #F6F9FF;
            }
            .zscore-table th {
                padding: 12px 15px;
                text-align: left;
                font-size: 11pt;
                font-weight: 600;
                color: #676666;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background-color: #F6F9FF;
                border: none;  /* 表头无边框 */
                border-bottom: none;  /* 表头底部无边框 */
                
            }
            .zscore-table tbody tr {
                border-bottom: 1px solid #e0e0e0;  /* 仅数据行有底部边框 */
            }
            .zscore-table td {
                border: none;  /* 单元格无边框 */
                border-left: none;  /* 单元格左侧无边框 */
                border-right: none;  /* 单元格右侧无边框 */
                border-top: none;  /* 单元格顶部无边框 */
            }
            .zscore-table tbody tr:hover {
                background-color: #f9f9f9;
            }
            .zscore-table td {
                padding: 12px 15px;
                font-size: 14px;
                vertical-align: middle;
            }
            .col-region {
            font-family: Microsoft YaHei;
            font-weight: bold;
            font-size: 14px;
            color: #31373D;
            }
            /* 第二列样式：斜体，灰色 */
            .col-band {
            font-family: Microsoft YaHei;
            font-weight: 500;
            font-size: 14px;
            color: #31373D;
            }
            /* 第四列样式：小一点的字体 */
            .col-func {
            font-family: Microsoft YaHei;
            font-size: 14px;
            color: #31373D;
            font-weight: 400;
            }
            
            .zscore-table td:not(.zscore-value) {
                color: #333;
            }
            .zscore-table td:first-child {
                font-weight: 700;
            }
            .zscore-value {
                font-weight: 700;
                font-size: 20px;
            }
            .zscore-table td.zscore-value.zscore-positive {
                color: #d32f2f !important;
            }
            .zscore-table td.zscore-value.zscore-negative {
                color: #1976d2 !important;
            }
            
            /*综合评论*/
            .assessment-container {
                width: 100% !important;
                padding: 20px !important;
            }
            .assessment-title {
                font-size: 18pt !important;
                font-weight: bold !important;
                color: #31373D !important;
                margin-bottom: 20px !important;
                padding-bottom: 10px !important;
                border-bottom: 2px solid #E0E0E0 !important;
            }
            .assessment-content {
                min-height: 300px !important;
                margin-bottom: 30px !important;
            }
            .assessment-text {
                font-size: 11pt !important;
                line-height: 1.8 !important;
                color: #31373D !important;
                white-space: pre-wrap !important;
                word-wrap: break-word !important;
                padding: 20px !important;
                background-color: #ffffff !important;
                border: 2px solid #4A90E2 !important;
                border-radius: 8px !important;
                min-height: 250px !important;
                width: 100% !important;  /* 保持原有宽度，占满容器 */
                box-sizing: border-box !important;  /* 包含padding在宽度内 */
                margin: 0 auto !important;  /* 居中显示 */
            }
            .assessment-footer {
                display: flex !important;
                justify-content: space-between !important;
                margin-top: 40px !important;
                padding-top: 20px !important;
                border-top: 1px solid #E0E0E0 !important;
            }
            /* Initial button style */
            .btn-save {
                padding: 6px 16px;
                cursor: pointer;
                background-color: #007bff; /* Primary blue */
                color: white;
                border: none;
                border-radius: 4px;
                transition: background-color 0.3s;
            }
            
            /* Green state when saved */
            .btn-saved-active {
                background-color: #28a745 !important; /* Success green */
                cursor: default;
            }
            
            /* 打印时的分页控制（与屏幕预览保持完全一致：A4 纸，零页面边距，
               内边距和版面全部由 .page-section 自身的 CSS 控制） */
            @media print {
                @page {
                    size: A4;   /* 标准 A4：210mm × 297mm */
                    margin: 0;  /* 纸张级别无边距；版心内边距交给 .page-section 管理 */
                }
                html, body {
                    margin: 0;
                    padding: 0;
                    background: white;
                    width: 210mm;  /* 防止 body 超出纸张宽度 */
                }
                /* 每个 .page-section 严格对齐一张 A4 页面，与 @media screen 完全一致 */
                .page-section {
                    width: 210mm !important;
                    height: 297mm !important;
                    min-height: 0 !important;
                    max-height: 297mm !important;
                    padding: 0 15px !important;  /* 与 screen 模式左右内边距保持一致 */
                    box-sizing: border-box !important;
                    overflow: hidden !important;
                    page-break-after: always;
                    page-break-inside: avoid;
                    margin: 0 !important;
                    box-shadow: none !important;
                    border-radius: 0 !important;
                    background: white !important;
                    position: relative !important;
                }
                /* 页脚在打印时同样固定在页底 */
                .page-footer {
                    position: absolute !important;
                    left: 0 !important;
                    right: 0 !important;
                    bottom: 0 !important;
                    margin: 0 !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                    background: #FFFFFF !important;
                }
                /* 打印时内容区同样为页脚预留空间 */
                .section-content {
                    padding-bottom: 70px !important;
                    box-sizing: border-box !important;
                }
                .qeeg-mapping-section .section-content {
                    padding-bottom: 40px !important;
                }
                .power-mapping-page .section-content {
                    padding-bottom: 30px !important;
                    overflow: hidden !important;
                }
                img {
                    page-break-inside: avoid;
                }
                /* 强制颜色完整输出（背景色、图表颜色在 PDF 中保留） */
                * {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                .metrics-grid {
                    grid-template-columns: repeat(2, 1fr) !important;
                }
            }
            /* 黑色倒三角形箭头，放在刻度条上方 */
            .card-1 .arrow-indicator,
            .card-2 .arrow-indicator,
            .card-3 .arrow-indicator,
            .card-4 .arrow-indicator {
                position: absolute;
                top: -8px;           /* 根据实际需要调整垂直位置 */
                left: 0;
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid black;  /* 向下箭头 */
                transform: translateX(-50%);
                z-index: 5;
            }
        </style>
        
        <script>
        
        function saveAssessment() {
            const editor = document.getElementById('assessment-text-editor');
            const btn = document.getElementById('save-btn');
        
            // 1. Disable editing
            editor.contentEditable = "false";
            editor.style.backgroundColor = "#f9f9f9"; // Optional: grey out to show it's locked
        
            // 2. Change button appearance and text
            btn.innerText = "已保存";
            btn.classList.add('btn-saved-active');
            
            // 3. Disable the button so it can't be clicked again
            btn.disabled = true;
        
            // 标记评论已保存，供 printToPdf 前检查
            window._assessmentSaved = true;
            window._assessmentContent = editor.innerHTML;
            
            // Optional: Logic to send data to your server via fetch/POST would go here
            console.log("QL_ASSESSMENT_SAVED:" + encodeURIComponent(editor.innerHTML));
        }
        
        // 确保在页面加载完成后执行
        document.addEventListener('DOMContentLoaded', function() {
            // 添加Font Awesome图标库
            if (!document.querySelector('link[href*="font-awesome"]')) {
                const faLink = document.createElement('link');
                faLink.rel = 'stylesheet';
                faLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
                document.head.appendChild(faLink);
            }
            
            // 简单的交互效果
            const metricCards = document.querySelectorAll('.metric-card');
            
            metricCards.forEach(card => {
                card.addEventListener('click', function() {
                    this.style.transform = 'scale(0.99)';
                    setTimeout(() => {
                        this.style.transform = '';
                    }, 150);
                });
            });
            
            // 模拟动态数据更新
            function updateValues() {
                const values = document.querySelectorAll('.tbr-metric-value');
                if(values.length > 0) {
                    // 模拟数据变化
                    values[0].textContent = (1.65 + Math.random() * 0.2 - 0.1).toFixed(2);
                    values[1].textContent = (1.42 + Math.random() * 0.2 - 0.1).toFixed(2);
                    values[2].textContent = (
                        (parseFloat(values[0].textContent) + parseFloat(values[1].textContent)) / 2
                    ).toFixed(2);
                }
            }
            
            // 每10秒更新一次数据（模拟实时数据）
            setInterval(updateValues, 10000);
        });
</script>
    """
