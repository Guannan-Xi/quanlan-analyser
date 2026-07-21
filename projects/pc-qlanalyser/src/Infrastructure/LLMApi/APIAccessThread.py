
from concurrent.futures import ThreadPoolExecutor

class MyObject:
    def __init__(self, name):
        self.name = name

    def my_method(self, message):
        print(f"{self.name} says: {message}")
        return f"Response from {self.name}"

# 创建对象实例
obj = MyObject("MyObjectInstance")

# 定义一个函数来包装对象方法调用
def call_my_method(obj, message):
    return obj.my_method(message)

# 创建线程池
with ThreadPoolExecutor(max_workers=5) as executor:
    # 提交任务到线程池
    future = executor.submit(call_my_method, obj, "Hello, World!")

    # 获取结果（这会阻塞直到结果准备好）
    result = future.result()
    print(result)