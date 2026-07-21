import sqlite3
from ..log.QLLogging import QLLogging

class SQLLiteAccessor():
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect_db(self, db_name):
        if self.is_valid():
            self.close_db()
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def is_valid(self):
        return  self.cursor and  self.conn

    def execute(self, sql):
        if self.is_valid():
            self.cursor.execute(sql)

    def select(self, sql):
        if self.is_valid():
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            return rows
        return None

    def execute_and_commit(self, sql, value=None):
        if self.is_valid():
            if value is None:
                self.cursor.execute(sql)
                self.conn.commit()
            else:
                self.cursor.execute(sql, value)
                self.conn.commit()

    def rollback(self):
        if self.is_valid():
            self.conn.rollback()
            
    def close_db(self):
        if self.is_valid():
            self.conn.close()


#非线程安全，只能在主线程用，子线程如要使用，则自己创建
class SQLLiteDB_Only_MainTread():
    user_db = SQLLiteAccessor()

    @staticmethod
    def connect():
        SQLLiteDB_Only_MainTread.user_db.connect_db(".user.db")

    @staticmethod
    def close():
        SQLLiteDB_Only_MainTread.user_db.close_db()
