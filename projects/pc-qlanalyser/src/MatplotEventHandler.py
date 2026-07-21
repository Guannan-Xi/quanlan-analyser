"""存放连接事件的代码"""
from PyQt5 import QtCore

from .Infrastructure.log.QLLogging import QLLogging
import pyqtgraph as pg
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import time
from pyqtgraph.opengl import GLViewWidget, GLLinePlotItem, GLGridItem
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QGraphicsRectItem, QDialog, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MatplotlibEventHandler:
    def __init__(self, canvas, owner):
        """
        :param canvas: matplotlib 图形的 canvas 对象
        :param owner: 拥有事件处理逻辑的对象（通常是一个 QWidget 或自定义类）
        """
        self.canvas = canvas
        self.owner = owner

        # 注册事件
        self.cid_click = None
        self.cid_press = None
        self.cid_motion = None

        self.connect_events()
        # self.canvas.mpl_connect("button_press_event", self.on_click)

    def connect_events(self):
        """连接所有需要的事件"""
        QLLogging.log.debug("connect_events")
        self.cid_click = self.canvas.mpl_connect('button_release_event', lambda e: self.on_released(e))
        self.cid_press = self.canvas.mpl_connect('button_press_event', lambda e: self.on_pressed(e))
        self.cid_motion = self.canvas.mpl_connect('motion_notify_event', lambda e: self.on_dragged(e))

    def disconnect_events(self):
        """断开事件连接（防止重复绑定或内存泄漏）"""
        QLLogging.log.debug("disconnect_events")
        if self.cid_click:
            self.canvas.mpl_disconnect(self.cid_click)
            self.cid_click = None
        if self.cid_press:
            self.canvas.mpl_disconnect(self.cid_press)
            self.cid_press = None
        if self.cid_motion:
            self.canvas.mpl_disconnect(self.cid_motion)
            self.cid_motion = None

    # 定义点击事件处理
    def on_released(self, event):

        self.owner.button_is_pressed = False

        is_in_dragged = self.owner.mouse_is_dragged
        self.drag_end(event)
        if is_in_dragged:
            return

        # 基本检查
        if event.inaxes is None or event.button != 1:
            return

        try:
            # 计算点击位置对应的epoch
            new_epoch = int(event.xdata // self.owner.epoch_length)
            # 验证epoch是否在有效范围内
            if new_epoch < 0 or new_epoch >= len(self.owner.df_score['Stage_Code'].values):
                return

            # 设置标志，防止combobox触发额外的更新
            self.owner._ignore_combobox_change = True
            # 清除所有现有高亮
            for line in self.owner.highlight_lines:
                try:
                    line.remove()
                except:
                    pass
            self.owner.highlight_lines.clear()
            self.owner.current_selected_epoch = new_epoch

            # 始终处理为新选择，除非点击当前选中的 epoch
            if new_epoch in self.owner.current_selected_epochs:
                # 取消选择
                self.owner.current_selected_epochs.remove(new_epoch)
                self.owner.current_selected_epoch = None

                for light in self.owner.highlight_lines[:]:
                    if (light.get_xy()[0] == new_epoch * self.owner.epoch_length and light.get_width() == self.owner.epoch_length):
                        light.remove()
                        self.owner.highlight_lines.remove(light)

                    print("after  :", light.get_xy()[0], light.get_width(), new_epoch * self.owner.scale_seconds,
                          self.owner.scale_seconds, len(self.owner.highlight_lines))

                if len(self.owner.current_selected_epochs) == 0:
                    self.owner.current_selected_epochs = []
                print("double clicked:", len(self.owner.highlight_lines), len(self.owner.current_selected_epochs))
            else:
                # 先更新内部状态
                self.owner.current_selected_epochs.append(new_epoch)
                # 在两个画布的所有子图上添加高亮
                # 处理第一个画布 (canvas1)
                if hasattr(self.owner, 'figure1'):
                    for ax in self.owner.figure1.axes:
                        line = ax.axvspan(
                            new_epoch * self.owner.epoch_length,
                            (new_epoch + 1) * self.owner.epoch_length,
                            color="pink",
                            alpha=0.3,
                            zorder=1000
                        )
                        self.owner.highlight_lines.append(line)

                # 处理第二个画布 (canvas2)
                if hasattr(self.owner, 'figure2'):
                    for ax in self.owner.figure2.axes:
                        line = ax.axvspan(
                            new_epoch * self.owner.epoch_length,
                            (new_epoch + 1) * self.owner.epoch_length,
                            color="pink",
                            alpha=0.3,
                            zorder=1000
                        )
                        self.owner.highlight_lines.append(line)

                # 重绘两个画布
            if hasattr(self.owner, 'canvas1'):
                self.owner.canvas1.draw()
            if hasattr(self.owner, 'canvas2'):
                self.owner.canvas2.draw()
            # 重置标志
            self.owner._ignore_combobox_change = False

        except Exception as e:
            QLLogging.log.exception(f"Error in onclick: {str(e)}")
            import traceback
            traceback.print_exc()
            self.owner._ignore_combobox_change = False  # 确保在发生错误时也重置标志

    def drag_end(self, event):
        self.owner.button_is_pressed = False
        self.owner.mouse_is_dragged = False
        self.owner.mouse_dragged_begin = None

    def on_pressed(self, event):
        # 基本检查
        if event.inaxes is None or event.button != 1:
            return

        try:
            # 计算点击位置对应的epoch
            new_epoch = int(event.xdata // self.owner.epoch_length)
            # 验证epoch是否在有效范围内
            if new_epoch < 0 or new_epoch >= len(self.owner.df_score['Stage_Code'].values):
                return

            self.owner.button_is_pressed = True

            if self.owner.mouse_dragged_begin is None:
                self.owner.mouse_dragged_begin = new_epoch

            self.owner.current_selected_epochs = []
            self.owner.current_selected_epoch = new_epoch
            for per_line in self.owner.highlight_lines:
                try:
                    per_line.remove()
                except:
                    pass
            self.owner.highlight_lines.clear()

            # 设置标志，防止combobox变化触发额外的更新
            self.owner._ignore_combobox_change = True

            # 在两个画布的所有子图上添加高亮
            # 处理第一个画布 (canvas1)
            canvas_draw_required = False
            if hasattr(self.owner, 'figure1'):
                for ax in self.owner.figure1.axes:
                    line = ax.axvspan(
                        new_epoch * self.owner.epoch_length,
                        (new_epoch + 1) * self.owner.epoch_length,
                        color="pink",
                        alpha=0.3,
                        zorder=1000
                    )
                    self.owner.highlight_lines.append(line)
                canvas_draw_required = True

            # 处理第二个画布 (canvas2)
            if hasattr(self.owner, 'figure2'):
                for ax in self.owner.figure2.axes:
                    line = ax.axvspan(
                        new_epoch * self.owner.epoch_length,
                        (new_epoch + 1) * self.owner.epoch_length,
                        color="pink",
                        alpha=0.3,
                        zorder=1000
                    )
                    self.owner.highlight_lines.append(line)
                canvas_draw_required = True

            # 重绘画布
            if hasattr(self.owner, 'canvas1') and canvas_draw_required:
                self.owner.canvas1.draw()
            if hasattr(self.owner, 'canvas2') and canvas_draw_required:
                self.owner.canvas2.draw()
            # 重置标志
            self.owner._ignore_combobox_change = False
        except Exception as e:
            QLLogging.log.exception(f"Error in onclick: {str(e)}")
            import traceback
            traceback.print_exc()
            self.owner._ignore_combobox_change = False  # 确保在发生错误时也重置标志

    def on_dragged(self, event):
        if not self.owner.button_is_pressed:
            return
        # 基本检查
        if event.inaxes is None or event.button != 1:
            return

        try:
            # 计算点击位置对应的epoch
            new_epoch = int(event.xdata // self.owner.epoch_length)
            # 验证epoch是否在有效范围内
            if new_epoch < 0 or new_epoch >= len(self.owner.df_score['Stage_Code'].values):
                return
            if new_epoch == self.owner.mouse_dragged_begin:
                return
            self.owner.mouse_is_dragged = True
            # 设置标志，防止combobox变化触发额外的更新
            self.owner._ignore_combobox_change = True

            self.owner.current_selected_epochs = []
            self.owner.current_selected_epoch = new_epoch

            for per_line in self.owner.highlight_lines:
                try:
                    per_line.remove()
                except:
                    pass
            self.owner.highlight_lines.clear()

            start, end = sorted([new_epoch, self.owner.mouse_dragged_begin])
            for epoch_idx in range(start, end + 1):
                self.owner.current_selected_epochs.append(epoch_idx)
                # 处理第一个画布 (canvas1)
                if hasattr(self.owner, 'figure1'):
                    for axes in self.owner.figure1.axes:
                        per_line = axes.axvspan(
                            epoch_idx * self.owner.epoch_length,
                            (epoch_idx + 1) * self.owner.epoch_length,
                            color="pink",
                            alpha=0.3,
                            zorder=1000
                        )
                        self.owner.highlight_lines.append(per_line)

                # 处理第二个画布 (canvas2)
                if hasattr(self.owner, 'figure2'):
                    for axes in self.owner.figure2.axes:
                        per_line = axes.axvspan(
                            epoch_idx * self.owner.epoch_length,
                            (epoch_idx + 1) * self.owner.epoch_length,
                            color="pink",
                            alpha=0.3,
                            zorder=1000
                        )
                        self.owner.highlight_lines.append(per_line)

                # 重绘两个画布
            if hasattr(self.owner, 'canvas1'):
                self.owner.canvas1.draw()
            if hasattr(self.owner, 'canvas2'):
                self.owner.canvas2.draw()

            # 重置标志
            self.owner._ignore_combobox_change = False

        except Exception as e:
            QLLogging.log.exception(f"Error in onclick: {str(e)}")
            import traceback
            traceback.print_exc()
            self.owner._ignore_combobox_change = False  # 确保在发生错误时也重置标志

# todo MatplotlibEventHandler_
class MatplotlibEventHandler_:
    def __init__(self, canvas, owner, plot_widgets=None):
        """
        :param canvas: matplotlib 图形的 canvas 对象
        :param owner: 拥有事件处理逻辑的对象（通常是一个 QWidget 或自定义类）
        """
        self.canvas = canvas
        self.owner = owner
        self.highlight_regions = []
        self.plot_widgets = plot_widgets
        self.last_axes_id = None
        
        # 初始化 Matplotlib 的高亮补丁列表
        self.plt_patches = []
        self.rects = []

        for pw in self.plot_widgets:
            vb = pw.getPlotItem().getViewBox()
            (_, _), (ymin, ymax) = vb.viewRange()
            # QGraphicsRectItem 参数，x, y, width, height
            r = QGraphicsRectItem(0, ymin, 0, ymax - ymin)
            r.setBrush(pg.mkBrush(255, 192, 203, 76))
            r.setPen(pg.mkPen(None))
            r.setZValue(1000)
            vb.addItem(r)
            self.rects.append((vb, r))

        # 注册事件
        self.cid_click = None
        self.cid_press = None
        self.cid_motion = None

        self.connect_events()

    def connect_events(self):
        """连接所有需要的事件"""
        QLLogging.log.debug("connect_events")
        self.cid_click = self.canvas.mpl_connect('button_release_event', lambda e: self.on_released(e))
        self.cid_press = self.canvas.mpl_connect('button_press_event', lambda e: self.on_pressed(e))
        self.cid_motion = self.canvas.mpl_connect('motion_notify_event', lambda e: self.on_dragged(e))

    def disconnect_events(self):
        """断开事件连接（防止重复绑定或内存泄漏）"""
        QLLogging.log.debug("disconnect_events")
        if self.cid_click:
            self.canvas.mpl_disconnect(self.cid_click)
            self.cid_click = None
        if self.cid_press:
            self.canvas.mpl_disconnect(self.cid_press)
            self.cid_press = None
        if self.cid_motion:
            self.canvas.mpl_disconnect(self.cid_motion)
            self.cid_motion = None

    def drag_end(self, event):
        self.owner.button_is_pressed = False
        self.owner.mouse_is_dragged = False
        self.owner.mouse_dragged_begin = None

    def on_released(self, event):
        self.owner.button_is_pressed = False
        self.owner.mouse_is_dragged = False

        is_in_dragged = self.owner.mouse_is_dragged
        self.drag_end(event)
        if is_in_dragged:
            return
        # 基本检查
        if event.inaxes is None:
            return

        try:
            # 处理右键单击取消高亮
            if event.button == 3:  # 右键
                self.owner._ignore_combobox_change = True
                # 清除所有选中的epochs
                self.owner.current_selected_epochs = []
                self.owner.current_selected_epoch = None
                # 清除高亮显示
                self.clear_highlight()
                # 重置标志
                self.owner._ignore_combobox_change = False
                self.owner.mouse_dragged_begin = None
                return

            # 只有左键才继续处理
            if event.button != 1:
                return
            # 计算点击位置对应的epoch
            new_epoch = int(event.xdata // self.owner.thread_run.epoch_length)
            # 验证epoch是否在有效范围内
            if new_epoch < 0 or new_epoch >= len(self.owner.df_score['Stage_Code'].values):
                return

            # 设置标志，防止combobox触发额外的更新
            self.owner._ignore_combobox_change = True
            self.owner.current_selected_epoch = new_epoch

            # 始终处理为新选择，除非点击当前选中的 epoch
            if new_epoch in self.owner.current_selected_epochs:
                # 取消选择
                self.owner.current_selected_epochs.remove(new_epoch)
                self.owner.current_selected_epoch = None

                if len(self.owner.current_selected_epochs) == 0:
                    self.owner.current_selected_epochs = []
            else:
                # 先更新内部状态
                self.owner.current_selected_epochs.append(new_epoch)
                start_time = new_epoch * self.owner.thread_run.epoch_length
                end_time = (new_epoch + 1) * self.owner.thread_run.epoch_length

                self.clear_highlight()
                self.update_highlight(start_time, end_time)
                self.lastStart = start_time
                self.lastEnd = end_time

            # 重置标志
            self.owner._ignore_combobox_change = False
            self.owner.mouse_dragged_begin = None

            self.end_time = time.time()
        
        except Exception as e:
            QLLogging.log.exception(f"Error in onclick: {str(e)}")
            import traceback
            traceback.print_exc()
            self.owner._ignore_combobox_change = False  # 确保在发生错误时也重置标志

    def on_pressed(self, event):
        self.start_time = time.time()
        # 基本检查
        if event.inaxes is None or event.button != 1:
            return
        try:
            # 计算点击位置对应的epoch
            new_epoch = int(event.xdata // self.owner.thread_run.epoch_length)
            # 验证epoch是否在有效范围内
            if new_epoch < 0 or new_epoch >= len(self.owner.df_score['Stage_Code'].values):
                return

            self.owner.button_is_pressed = True

            if self.owner.mouse_dragged_begin is None:
                self.owner.mouse_dragged_begin = new_epoch

            self.owner.current_selected_epochs = []
            self.owner.current_selected_epoch = new_epoch
            start_time = new_epoch * self.owner.thread_run.epoch_length
            end_time = (new_epoch + 1) * self.owner.thread_run.epoch_length

            # 设置标志，防止combobox变化触发额外的更新
            self.owner._ignore_combobox_change = True
            self.clear_highlight()
            self.update_highlight(start_time, end_time)
            self.lastStart = start_time
            self.lastEnd = end_time
            # 重置标志
            self.owner._ignore_combobox_change = False

        except Exception as e:
            QLLogging.log.exception(f"Error in onclick: {str(e)}")
            import traceback
            traceback.print_exc()
            self.owner._ignore_combobox_change = False  # 确保在发生错误时也重置标志

    def on_dragged(self, event):
        # 如果还没记录起始 epoch，或鼠标已释放，都不处理
        if self.owner.mouse_dragged_begin is None or not self.owner.button_is_pressed:
            return
        # 如果不在 axes 里，或 xdata 为 None，也不处理
        if event.inaxes is None or event.xdata is None:
            return
        try:
            # 计算点击位置对应的epoch
            new_epoch = int(event.xdata // self.owner.thread_run.epoch_length)
            # 验证epoch是否在有效范围内
            if new_epoch < 0 or new_epoch >= len(self.owner.df_score['Stage_Code'].values):
                return
            if new_epoch == self.owner.mouse_dragged_begin:
                return
            self.owner.mouse_is_dragged = True
            # 设置标志，防止combobox变化触发额外的更新
            self.owner._ignore_combobox_change = True

            self.owner.current_selected_epochs = []
            self.owner.current_selected_epoch = new_epoch
            start, end = sorted([new_epoch, self.owner.mouse_dragged_begin])

            for epoch_idx in range(start, end + 1):
                self.owner.current_selected_epochs.append(epoch_idx)

            start_time = start * self.owner.thread_run.epoch_length
            end_time = end * self.owner.thread_run.epoch_length
            self.clear_highlight()
            self.update_highlight(start_time, end_time)
            
            end_time1 = time.time()

        finally:
            self.owner._ignore_combobox_change = False  # 确保在发生错误时也重置标志

    def clear_highlight(self):
        """清除所有高亮区域"""
        for vb, rect in self.rects:
            rect.setRect(0, 0, 0, 1)
            vb.update(rect.boundingRect())

        axes = self.owner.figure.axes
        if self.last_axes_id is None or self.last_axes_id != id(axes):
            # 先删除残留的引用
            for patch in self.plt_patches:
                patch.remove()
            self.plt_patches.clear()
            from matplotlib.patches import Rectangle
            for ax in self.owner.figure.axes:
                # Rectangle 参数 (x y) 宽度 高度
                patch = Rectangle((0, 0), 0, 1,
                                transform=ax.get_xaxis_transform(),
                                color="pink", alpha=0.3, zorder=1000)
                ax.add_patch(patch)
                self.plt_patches.append(patch)
            self.last_axes_id = id(axes)

        # 重置所有 Matplotlib 高亮补丁宽度为 0
        for patch in self.plt_patches:
           patch.set_width(0)
        self.canvas.draw()

    def update_highlight(self, start_time, end_time):
        for vb, r in self.rects:
            (_, _), (ymin, ymax) = vb.viewRange()
            r.setRect(start_time, ymin, end_time - start_time, ymax - ymin)
            vb.update(r.boundingRect())

        # 批量更新 Matplotlib
        for patch in self.plt_patches:
            patch.set_x(start_time)
            patch.set_width(end_time - start_time)
        self.canvas.draw()

    def create_gl_widget(self):
        """创建支持OpenGL的绘图部件"""
        widget = GLViewWidget()
        grid = GLGridItem()
        widget.addItem(grid)
        self.plot_widgets.append(widget)
        return widget


# todo PyqtgraphPlotWidgetEventHandler
class PyqtgraphPlotWidgetEventHandler:
    def __init__(self, plot_widgets, owner):
        super().__init__()
        self.plot_widgets = plot_widgets
        self.owner = owner
        self.highlight_regions = []
        self.last_axes_id = None

        # 初始化 Matplotlib 的高亮补丁列表
        self.plt_patches = []
        self.rects = []

        for pw in self.plot_widgets:
            vb = pw.getPlotItem().getViewBox()
            (_, _), (ymin, ymax) = vb.viewRange()
            # QGraphicsRectItem 参数，x, y, width, height
            r = QGraphicsRectItem(0, ymin, 0, ymax - ymin)
            r.setBrush(pg.mkBrush(255, 192, 203, 76))
            r.setPen(pg.mkPen(None))
            r.setZValue(1000)
            vb.addItem(r)
            self.rects.append((vb, r))
            # 设置鼠标跟踪
            pw.setMouseTracking(True)
    '''
    def eventFilter(self, obj, event):
        """事件过滤器，处理 PlotWidget 的鼠标事件"""
        from PyQt5.QtCore import Qt

        # 只处理我们关注的 PlotWidget
        if obj not in self.plot_widgets:
            return False

        try:
            event_type = event.type()

            if event_type == event.MouseButtonPress:
                return self._handle_mouse_press(obj, event)
            elif event_type == event.MouseMove:
                return self._handle_mouse_move(obj, event)
            elif event_type == event.MouseButtonRelease:
                return self._handle_mouse_release(obj, event)

        except Exception as e:
            QLLogging.log.exception(f"Error in PyQtGraph event handler: {str(e)}")
            import traceback
            traceback.print_exc()
    '''

    def _handle_mouse_press(self, plot_widget, event):
        pass

    def _handle_mouse_move(self, plot_widget, event):
        pass

    def _handle_mouse_release(self, plot_widget, event):
        pass

    def clear_highlight(self):
        """清除所有高亮区域"""
        for vb, rect in self.rects:
            rect.setRect(0, 0, 0, 1)
            vb.update(rect.boundingRect())

    def update_highlight(self, start_time, end_time):
        """更新高亮区域"""
        for vb, r in self.rects:
            (_, _), (ymin, ymax) = vb.viewRange()
            r.setRect(start_time, ymin, end_time - start_time, ymax - ymin)
            vb.update(r.boundingRect())

    def add_plot_widget(self, plot_widget):
        """添加新的 PlotWidget"""
        if plot_widget not in self.plot_widgets:
            self.plot_widgets.append(plot_widget)
            plot_widget.installEventFilter(self)
            plot_widget.setMouseTracking(True)

            # 创建高亮矩形
            vb = plot_widget.getPlotItem().getViewBox()
            (_, _), (ymin, ymax) = vb.viewRange()
            r = QGraphicsRectItem(0, ymin, 0, ymax - ymin)
            r.setBrush(pg.mkBrush(255, 192, 203, 76))
            r.setPen(pg.mkPen(None))
            r.setZValue(1000)
            vb.addItem(r)
            self.rects.append((vb, r))