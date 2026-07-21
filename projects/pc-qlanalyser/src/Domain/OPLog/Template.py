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


class Template():
    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name

    @classmethod
    def from_dict(cls, data):
        """从字典创建Template对象"""
        return cls(
            id=data.get("id"),
            name=data.get("name")
        )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name
        }

    @staticmethod
    def create_table(db):
        """创建模板数据表"""
        try:
            create_sql = '''
                    CREATE TABLE IF NOT EXISTS t_template (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE
                    )
                '''
            db.execute(create_sql)
            db.conn.commit()
            QLLogging.log.debug("t_template数据表创建成功")

            # 创建索引以提高查询性能
            index_sql = '''
                    CREATE INDEX IF NOT EXISTS idx_template_name 
                    ON t_template(name)
                '''
            db.execute(index_sql)
            db.conn.commit()
            QLLogging.log.debug("t_template索引创建成功")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_template创建表失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def insert(db, template):
        """插入新模板记录"""
        try:
            insert_sql = '''
                    INSERT INTO t_template (name) 
                    VALUES (?)
                '''
            values = (template.name,)
            db.execute_and_commit(insert_sql, values)
            last_id = db.cursor.lastrowid
            QLLogging.log.debug(f"t_template插入记录成功: {last_id}:名称={template.name}")
            return last_id
        except Exception as e:
            QLLogging.log.exception(f"t_template插入数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def select_all(db, order_by="id DESC"):
        """查询所有模板记录"""
        try:
            select_sql = f'''
                    SELECT id, name
                    FROM t_template 
                    ORDER BY {order_by}
                '''
            rows = db.select(select_sql)
            templates = []
            for row in rows:
                template = Template(
                    id=row[0],
                    name=row[1]
                )
                templates.append(template)
            return templates
        except Exception as e:
            QLLogging.log.exception(f"查询模板数据失败: {e}")
            return []

    @staticmethod
    def get_by_id(db, template_id):
        """根据ID获取模板记录"""
        try:
            select_sql = '''
                    SELECT id, name
                    FROM t_template 
                    WHERE id=?
                '''
            db.cursor.execute(select_sql, (template_id,))
            row = db.cursor.fetchone()

            if row:
                return Template(
                    id=row[0],
                    name=row[1]
                )
            return None
        except Exception as e:
            QLLogging.log.exception(f"根据ID查询模板失败: {e}")
            return None

    @staticmethod
    def get_by_name(db, template_name):
        """根据ID获取模板记录"""
        try:
            select_sql = '''
                        SELECT id, name
                        FROM t_template 
                        WHERE name=?
                    '''
            db.cursor.execute(select_sql, (template_name,))
            row = db.cursor.fetchone()

            if row:
                return Template(
                    id=row[0],
                    name=row[1]
                )
            return None
        except Exception as e:
            QLLogging.log.exception(f"根据name查询模板失败: {e}")
            return None

    @staticmethod
    def delete(db, template_id):
        """删除模板记录"""
        try:
            delete_sql = "DELETE FROM t_template WHERE id=?"
            db.execute_and_commit(delete_sql, (template_id,))
            QLLogging.log.debug(f"t_template删除记录成功: ID={template_id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_template删除数据失败: {e}")
            db.rollback()
            return False


