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

class OPLog():
    # deviceidtype: 0  hostname
    #TODO uuid不唯一，要改
    def __init__(self,  optype, action, result,  opid = None, deviceid = DeviceWin.get_device_identifier(),
                 deviceidtype = 0, deviceip=DeviceWin.get_local_ip(),  time = None, reserve1 = None):

        if not opid:
            opid = str(uuid.uuid4())
        self.opid = opid

        self.deviceid = deviceid
        self.deviceidtype =deviceidtype
        self.deviceip = deviceip
        self.optype =optype
        self.action = action

        if not time:
            time = datetime.now()
        self.time = time

        self.result = result
        if not reserve1:
            reserve1 = f"{Version.get_current_version()}"

        self.reserve1 = reserve1

    def to_mask_dict(self):
        return {
            "opId": self.opid,
            "deviceId": DataProcessor.mask_string(self.deviceid),
            "deviceType": self.deviceidtype,
            "deviceIp": DataProcessor.mask_ip_address(self.deviceip),
            "opType": self.optype,
            "opAction": self.action,
            "opTime": self.time,
            "result": self.result,
            "reserve1": self.reserve1
            }

    @staticmethod
    def write(db, optype, action, result):
        log = OPLog(optype, action, result)
        try:
            db.execute('''
                CREATE TABLE IF NOT EXISTS t_op_log (
                    opid TEXT NOT NULL PRIMARY KEY,
                    deviceid TEXT NOT NULL,
                    deviceidtype INTEGER NOT NULL,
                    deviceip TEXT NOT NULL,
                    optype INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    time DATETIME NOT NULL,
                    result TEXT NOT NULL,
                    reserve1 TEXT
                )
            ''')
            db.execute_and_commit('''
                INSERT INTO t_op_log (opid, deviceid, deviceidtype, deviceip, optype, action, time, result, reserve1) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',(log.opid, log.deviceid,log.deviceidtype,log.deviceip,log.optype,log.action, log.time,log.result,log.reserve1))

            QLLogging.log.debug(f"OPLog execute successfully, logid:{log.opid}, action:{log.action}")
        except Exception as e:
            db.rollback()
            QLLogging.log.exception(f"OPLog write_db exception: {e}, logid:{log.opid}")

    @staticmethod
    def send(db):
        try:
            #一批处理限制条数
            import requests
            import json
            import time
            while True:
                rows = db.select(''' 
                    SELECT * FROM t_op_log  limit 10
                ''')
                if not rows:
                    QLLogging.log.debug(f"no record.")
                    break
                for row in rows:
                    oplog = OPLog(row[4], row[5], row[7], row[0],
                        row[1], row[2], row[3], row[6], row[8])

                    dict = oplog.to_mask_dict()
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    url = config.config['oplog_url']
                    QLLogging.log.debug(f"post {url}: {json.dumps(dict, ensure_ascii=False, indent=4)}")
                    response = requests.post(url, json=dict, headers=headers)
                    result_code = response.json().get('code')
                    if not response.status_code == 200 or not result_code == 0:
                        time.sleep(2)
                        QLLogging.log.error(f"send failed，code: {response.status_code}, {result_code}")
                        continue

                    QLLogging.log.debug(f"send successfully.")
                    OPLog.clean(db, oplog)

                time.sleep(5)
        except Exception as e:
            QLLogging.log.exception(f"OPLog send exception: {e}")

    @staticmethod
    def clean(db, oplog):
        try:
            db.execute_and_commit('''
                DELETE FROM t_op_log  where opid = ?
                ''', (oplog.opid,))
            QLLogging.log.debug(f"delete {oplog.opid} from db successfully.")
        except Exception as e:
            db.rollback()
            QLLogging.log.exception(f"delete {oplog.opid} from db exception: {e}")

        #TODO   最好是能再备份几天
        pass

class OPLogTask(QThread):

    def run(self):
        import time
        db = SQLLiteAccessor()
        db.connect_db(".user.db")
        while True:
            try:
                time.sleep(10)
                OPLog.send(db)
                time.sleep(20)
            except Exception as e:
                QLLogging.log.exception(f"OPLogTask run failed: {e}")