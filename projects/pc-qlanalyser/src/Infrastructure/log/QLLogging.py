import logging
import os
from logging.handlers import RotatingFileHandler

class QLLogger():
    def __init__(self):
        self.logger = logging.getLogger('AL')
        self.logger.setLevel(logging.DEBUG)

    def set_log(self):
        user_docs = os.path.expanduser('~/Documents')
        log_dir = os.path.join(user_docs, 'AR_Analyser_Logs')
        self.do_set_logg(user_docs, log_dir, 'analyser_run.log', 'analyser_error.txt')


    def do_set_logg(self, user_docs_dir, parent_dir, log_name, error_file):
        """设置日志记录"""
        try:
            # 使用用户文档目录
            os.makedirs(parent_dir, exist_ok=True)
            log_path = os.path.join(parent_dir, log_name)

            all_handler = RotatingFileHandler(log_path, maxBytes=2*1024*1024, backupCount=10)
            all_handler.setLevel(logging.DEBUG)  # 处理所有级别的日志
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s[%(thread)d] - %(message)s')   #- %(filename)s:%(lineno)d
            all_handler.setFormatter(formatter)
            self.logger.addHandler(all_handler)

        except Exception as e:
            # 确保即使日志设置失败，我们也能看到错误信息
            print(f"Failed to setup logging: {str(e)}")
            # 尝试写入一个简单的错误文件
            try:
                with open(os.path.join(user_docs_dir, error_file), 'w') as f:
                    f.write(f"Logging setup failed: {str(e)}")
            except:
                pass

class QLLogging():
    qllog = QLLogger()
    log = qllog.logger

    @staticmethod
    def init():
        return QLLogging.qllog.set_log()

