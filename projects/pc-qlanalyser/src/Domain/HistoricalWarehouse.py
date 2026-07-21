from collections import deque

class SleepScoreWH:
    def __init__(self):
        self.his_wh = deque()
        self.work_data = {}

    def record(self, epoch :int, stage_code: int):
        self.work_data[epoch] = stage_code

    def finish_backup(self):
        if len(self.work_data) > 0:
            self.his_wh.append(self.work_data)
            print("SleepScoreWH:", self.work_data)
            self.work_data = {}

    def get_restore_data(self):
        if  len(self.his_wh) == 0:
            return {}
        else:
            return self.his_wh.pop()

    def is_empty(self):
        return len(self.his_wh) == 0

    def clear(self):
        self.his_wh.clear()
        self.work_data = {}
        
    def get_last_backup(self):
        """获取最近的备份记录"""
        try:
            if self.his_wh:
                return self.his_wh[-1]
            return None
        except Exception as e:
            return None

# 癫痫分析存储事件
class EpilepsyScoreWH:

    def __init__(self):
        self.his_wh = deque()
        self.work_data = {}

    def record(self, epoch :int, stage_code: int):
        self.work_data[epoch] = stage_code

    def finish_backup(self):
        if len(self.work_data) > 0:
            self.his_wh.append(self.work_data)
            self.work_data = {}

    def get_restore_data(self):
        if  len(self.his_wh) == 0:
            return {}
        else:
            return self.his_wh.pop()

    def is_empty(self):
        return len(self.his_wh) == 0

    def clear(self):
        self.his_wh.clear()
        self.work_data = {}
        
    def get_last_backup(self):
        """获取最近的备份记录"""
        try:
            if self.his_wh:
                return self.his_wh[-1]
            return None
        except Exception as e:
            return None

class EventScoreWH:
    """存储事件"""
    def __init__(self):
        self.his_wh = deque()
        self.work_data = {}

    def record(self, epoch :int, stage_code: int):
        self.work_data[epoch] = stage_code

    def finish_backup(self):
        if len(self.work_data) > 0:
            self.his_wh.append(self.work_data)
            self.work_data = {}

    def get_restore_data(self):
        if  len(self.his_wh) == 0:
            return {}
        else:
            return self.his_wh.pop()

    def is_empty(self):
        return len(self.his_wh) == 0

    def clear(self):
        self.his_wh.clear()
        self.work_data = {}
    
    def get_last_backup(self):
        """获取最后一次备份的数据"""
        if self.his_wh:
            return self.his_wh[-1]  # 返回最后一次备份
        return None