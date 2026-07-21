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


class HistoryTask():
    def __init__(self, id, name, created_date, relative_path, subject_id):
        self.id = id
        self.name = name
        self.created_date = created_date
        self.relative_path = relative_path
        self.subject_id = subject_id

    @classmethod
    def from_dict(cls, data):
        """从字典创建HistoryTask对象"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            created_date=data.get("created_date"),
            relative_path=data.get("relative_path"),
            subject_id=data.get("subject_id")
        )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "created_date": self.created_date,
            "relative_path": self.relative_path,
            "subject_id": self.subject_id
        }

    @staticmethod
    def create_table(db):
        """创建历史任务数据表"""
        try:
            # 首先确保数据库支持外键
            db.execute("PRAGMA foreign_keys = ON")

            create_sql = '''
                CREATE TABLE IF NOT EXISTS t_history_task (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_date TEXT,
                    relative_path TEXT,
                    subject_id TEXT,
                    FOREIGN KEY (subject_id) REFERENCES t_subject(id) ON DELETE CASCADE
                )
            '''
            db.execute(create_sql)
            db.conn.commit()
            QLLogging.log.debug("t_history_task数据表创建成功")

            # 创建索引以提高查询性能
            index_sql = '''
                CREATE INDEX IF NOT EXISTS idx_history_task_subject_id 
                ON t_history_task(subject_id)
            '''
            db.execute(index_sql)
            db.conn.commit()
            QLLogging.log.debug("t_history_task索引创建成功")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_history_task创建表失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def insert(db, history_task):
        """插入新历史任务记录"""
        try:
            insert_sql = '''
                    INSERT INTO t_history_task (name, created_date, relative_path, subject_id) 
                    VALUES (?, ?, ?, ?)
                '''
            values = (
                history_task.name,
                history_task.created_date,
                history_task.relative_path,
                history_task.subject_id
            )
            db.execute_and_commit(insert_sql, values)
            QLLogging.log.debug(
                f"t_history_task插入记录成功: 名称={history_task.name}, 受试者ID={history_task.subject_id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_history_task插入数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def update(db, history_task):
        """更新历史任务记录"""
        try:
            update_sql = '''
                    UPDATE t_history_task 
                    SET name=?, created_date=?, relative_path=?, subject_id=?
                    WHERE id=?
                '''
            values = (
                history_task.name,
                history_task.created_date,
                history_task.relative_path,
                history_task.subject_id,
                history_task.id
            )
            db.execute_and_commit(update_sql, values)
            QLLogging.log.debug(f"t_history_task更新记录成功: ID={history_task.id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_history_task更新数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def delete(db, id):
        """删除记录"""
        try:
            delete_sql = "DELETE FROM t_history_task WHERE id=?"
            db.execute_and_commit(delete_sql, (id,))
            QLLogging.log.debug(f"t_history_task删除记录成功: ID={id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_history_task删除数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_by_id(db, task_id):
        """根据ID获取历史任务记录"""
        try:
            select_sql = '''
                    SELECT id, name, created_date, relative_path, subject_id
                    FROM t_history_task 
                    WHERE id=?
                '''
            db.cursor.execute(select_sql, (task_id,))
            row = db.cursor.fetchone()

            if row:
                return HistoryTask(
                    id=row[0],
                    name=row[1],
                    created_date=row[2],
                    relative_path=row[3],
                    subject_id=row[4]
                )
            return None
        except Exception as e:
            QLLogging.log.exception(f"根据ID查询历史任务失败: {e}")
            return None

    @staticmethod
    def get_by_subject_id(db, subject_id, order_by="created_date DESC"):
        """根据受试者ID获取相关历史任务"""
        try:
            select_sql = f'''
                    SELECT id, name, created_date, relative_path, subject_id
                    FROM t_history_task 
                    WHERE subject_id = ?
                    ORDER BY {order_by}
                '''
            db.cursor.execute(select_sql, (subject_id,))
            rows = db.cursor.fetchall()

            tasks = []
            for row in rows:
                task = HistoryTask(
                    id=row[0],
                    name=row[1],
                    created_date=row[2],
                    relative_path=row[3],
                    subject_id=row[4]
                )
                tasks.append(task)
            return tasks
        except Exception as e:
            QLLogging.log.exception(f"根据受试者ID查询历史任务失败: {e}")
            return []


