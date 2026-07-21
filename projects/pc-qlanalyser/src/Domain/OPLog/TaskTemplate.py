from .Task import Task
from .Template import Template
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

class TaskTemplate(): # task和template的关联表
    def __init__(self, template_id, task_id):
        self.template_id = template_id
        self.task_id = task_id

    @classmethod
    def from_dict(cls, data):
        """从字典创建TaskTemplate对象"""
        return cls(
            template_id=data.get("template_id"),
            task_id=data.get("task_id")
        )

    def to_dict(self):
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "task_id": self.task_id
        }

    @staticmethod
    def create_table(db):
        """创建任务模板关联数据表"""
        try:
            # 首先确保数据库支持外键
            db.execute("PRAGMA foreign_keys = ON")

            create_sql = '''
                    CREATE TABLE IF NOT EXISTS t_task_template (
                        template_id INTEGER NOT NULL,
                        task_id INTEGER NOT NULL,
                        PRIMARY KEY (template_id, task_id),
                        FOREIGN KEY (template_id) REFERENCES t_template(id) ON DELETE CASCADE,
                        FOREIGN KEY (task_id) REFERENCES t_task(id) ON DELETE CASCADE
                    )
                '''
            db.execute(create_sql)
            db.conn.commit()
            QLLogging.log.debug("t_task_template数据表创建成功")

            # 创建索引以提高查询性能
            index_sql1 = '''
                    CREATE INDEX IF NOT EXISTS idx_task_template_template_id 
                    ON t_task_template(template_id)
                '''
            db.execute(index_sql1)

            index_sql2 = '''
                    CREATE INDEX IF NOT EXISTS idx_task_template_task_id 
                    ON t_task_template(task_id)
                '''
            db.execute(index_sql2)

            db.conn.commit()
            QLLogging.log.debug("t_task_template索引创建成功")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_task_template创建表失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def insert(db, template_id,task_id):
        """插入新关联记录"""
        try:
            insert_sql = '''
                    INSERT OR IGNORE INTO t_task_template (template_id, task_id) 
                    VALUES (?, ?)
                '''
            values = (
                template_id,
                task_id
            )
            db.execute_and_commit(insert_sql, values)
            QLLogging.log.debug(
                f"t_task_template插入记录成功: template_id={template_id}, task_id={task_id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_task_template插入数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def delete(db, template_id, task_id):
        """删除关联记录"""
        try:
            delete_sql = "DELETE FROM t_task_template WHERE template_id=? AND task_id=?"
            db.execute_and_commit(delete_sql, (template_id, task_id))
            QLLogging.log.debug(f"t_task_template删除记录成功: template_id={template_id}, task_id={task_id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_task_template删除数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def delete_by_template(db, template_id):
        """删除模板的所有关联记录"""
        try:
            delete_sql = "DELETE FROM t_task_template WHERE template_id=?"
            db.execute_and_commit(delete_sql, (template_id,))
            QLLogging.log.debug(f"t_task_template删除模板关联记录成功: template_id={template_id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_task_template删除模板关联数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_tasks_by_template(db, template_id):
        """根据模板ID获取所有关联的任务"""
        try:
            # 检查表结构，确定哪些列存在
            db.cursor.execute("PRAGMA table_info(t_task)")
            columns_info = db.cursor.fetchall()
            existing_columns = [col[1] for col in columns_info]
            
            # 构建SELECT语句，包含所有存在的列
            base_columns = ['t.id', 't.name', 't.analysis_method', 't.start_time', 't.end_time', 't.high_pass', 't.low_pass']
            optional_columns = [
                't.notch', 't.high_pass_enabled', 't.low_pass_enabled', 't.notch_enabled',
                't.bandpass_mode', 't.x_axis_scale', 't.y_axis_scale',
                't.start_time_', 't.end_time_', 't.selected_event_names',
                't.selected_event_names_segment1', 't.selected_event_names_segment2', 't.current_segment'
            ]

            select_columns = base_columns.copy()
            for col in optional_columns:
                if col.replace('t.', '') in existing_columns:
                    select_columns.append(col)

            select_sql = f'''
                    SELECT {', '.join(select_columns)}
                    FROM t_task t
                    INNER JOIN t_task_template tt ON t.id = tt.task_id
                    WHERE tt.template_id = ?
                    ORDER BY t.name ASC
                '''
            db.cursor.execute(select_sql, (template_id,))
            rows = db.cursor.fetchall()

            tasks = []
            for row in rows:
                # 根据 select_columns 动态映射（兼容可选列顺序变化）
                task_data = {}
                for i, col in enumerate(select_columns):
                    key = col.replace('t.', '')
                    if i < len(row):
                        task_data[key] = row[i]
                task = Task(**task_data)
                tasks.append(task)
            return tasks
        except Exception as e:
            QLLogging.log.exception(f"根据模板ID查询关联任务失败: {e}")
            return []

    @staticmethod
    def exists(db, template_id, task_id):
        """检查关联是否存在"""
        try:
            select_sql = '''
                    SELECT COUNT(*) FROM t_task_template 
                    WHERE template_id=? AND task_id=?
                '''
            db.cursor.execute(select_sql, (template_id, task_id))
            result = db.cursor.fetchone()
            return result[0] > 0 if result else False
        except Exception as e:
            QLLogging.log.exception(f"检查关联存在性失败: {e}")
            return False