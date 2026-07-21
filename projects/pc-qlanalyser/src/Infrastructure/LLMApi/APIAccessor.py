import os
from openai import OpenAI
from pathlib import Path
import abc

#TODO
from PyQt5.QtCore import pyqtSignal, QObject
class APIAccessor((QObject)):
    #TODO
    stream_signal = pyqtSignal(str)
    stream_end_signal = pyqtSignal(str)

    def __init__(self, model):
        super().__init__()
        self.client = None  #参数在子类中初始化，下同
        self.model = model

    @abc.abstractmethod
    def getClient(self):
        pass

    @abc.abstractmethod
    def getModel(self):
        pass

    def upload_file(self, path):
        try:
            file_object = self.client.files.create(file=Path(path), purpose="file-extract")
            print(f"upload file {path} successfully:{file_object.id}")
            return file_object.id
        except Exception as e:
            print(f"Error in upload_file, path:{Path(path)}")
            import traceback
            traceback.print_exc()

    def delete_file(self, fileid):
        if not fileid:
            return
        try:
            result = self.client.files.delete(fileid)
            print(f"delete file, result :{result.deleted}")
        except Exception as e:
            print(f"Error in delete_file, path:{fileid}")
            import traceback
            traceback.print_exc()

    def sleep_report(self, question, role, fileid):
        self.ask(question, role, fileid)
        self.stream_signal.emit("(评估内容由 AI 生成，请仔细甄别)\n")

    def ask(self, question, role, fileid):
        try:
            completion = self.client.chat.completions.create(
                model=self.model,     #deepseek-r1-distill-qwen-7b
                # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                messages=[
                    {'role': 'system', 'content': f"{role}"},
                    {'role':'user','content': f"{fileid}"},
                    {'role': 'user', 'content': f"{question}"}],
                stream=True
            )
            from PyQt5 import QtGui
            from PyQt5.QtWidgets import QApplication

            #str = ""
            for chunk in completion:
                if chunk.choices[0].delta.content is None:
                    continue
            #    str += chunk.choices[0].delta.content
                self.stream_signal.emit(chunk.choices[0].delta.content)
            #    print(chunk.choices[0].delta.content, end='', flush = True)
            #self.stream_signal.emit("\n")
            self.stream_end_signal.emit("True")
            #print(str)
            #import markdown
            #print(markdown.markdown(str))

        except Exception as e:
            print(f"Error in ask.")
            import traceback
            traceback.print_exc()