import markdown
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication
class MdStreamConvertor:
    def __init__(self):
        self.buffer = ""
        self.last_start = None
        self.dialog_buffer = ""
        self.dialog_start = None
        self.in_table = False

    def append_answer(self, text_edit, text):
        #print(text)
        parts = text.split("\n\n")

        tail = ""
        for index, complete_part in enumerate(parts):
            if index == len(parts) - 1:
                tail = ""
            else:
                tail = "\n\n"
            self.append_unit(text_edit, complete_part + tail)

    def append_unit(self, text_edit, text):
        # self.append_with_alignment(text_edit, text, "left")

        # #self.text_edit.appendPlainText(text)
        # 移动光标到文档末尾
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        # 插入文本
        cursor.insertText(text)
        cursor.movePosition(QTextCursor.End)
        # 更新文本编辑器的光标
        text_edit.setTextCursor(cursor)
        # 强制刷新视图
        # text_edit.viewport().update()
        QApplication.instance().processEvents()

        self.append_text(text_edit, text)

    def preprocess(self, text_edit):
        from PyQt5.QtGui import QTextCursor
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.End)
        self.last_start = cursor.position()
        self.dialog_start = cursor.position()

    def append_text(self, text_edit, text):

        # 将新文本添加到缓冲区
        self.dialog_buffer += text
        self.buffer += text
        if "\n\n" in self.buffer:
            self.convert_and_display(text_edit, self.buffer)
            self.buffer = ""

    def convert_and_display(self, text_edit, md_text):
        html_content = markdown.markdown(md_text)
        #print(f"md_text:{md_text}")
        #print(f"html_content:{html_content}")
        start = self.last_start
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.End)
        end = cursor.position()
        self.replace_text(text_edit, start, end, html_content)

        #text_edit.ensureCursorVisible()
        # 更新文本编辑器的光标
        cursor.movePosition(cursor.End)
        text_edit.setTextCursor(cursor)
        self.last_start = cursor.position()
        # 强制刷新视图
        # text_edit.viewport().update()

        QApplication.instance().processEvents()


    def convert_dialog(self, text_edit, text):
        html_content = markdown.markdown(text)
        start = self.dialog_start
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.End)
        end = cursor.position()

        #self.replace_text(text_edit, start, end, html_content)
        # 开始查找
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)

        # 移除选中的文本
        cursor.removeSelectedText()
        # 插入新的文本
        cursor.insertHtml(html_content + "<br>")
        #text_edit.setMarkdown(html_content)
        #cursor.insertBlock()  # 段落更新替换，最后加个换行,也能防止非表格内容被textedit误判

        # 更新文本编辑器的光标
        cursor.movePosition(cursor.End)
        text_edit.setTextCursor(cursor)
        # 强制刷新视图
        # text_edit.viewport().update()
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().processEvents()

    def replace_text(self, text_edit, start, end, new_text):
        # 查找需要替换的文本
        cursor = text_edit.textCursor()
        # 开始查找
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)

        print(f"plan to remove:{cursor.selectedText()}, start:{start}, end:{end}")
            # 移除选中的文本
        cursor.removeSelectedText()

        #test case: 1.用二级列表来回答什么是高质量睡眠 2.用列表回答怎么改善睡眠 3.输出睡眠报告模板 4. 用多维列表输出睡眠报告 5.输出睡眠报告模板，把markdown的各种元素都用上
        # 6. 你能做什么？用列表回答，包括最后一段话也是列表项
        self.in_table = "<ol>" in new_text and "</ol>" in new_text  or  "<ul>" in new_text and "</ul>" in new_text
        if self.in_table:
        # if  self.in_table:
        #     if not new_text.lower().startswith(('<ol>', '<ul>')):
                # 测试示例
                new_text +=  "<div></div>"
                print(f"adjust append:{new_text}")

        # 插入新的文本
        cursor.insertHtml(new_text)
        cursor.insertBlock() #段落更新替换，最后加个换行

        print(f"plan to insert:{new_text}")

    def postprocess(self, text_edit, text):
        if text == "True":
            #self.convert_and_display(text_edit, self.buffer)   #下面会总体刷新，因此此处可以不用

            self.convert_dialog(text_edit, self.dialog_buffer)
            print(f"convert_dialog successfully({self.dialog_start}):{self.dialog_buffer}")
            self.buffer = ""
            self.dialog_start = None
            self.dialog_buffer = ""

