from src.utils import ConfigManager


config = ConfigManager("./config/config.dat")

class Version:

    current_version = config.config['current_version']
    current_version_code = int(config.config['current_version_code']) #<class 'str'>需要进行类型转化
    build_info = ""

    @staticmethod
    def get_current_version():
        return Version.current_version

    @staticmethod
    def need_upgrade(version_code):
        return version_code > Version.current_version_code