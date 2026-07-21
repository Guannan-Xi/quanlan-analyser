from ...Infrastructure.log.QLLogging import QLLogging
from datetime import datetime
from ...Infrastructure.PrivacySecurity import DataProcessor
from ...Infrastructure.DB.SQLLiteAccessor import SQLLiteAccessor
import uuid
from enum import Enum
from PyQt5.QtCore import QThread
from src.Infrastructure.Device import DeviceWin
from ...Infrastructure.mng.Version import Version
from src.utils import ConfigManager

config = ConfigManager("./config/config.dat")


class Task():
    def __init__(self, id=None, name=None, analysis_method=None,
                 start_time=None, end_time=None,
                 high_pass=None, low_pass=None, notch=None,
                 high_pass_enabled=None, low_pass_enabled=None, notch_enabled=None,
                 bandpass_mode=None, x_axis_scale=None, y_axis_scale=None,
                 start_time_=None, end_time_=None, selected_event_names=None,
                 selected_event_names_segment1=None, selected_event_names_segment2=None, current_segment=None):
        self.id = id
        self.name = name
        self.analysis_method = analysis_method
        self.start_time = start_time
        self.end_time = end_time
        self.high_pass = high_pass
        self.low_pass = low_pass
        self.notch = notch
        # 兼容：旧数据没有 enable 字段时视为启用（None -> True）
        self.high_pass_enabled = True if high_pass_enabled is None else bool(int(high_pass_enabled))
        self.low_pass_enabled = True if low_pass_enabled is None else bool(int(low_pass_enabled))
        self.notch_enabled = True if notch_enabled is None else bool(int(notch_enabled))
        # Quick Bandpass 模式与波形缩放选项
        self.bandpass_mode = bandpass_mode
        self.x_axis_scale = x_axis_scale
        self.y_axis_scale = y_axis_scale
        self.start_time_ = start_time_
        self.end_time_ = end_time_
        self.selected_event_names = selected_event_names  # JSON字符串，存储选中的事件名称列表
        self.selected_event_names_segment1 = selected_event_names_segment1  # alpha Ratio 分子事件名
        self.selected_event_names_segment2 = selected_event_names_segment2  # alpha Ratio 分母事件名
        self.current_segment = current_segment  # alpha Ratio 当前分段 1 或 2

    @classmethod
    def from_dict(cls, data):
        """从字典创建Task对象"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            analysis_method=data.get("analysis_method"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            high_pass=data.get("high_pass"),
            low_pass=data.get("low_pass"),
            notch=data.get("notch"),
            high_pass_enabled=data.get("high_pass_enabled"),
            low_pass_enabled=data.get("low_pass_enabled"),
            notch_enabled=data.get("notch_enabled"),
            bandpass_mode=data.get("bandpass_mode"),
            x_axis_scale=data.get("x_axis_scale"),
            y_axis_scale=data.get("y_axis_scale"),
            start_time_=data.get("start_time_"),
            end_time_=data.get("end_time_"),
            selected_event_names=data.get("selected_event_names"),
            selected_event_names_segment1=data.get("selected_event_names_segment1"),
            selected_event_names_segment2=data.get("selected_event_names_segment2"),
            current_segment=data.get("current_segment"),
        )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "analysis_method": self.analysis_method,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "high_pass": self.high_pass,
            "low_pass": self.low_pass,
            "notch": getattr(self, "notch", None),
            "high_pass_enabled": int(getattr(self, "high_pass_enabled", True)),
            "low_pass_enabled": int(getattr(self, "low_pass_enabled", True)),
            "notch_enabled": int(getattr(self, "notch_enabled", True)),
            "bandpass_mode": getattr(self, "bandpass_mode", None),
            "x_axis_scale": getattr(self, "x_axis_scale", None),
            "y_axis_scale": getattr(self, "y_axis_scale", None),
            "start_time_": self.start_time_,
            "end_time_": self.end_time_,
            "selected_event_names": self.selected_event_names,
            "selected_event_names_segment1": getattr(self, 'selected_event_names_segment1', None),
            "selected_event_names_segment2": getattr(self, 'selected_event_names_segment2', None),
            "current_segment": getattr(self, 'current_segment', None),
        }

    @staticmethod
    def create_table(db):

        try:
            create_sql = '''
                            CREATE TABLE IF NOT EXISTS t_task (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                analysis_method TEXT NOT NULL,
                                start_time TEXT,
                                end_time TEXT,
                                high_pass REAL,
                                low_pass REAL,
                                notch REAL,
                                high_pass_enabled INTEGER DEFAULT 1,
                                low_pass_enabled INTEGER DEFAULT 1,
                                notch_enabled INTEGER DEFAULT 1,
                                start_time_ TEXT,
                                end_time_ TEXT
                            )
                        '''
            db.execute(create_sql)
            db.conn.commit()
            QLLogging.log.debug("t_task数据表创建成功")

            # 创建索引以提高查询性能
            index_sql = '''
                            CREATE INDEX IF NOT EXISTS idx_task_name 
                            ON t_task(name)
                        '''
            db.execute(index_sql)

            # 新增时间范围索引
            time_index_sql = '''
                            CREATE INDEX IF NOT EXISTS idx_task_time_range 
                            ON t_task(start_time, end_time)
                        '''
            db.execute(time_index_sql)

            # 新增滤波器参数索引
            filter_index_sql = '''
                            CREATE INDEX IF NOT EXISTS idx_task_filter_params 
                            ON t_task(high_pass, low_pass)
                        '''
            db.execute(filter_index_sql)

            db.conn.commit()
            QLLogging.log.debug("t_task索引创建成功")
            
            # 检查并添加可选列（旧库迁移）
            try:
                db.cursor.execute("PRAGMA table_info(t_task)")
                columns_info = db.cursor.fetchall()
                existing_columns = [col[1] for col in columns_info]
                # 滤波器新增字段
                if 'notch' not in existing_columns:
                    db.execute("ALTER TABLE t_task ADD COLUMN notch REAL")
                    db.conn.commit()
                    QLLogging.log.debug("t_task表添加notch列成功")
                for col_name, col_type, default_sql in (
                        ('high_pass_enabled', 'INTEGER', 'DEFAULT 1'),
                        ('low_pass_enabled', 'INTEGER', 'DEFAULT 1'),
                        ('notch_enabled', 'INTEGER', 'DEFAULT 1'),
                ):
                    if col_name not in existing_columns:
                        db.execute(f"ALTER TABLE t_task ADD COLUMN {col_name} {col_type} {default_sql}")
                        db.conn.commit()
                        QLLogging.log.debug(f"t_task表添加{col_name}列成功")

                # Quick Bandpass 模式与波形缩放参数
                for col_name in ('bandpass_mode', 'x_axis_scale', 'y_axis_scale'):
                    if col_name not in existing_columns:
                        db.execute(f"ALTER TABLE t_task ADD COLUMN {col_name} TEXT")
                        db.conn.commit()
                        QLLogging.log.debug(f"t_task表添加{col_name}列成功")

                if 'selected_event_names' not in existing_columns:
                    alter_sql = "ALTER TABLE t_task ADD COLUMN selected_event_names TEXT"
                    db.execute(alter_sql)
                    db.conn.commit()
                    QLLogging.log.debug("t_task表添加selected_event_names列成功")
                for col_name in ('selected_event_names_segment1', 'selected_event_names_segment2', 'current_segment'):
                    if col_name not in existing_columns:
                        alter_sql = f"ALTER TABLE t_task ADD COLUMN {col_name} TEXT"
                        db.execute(alter_sql)
                        db.conn.commit()
                        QLLogging.log.debug(f"t_task表添加{col_name}列成功")
            except Exception as e:
                QLLogging.log.warning(f"t_task表迁移新增列失败（可能已存在）: {e}")

            return True
        except Exception as e:
            QLLogging.log.exception(f"t_task创建表失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def insert(db, task):
        """插入新任务记录"""
        try:
            # 检查表结构，确定哪些列存在
            db.cursor.execute("PRAGMA table_info(t_task)")
            columns_info = db.cursor.fetchall()
            existing_columns = [col[1] for col in columns_info]
            
            # 构建INSERT语句，只包含存在的列
            base_columns = ['name', 'analysis_method', 'start_time', 'end_time', 'high_pass', 'low_pass']
            optional_columns = [
                'notch', 'high_pass_enabled', 'low_pass_enabled', 'notch_enabled',
                'bandpass_mode', 'x_axis_scale', 'y_axis_scale',
                'start_time_', 'end_time_', 'selected_event_names',
                'selected_event_names_segment1', 'selected_event_names_segment2', 'current_segment']

            columns = base_columns.copy()
            placeholders = ['?' for _ in base_columns]
            values = [
                task.name,
                task.analysis_method,
                task.start_time,
                task.end_time,
                task.high_pass,
                task.low_pass
            ]

            for col in optional_columns:
                if col in existing_columns:
                    columns.append(col)
                    placeholders.append('?')
                    if col == 'notch':
                        values.append(getattr(task, 'notch', None))
                    elif col == 'high_pass_enabled':
                        values.append(int(getattr(task, 'high_pass_enabled', True)))
                    elif col == 'low_pass_enabled':
                        values.append(int(getattr(task, 'low_pass_enabled', True)))
                    elif col == 'notch_enabled':
                        values.append(int(getattr(task, 'notch_enabled', True)))
                    elif col == 'bandpass_mode':
                        values.append(getattr(task, 'bandpass_mode', None))
                    elif col == 'x_axis_scale':
                        values.append(getattr(task, 'x_axis_scale', None))
                    elif col == 'y_axis_scale':
                        values.append(getattr(task, 'y_axis_scale', None))
                    elif col == 'start_time_':
                        values.append(getattr(task, 'start_time_', None))
                    elif col == 'end_time_':
                        values.append(getattr(task, 'end_time_', None))
                    elif col == 'selected_event_names':
                        values.append(task.selected_event_names)
                    elif col == 'selected_event_names_segment1':
                        values.append(getattr(task, 'selected_event_names_segment1', None))
                    elif col == 'selected_event_names_segment2':
                        values.append(getattr(task, 'selected_event_names_segment2', None))
                    elif col == 'current_segment':
                        values.append(getattr(task, 'current_segment', None))
            
            insert_sql = f'''
                            INSERT INTO t_task ({', '.join(columns)}) 
                            VALUES ({', '.join(placeholders)})
                        '''
            db.execute_and_commit(insert_sql, values)

            last_id = db.cursor.lastrowid

            QLLogging.log.debug(
                f"t_task插入记录成功: 名称={task.name}, "
                f"方法={task.analysis_method}, "
                f"时间范围={task.start_time}-{task.end_time}, "
                f"滤波器=HP({getattr(task, 'high_pass_enabled', True)}):{task.high_pass}Hz,"
                f"LP({getattr(task, 'low_pass_enabled', True)}):{task.low_pass}Hz,"
                f"Notch({getattr(task, 'notch_enabled', True)}):{getattr(task, 'notch', None)}Hz,"
                f"{task.selected_event_names}"
            )
            return last_id
        except Exception as e:
            QLLogging.log.exception(f"t_task插入数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def delete(db, task_id):
        """删除任务记录"""
        try:
            delete_sql = "DELETE FROM t_task WHERE id=?"
            db.execute_and_commit(delete_sql, (task_id,))
            QLLogging.log.debug(f"t_task删除记录成功: ID={task_id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_task删除数据失败: {e}")
            db.rollback()
            return False


    @staticmethod
    def update(db, task):
        """更新任务记录"""
        try:
            # 检查表结构，确定哪些列存在
            db.cursor.execute("PRAGMA table_info(t_task)")
            columns_info = db.cursor.fetchall()
            existing_columns = [col[1] for col in columns_info]
            
            # 构建UPDATE语句，只更新存在的列
            set_parts = []
            values = []
            
            if 'name' in existing_columns:
                set_parts.append("name=?")
                values.append(task.name)
            if 'analysis_method' in existing_columns:
                set_parts.append("analysis_method=?")
                values.append(task.analysis_method)
            if 'start_time' in existing_columns:
                set_parts.append("start_time=?")
                values.append(task.start_time)
            if 'end_time' in existing_columns:
                set_parts.append("end_time=?")
                values.append(task.end_time)
            if 'high_pass' in existing_columns:
                set_parts.append("high_pass=?")
                values.append(task.high_pass)
            if 'low_pass' in existing_columns:
                set_parts.append("low_pass=?")
                values.append(task.low_pass)
            if 'notch' in existing_columns:
                set_parts.append("notch=?")
                values.append(getattr(task, 'notch', None))
            if 'high_pass_enabled' in existing_columns:
                set_parts.append("high_pass_enabled=?")
                values.append(int(getattr(task, 'high_pass_enabled', True)))
            if 'low_pass_enabled' in existing_columns:
                set_parts.append("low_pass_enabled=?")
                values.append(int(getattr(task, 'low_pass_enabled', True)))
            if 'notch_enabled' in existing_columns:
                set_parts.append("notch_enabled=?")
                values.append(int(getattr(task, 'notch_enabled', True)))
            if 'bandpass_mode' in existing_columns:
                set_parts.append("bandpass_mode=?")
                values.append(getattr(task, 'bandpass_mode', None))
            if 'x_axis_scale' in existing_columns:
                set_parts.append("x_axis_scale=?")
                values.append(getattr(task, 'x_axis_scale', None))
            if 'y_axis_scale' in existing_columns:
                set_parts.append("y_axis_scale=?")
                values.append(getattr(task, 'y_axis_scale', None))
            # start_time_ 和 end_time_ 是可选的，只有在列存在时才更新
            if 'start_time_' in existing_columns:
                set_parts.append("start_time_=?")
                values.append(task.start_time_)
            if 'end_time_' in existing_columns:
                set_parts.append("end_time_=?")
                values.append(task.end_time_)
            if 'selected_event_names' in existing_columns:
                set_parts.append("selected_event_names=?")
                values.append(task.selected_event_names)
            if 'selected_event_names_segment1' in existing_columns:
                set_parts.append("selected_event_names_segment1=?")
                values.append(getattr(task, 'selected_event_names_segment1', None))
            if 'selected_event_names_segment2' in existing_columns:
                set_parts.append("selected_event_names_segment2=?")
                values.append(getattr(task, 'selected_event_names_segment2', None))
            if 'current_segment' in existing_columns:
                set_parts.append("current_segment=?")
                values.append(getattr(task, 'current_segment', None))

            if not set_parts:
                QLLogging.log.warning("No columns to update in t_task table")
                return False
            
            values.append(task.id)  # WHERE id=?
            
            update_sql = f'''
                    UPDATE t_task 
                    SET {', '.join(set_parts)}
                    WHERE id=?
                '''
            db.execute_and_commit(update_sql, values)
            QLLogging.log.debug(f"t_task更新记录成功: ID={task.id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_task更新数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def select_all(db, order_by="name ASC"):
        """查询所有任务记录"""
        try:
            # 检查表结构，确定哪些列存在
            db.cursor.execute("PRAGMA table_info(t_task)")
            columns_info = db.cursor.fetchall()
            existing_columns = [col[1] for col in columns_info]
            
            # 构建SELECT语句，只包含存在的列
            base_columns = ['id', 'name', 'analysis_method', 'start_time', 'end_time', 'high_pass', 'low_pass']
            optional_columns = [
                'notch', 'high_pass_enabled', 'low_pass_enabled', 'notch_enabled',
                'bandpass_mode', 'x_axis_scale', 'y_axis_scale',
                'start_time_', 'end_time_', 'selected_event_names',
                'selected_event_names_segment1', 'selected_event_names_segment2', 'current_segment']

            select_columns = base_columns.copy()
            for col in optional_columns:
                if col in existing_columns:
                    select_columns.append(col)

            select_sql = f'''
                    SELECT {', '.join(select_columns)}
                    FROM t_task 
                    ORDER BY {order_by}
                '''
            rows = db.select(select_sql)
            tasks = []
            for row in rows:
                task_data = {select_columns[i]: row[i] for i in range(min(len(select_columns), len(row)))}
                task = Task(**task_data)
                tasks.append(task)
            return tasks
        except Exception as e:
            QLLogging.log.exception(f"查询任务数据失败: {e}")
            return []

    @staticmethod
    def get_by_id(db, task_id):
        """根据ID获取任务记录"""
        try:
            # 检查表结构，确定哪些列存在
            db.cursor.execute("PRAGMA table_info(t_task)")
            columns_info = db.cursor.fetchall()
            existing_columns = [col[1] for col in columns_info]
            
            # 构建SELECT语句，只包含存在的列
            base_columns = ['id', 'name', 'analysis_method', 'start_time', 'end_time', 'high_pass', 'low_pass']
            optional_columns = [
                'notch', 'high_pass_enabled', 'low_pass_enabled', 'notch_enabled',
                'bandpass_mode', 'x_axis_scale', 'y_axis_scale',
                'start_time_', 'end_time_', 'selected_event_names',
                'selected_event_names_segment1', 'selected_event_names_segment2', 'current_segment']

            select_columns = base_columns.copy()
            for col in optional_columns:
                if col in existing_columns:
                    select_columns.append(col)

            select_sql = f'''
                    SELECT {', '.join(select_columns)}
                    FROM t_task 
                    WHERE id=?
                '''
            db.cursor.execute(select_sql, (task_id,))
            row = db.cursor.fetchone()

            if row:
                task_data = {select_columns[i]: row[i] for i in range(min(len(select_columns), len(row)))}
                return Task(**task_data)
            return None
        except Exception as e:
            QLLogging.log.exception(f"根据ID查询任务失败: {e}")
            return None

    def __repr__(self):
        """开发者调试用的字符串表示"""
        return (f"Task(id={self.id}, name={repr(self.name)}, "
                f"method={repr(self.analysis_method)}, "
                f"time=[{self.start_time}~{self.end_time}], "
                f"filter=[HP({getattr(self, 'high_pass_enabled', True)}):{self.high_pass}Hz~"
                f"LP({getattr(self, 'low_pass_enabled', True)}):{self.low_pass}Hz,"
                f"Notch({getattr(self, 'notch_enabled', True)}):{getattr(self, 'notch', None)}Hz]),"
                f"{self.selected_event_names}")

    def __str__(self):
        """用户友好的字符串表示"""
        time_str = f"{self.start_time or '无'} ~ {self.end_time or '无'}"
        hp_part = f"{self.high_pass if self.high_pass is not None else '无'}Hz"
        lp_part = f"{self.low_pass if self.low_pass is not None else '无'}Hz"
        notch_part = f"{getattr(self, 'notch', None) if getattr(self, 'notch', None) is not None else '无'}Hz"
        filter_str = (
            f"HP({'开' if getattr(self, 'high_pass_enabled', True) else '关'}):{hp_part} | "
            f"LP({'开' if getattr(self, 'low_pass_enabled', True) else '关'}):{lp_part} | "
            f"Notch({'开' if getattr(self, 'notch_enabled', True) else '关'}):{notch_part}"
        )

        return (f"任务: {self.name} | ID: {self.id} | "
                f"方法: {self.analysis_method} | "
                f"时间: {time_str} | "
                f"滤波器: {filter_str}")
