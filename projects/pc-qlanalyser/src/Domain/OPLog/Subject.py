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


class OPType(Enum):
    BASIC = 0
    PREPROCESS = 1
    ANALYSE = 2
    HELP = 3


class Subject():
    def __init__(self, id, name, age=None, gender=None, create_date=None, height=None, weight=None, bmi=None,
                 analyst=None, remark=None):
        self.id = id
        self.name = name
        self.age = age
        self.gender = gender
        self.create_date = create_date
        self.height = height
        self.weight = weight
        self.bmi = bmi
        self.analyst = analyst
        self.remark = remark

    @classmethod
    def from_dict(cls, data):
        """从字典创建Subject对象"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            age=data.get("age"),
            gender=data.get("gender"),
            create_date=data.get("create_date"),
            height=data.get("height"),
            weight=data.get("weight"),
            bmi=data.get("bmi"),
            analyst=data.get("analyst"),
            remark=data.get("remark")
        )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "create_date": self.create_date,
            "height": self.height,
            "weight": self.weight,
            "bmi": self.bmi,
            "analyst": self.analyst,
            "remark": self.remark
        }

    @staticmethod
    def create_table(db):
        '''
        # 1. 删除旧表（如果存在）
        db.execute("DROP TABLE IF EXISTS t_subject")
        db.conn.commit()
        QLLogging.log.debug("旧t_subject数据表已删除")
        '''

        '''
        alter_sql = """
        ALTER TABLE t_subject ADD remark TEXT
        """
        db.execute(alter_sql)
        db.conn.commit()
        QLLogging.log.debug("旧t_subject数据表已修改")
        '''

        """创建数据表"""
        try:
            create_sql = '''
                            CREATE TABLE IF NOT EXISTS t_subject (
                                id TEXT PRIMARY KEY,
                                name TEXT NOT NULL,
                                age INTEGER,
                                gender TEXT,
                                created_date TEXT,
                                height REAL,
                                weight REAL,
                                bmi REAL,
                                analyst TEXT,
                                remark TEXT
                            )
                        '''
            db.execute(create_sql)
            db.conn.commit()
            QLLogging.log.debug("t_subject数据表创建成功")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_subject创建表失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def insert(db, subject):
        """插入新记录"""
        try:
            insert_sql = '''
                    INSERT INTO t_subject (id, name, age, gender, created_date, height, weight, bmi,analyst,remark) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?,?,?)
                '''
            values = (
                subject.id,
                subject.name,
                subject.age,
                subject.gender,
                subject.create_date,
                subject.height,
                subject.weight,
                subject.bmi,
                subject.analyst,
                subject.remark
            )
            db.execute_and_commit(insert_sql, values)
            print("*****************", db.cursor.lastrowid)
            QLLogging.log.debug(f"t_subject插入记录成功: ID={subject.id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_subject插入数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def update(db, subject):
        """更新记录"""
        try:
            update_sql = '''
                    UPDATE t_subject 
                    SET name=?, age=?, gender=?, height=?, weight=?, bmi=?,analyst=?,remark=?
                    WHERE id=?
                '''
            values = (
                subject.name,
                subject.age,
                subject.gender,
                subject.height,
                subject.weight,
                subject.bmi,
                subject.analyst,
                subject.remark,
                subject.id
            )
            db.execute_and_commit(update_sql, values)
            QLLogging.log.debug(f"t_subject更新记录成功: ID={subject.id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_subject更新数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def delete(db, subject_id):
        """删除记录"""
        try:
            delete_sql = "DELETE FROM t_subject WHERE id=?"
            db.execute_and_commit(delete_sql, (subject_id,))
            QLLogging.log.debug(f"t_subject删除记录成功: ID={subject_id}")
            return True
        except Exception as e:
            QLLogging.log.exception(f"t_subject删除数据失败: {e}")
            db.rollback()
            return False

    @staticmethod
    def clear(db):
        """删除记录"""
        try:
            truncate_sql = "DELETE FROM t_subject"
            db.execute_and_commit(truncate_sql)
            QLLogging.log.info(f"t_subject表记录已高效清空，事务提交成功")
            return True
        except Exception as e:
            db.rollback()
            QLLogging.log.exception(f"t_subject表清空失败，已执行事务回滚: {str(e)}")
            return False

    @staticmethod
    def select_all(db):
        """查询所有记录"""
        try:
            select_sql = '''
                    SELECT id, name, age, gender, created_date, height, weight, bmi,analyst,remark
                    FROM t_subject 
                    ORDER BY created_date DESC
                '''
            rows = db.select(select_sql)
            subjects = []
            for row in rows:
                subject = Subject(
                    id=row[0],
                    name=row[1],
                    age=row[2],
                    gender=row[3],
                    create_date=row[4],
                    height=row[5],
                    weight=row[6],
                    bmi=row[7],
                    analyst=row[8],
                    remark=row[9]
                )
                subjects.append(subject)
            return subjects
        except Exception as e:
            QLLogging.log.exception(f"查询数据失败: {e}")
            return []

    @staticmethod
    def get_by_id(db, subject_id):
        """根据ID获取记录"""
        try:
            select_sql = '''
                    SELECT id, name, age, gender, created_date, height, weight, bmi,analyst,remark
                    FROM t_subject 
                    WHERE id=?
                '''
            db.cursor.execute(select_sql, (subject_id,))
            row = db.cursor.fetchone()

            if row:
                return Subject(
                    id=row[0],
                    name=row[1],
                    age=row[2],
                    gender=row[3],
                    create_date=row[4],
                    height=row[5],
                    weight=row[6],
                    bmi=row[7],
                    analyst=row[8],
                    remark=row[9]

                )
            return None
        except Exception as e:
            QLLogging.log.exception(f"根据ID查询失败: {e}")
            return None
