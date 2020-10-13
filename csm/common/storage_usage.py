from csm.common.process import SimpleProcess
from cortx.utils.log import Log

class StorageInfo:

    @staticmethod
    def get_dir_usage(dir_path="", unit="K"):
        """
        Method to get disk usage of provided dir_path
        eg: sudo du -BM /var/log
        :params: 
        dir_path: Path to find disk usage info :default: "" :type:str
        unit: Unit to define data block : default: "K" :type:str
        :return: 
        :type:str
        """

        cmd = f"sudo du -B{unit} {dir_path}"
        return StorageInfo.execute_cmd(cmd)

    @staticmethod
    def get_fs_usage(fs="", unit="K"):
        """
        Method to get disk usage of provided filesystem
        eg: df -BM /var/log/elasticsearch
        :params: 
        dir_path: Path to find disk usage of filesystem info :default: "" :type:str
        unit: Unit to define data block : default: "K" :type:str
        :return: 
        :type:str
        """

        cmd = f"df -B{unit} {fs}"
        return StorageInfo.execute_cmd(cmd)

    @staticmethod
    def execute_cmd(cmd=""):
        sp_es = SimpleProcess(cmd)
        Log.debug(f"Running {cmd}")
        res = sp_es.run()
        Log.debug(f"Resulted: {res}")
        return res
