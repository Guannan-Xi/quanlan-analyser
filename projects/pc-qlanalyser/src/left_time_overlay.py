from PyQt5.QtCore import QObject, Qt, QEvent, QPoint, QTimer
from PyQt5.QtWidgets import QLabel, QWidget
from datetime import timedelta
import pyqtgraph as pg

class LeftTimeOverlay(QObject):
    """
    给任意 pyqtgraph.PlotWidget 添加“左侧可见时刻”悬浮文本（毫秒对齐，避免±0.001s误差）
    - 支持自由设置锚点父控件 + 角落 + 像素偏移
    - 自动监听 X 轴范围变化、父控件 Resize，文本会自动更新与摆位
    """
    def __init__(self, plot_widget, *, anchor_parent: QWidget = None,
                 corner: str = 'bottom-left', offset=(8, 8),
                 meas_date=None, dt_fmt: str = '%Y-%m-%d %H:%M:%S',
                 show_ms: bool = True, label_css: str = None):
        """
        plot_widget : 必填，pyqtgraph.PlotWidget
        anchor_parent: 文本要贴在哪个父控件里（默认贴在 plot_widget 内）
        corner      : 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center'
        offset      : (dx, dy) 像素偏移；对 bottom* 角，dy 向上为正
        meas_date   : 绝对时间起点（datetime）；不传则显示相对秒
        dt_fmt      : 绝对时间的日期时间格式，不含毫秒（毫秒自动拼接）
        show_ms     : 绝对时间是否显示毫秒
        label_css   : 可自定义样式；不传用内置白底样式
        """
        super().__init__(anchor_parent or plot_widget)
        self.plot_widget = plot_widget
        self.anchor = anchor_parent or plot_widget
        self.corner = corner.lower()
        self.offset = QPoint(int(offset[0]), int(offset[1]))
        self.meas_date = meas_date
        self.dt_fmt = dt_fmt
        self.show_ms = bool(show_ms)

        self.label = QLabel(self.anchor)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label.setStyleSheet(label_css or
            "QLabel{background:rgba(255,255,255,230);"
            "border:1px solid #D4D6D9;border-radius:3px;"
            "padding:2px 6px;color:#000;}"
        )
        self.label.hide()

        # 监听：视窗范围变化 & 父控件尺寸变化
        vb = self.plot_widget.getPlotItem().vb
        vb.sigXRangeChanged.connect(self._update)
        vb.sigRangeChanged.connect(self._update)
        self.anchor.installEventFilter(self)

        # 初始化一次
        QTimer.singleShot(0, self._update)

    # —— 对外 API ——
    def set_position(self, *, parent: QWidget = None, corner: str = None, offset=None):
        if parent is not None:
            try:
                self.anchor.removeEventFilter(self)
            except Exception:
                pass
            self.anchor = parent
            self.label.setParent(self.anchor)
            self.anchor.installEventFilter(self)
        if corner is not None:
            self.corner = corner.lower()
        if offset is not None:
            self.offset = QPoint(int(offset[0]), int(offset[1]))
        self._relayout()

    def set_meas_date(self, meas_date):
        """设置/更新绝对时间起点；传 None 改为显示相对秒"""
        self.meas_date = meas_date
        self._update()

    def set_format(self, dt_fmt: str = None, show_ms: bool = None):
        if dt_fmt is not None:
            self.dt_fmt = dt_fmt
        if show_ms is not None:
            self.show_ms = bool(show_ms)
        self._update()

    def destroy(self):
        """可选：手动卸载（会移除监听与标签）"""
        try:
            vb = self.plot_widget.getPlotItem().vb
            vb.sigXRangeChanged.disconnect(self._update)
            vb.sigRangeChanged.disconnect(self._update)
        except Exception:
            pass
        try:
            self.anchor.removeEventFilter(self)
        except Exception:
            pass
        self.label.hide()
        self.label.setParent(None)
        self.deleteLater()

    # —— 内部 ——
    def eventFilter(self, obj, event):
        if obj is self.anchor and event.type() == QEvent.Resize:
            self._relayout()
        return False

    def _left_sec(self) -> float:
        x0 = self.plot_widget.getPlotItem().vb.viewRange()[0][0]
        return int(round(x0 * 1000)) / 1000.0  # 量化到毫秒，避免±0.001s

    def _format_text(self, left_sec: float) -> str:
        if self.meas_date:
            ms = int(round(left_sec * 1000))
            t = self.meas_date + timedelta(milliseconds=ms)
            base = t.strftime(self.dt_fmt)
            return f"{base}.{ms % 1000:03d}" if self.show_ms else base
        return f"{left_sec:.3f}s"

    def _update(self, *args):
        left_sec = self._left_sec()
        self.label.setText(self._format_text(left_sec))
        self.label.adjustSize()
        self._relayout()
        self.label.show()

    def _relayout(self):
        rect = self.anchor.rect()
        w, h = self.label.width(), self.label.height()
        off = self.offset
        c = self.corner
        if c == 'top-left':
            x, y = rect.left() + off.x(), rect.top() + off.y()
        elif c == 'top-right':
            x, y = rect.right() - w - off.x(), rect.top() + off.y()
        elif c == 'bottom-right':
            x, y = rect.right() - w - off.x(), rect.bottom() - h - off.y()
        elif c == 'center':
            x, y = rect.center().x() - w // 2 + off.x(), rect.center().y() - h // 2 + off.y()
        else:  # bottom-left
            x, y = rect.left() + off.x(), rect.bottom() - h - off.y()
        self.label.move(x, y)

class DateAxis(pg.AxisItem):
    def __init__(self, meas_date, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meas_date = meas_date

    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            try:
                # v 是相对时间的秒数，加上起始时间得到绝对时间
                curr_time = self.meas_date + timedelta(seconds=v)
                # 根据缩放比例决定是否显示毫秒
                if spacing < 1:
                    strings.append(curr_time.strftime("%H:%M:%S.%f")[:-3])
                else:
                    strings.append(curr_time.strftime("%H:%M:%S"))
            except Exception:
                strings.append("")
        return strings